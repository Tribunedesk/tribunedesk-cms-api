"""Level 1 of the Tribune Desk CMS API: receive an article and make a draft.

Contract: the `article.delivered` webhook (an `ArticleDelivery` body), answered with an
`ArticleDeliveryResult`. Guide: guide/1-article-delivery.md.

Standard library only. Run it with your signing secret:

    TD_WEBHOOK_SECRET=whsec_... PORT=8080 python level1_receiver.py

The webhook address must be `https://` on a public host (any port), so to try it on your own
machine put a tunnel in front of it, for example `cloudflared tunnel --url http://localhost:8080`
or `ngrok http 8080`, and give Tribune Desk the `https://` address the tunnel prints. Posts are
kept in memory; a real CMS stores them in its database. In your own code prefer an official
Standard Webhooks library; `verify_signature` below shows what such a library checks.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import html
import json
import os
import re
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit

SECRET_PREFIX = "whsec_"
TOLERANCE_SECONDS = 300  # reject requests more than 5 minutes away from our clock
MAX_BODY_BYTES = 2 * 1024 * 1024  # an article is far smaller; refuse anything bigger (413)


class BodyTooLarge(Exception):
    """`Content-Length` above `MAX_BODY_BYTES`."""


class InvalidSignature(Exception):
    """The request is not signed by Tribune Desk, or is too old to trust."""


def check_secret(secret: str) -> bytes:
    """Return the signing key, or raise `ValueError` when the secret is not a `whsec_` secret.

    Call it at startup: a secret pasted without its trailing `=` would otherwise fail on every
    delivery and look like a bad request.
    """
    if not secret.startswith(SECRET_PREFIX):
        raise ValueError("the signing secret must start with whsec_")
    try:
        return base64.b64decode(secret.removeprefix(SECRET_PREFIX), validate=True)
    except binascii.Error as exc:
        raise ValueError(
            "the signing secret is not valid base64 after whsec_; copy it again in full"
        ) from exc


def verify_signature(
    secret: str,
    headers: Mapping[str, str],
    body: bytes,
    *,
    now: int | None = None,
    tolerance: int = TOLERANCE_SECONDS,
) -> None:
    """Raise `InvalidSignature` unless `body` carries a valid Standard Webhooks signature.

    `body` must be the raw request body, exactly as received, before any JSON parsing.
    """
    lower = {key.lower(): value for key, value in headers.items()}
    msg_id = lower.get("webhook-id")
    timestamp = lower.get("webhook-timestamp")
    signatures = lower.get("webhook-signature")
    if not msg_id or not timestamp or not signatures:
        raise InvalidSignature("missing signature headers")

    # 1. The timestamp must be close to our clock, so a recorded request cannot be replayed.
    try:
        sent = int(timestamp)
    except ValueError as exc:
        raise InvalidSignature("bad timestamp") from exc
    current = int(time.time()) if now is None else now
    if abs(current - sent) > tolerance:
        raise InvalidSignature("timestamp outside the tolerance")

    # 2. Signed content: "{webhook-id}.{webhook-timestamp}.{body}".
    signed = f"{msg_id}.{timestamp}.".encode() + body

    # 3. Key: the base64 part of the secret after "whsec_". HMAC-SHA256, then base64.
    key = check_secret(secret)
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()

    # 4. The header holds "v1,<signature>" entries separated by spaces (two during a secret
    #    rotation). One match is enough; compare in constant time.
    #    Compare bytes: `compare_digest` on text refuses non-ASCII input with a TypeError.
    for entry in signatures.split(" "):
        version, _, value = entry.partition(",")
        if version == "v1" and hmac.compare_digest(value.encode(), expected.encode()):
            return
    raise InvalidSignature("no signature matches")


# Players whose embeds stay (guide "A complete integration", Filtering the HTML): exact host and
# path prefix of the parsed `src`, so a look-alike host such as www.youtube.com.example.net and a
# trusted address hidden in another attribute do not pass.
TRUSTED_PLAYERS = {"www.youtube.com": "/embed/", "player.vimeo.com": "/video/"}
_ALLOWED: dict[str, frozenset[str]] = {
    **{t: frozenset() for t in ("p", "h2", "h3", "h4", "h5", "h6", "strong", "b", "em", "i", "u")},
    **{t: frozenset() for t in ("br", "hr", "ul", "ol", "li", "blockquote", "figcaption")},
    **{t: frozenset() for t in ("table", "thead", "tbody", "tfoot", "tr", "caption")},
    "th": frozenset({"colspan", "rowspan"}),
    "td": frozenset({"colspan", "rowspan"}),
    "a": frozenset({"href", "target", "rel", "title"}),
    "img": frozenset({"src", "alt", "width", "height"}),  # plus every data-td-* attribute
    "figure": frozenset({"class"}),
    "iframe": frozenset(
        {"src", "width", "height", "frameborder", "allowfullscreen", "allow", "title"}
    ),
}
_VOID = frozenset({"br", "hr", "img"})
# Removed together with everything inside them; any other unknown tag loses only the tag.
_DROP_WITH_CONTENT = frozenset(
    {
        "script",
        "style",
        "object",
        "embed",
        "form",
        "svg",
        "math",
        "template",
        "noscript",
        "textarea",
        "select",
        "iframe",
        "title",
        "head",
    }
)
_URL_ATTRS = frozenset({"href", "src"})
_SAFE_SCHEMES = frozenset({"", "http", "https", "mailto"})
_CONTROL = re.compile(r"[\x00-\x20\x7f]+")


def safe_url(value: str) -> bool:
    """True for a relative address, a `#` anchor, or `http`, `https` and `mailto`. Browsers drop
    whitespace and control characters inside a scheme, so `java<TAB>script:` is checked as
    `javascript:`; entities were already decoded by the parser."""
    return urlsplit(_CONTROL.sub("", value)).scheme.lower() in _SAFE_SCHEMES


def trusted_player(src: str) -> bool:
    if any(c == chr(92) or c.isspace() or ord(c) < 32 for c in src):
        return False  # a backslash or a space is read differently by browsers
    parts = urlsplit(src)
    host = parts.hostname or ""
    prefix = TRUSTED_PLAYERS.get(host)
    return (
        parts.scheme == "https"
        and parts.netloc.lower() == host  # no port, no user name
        and prefix is not None
        and parts.path.startswith(prefix)
    )


class _Sanitizer(HTMLParser):
    """Allow-list filter on the standard library's HTML parser: what is not on `_ALLOWED` goes.
    Text is escaped again on output, attributes are rebuilt from their decoded values."""

    # Only `script` and `style` hold raw text here. Newer and patched versions of `html.parser`
    # also read `iframe`, `textarea` and others as raw text; the filter parses their content as
    # markup on every version and filters it like the rest of the body.
    CDATA_CONTENT_ELEMENTS = ("script", "style")
    RCDATA_CONTENT_ELEMENTS = ()

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self._skip: str | None = None  # tag whose content is being dropped
        self._depth = 0
        self._label = False  # inside the AI label block, kept as it is
        self._players = 0  # kept iframes already closed on output, whose `</iframe>` is still due

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._skip is not None:
            self._depth += tag == self._skip
            return
        names = [n for n, _ in attrs]
        if (
            tag == "script"
            and ("data-hf-provenance" in names)
            and dict(attrs).get("type") == "application/ld+json"
        ):
            self._label = True
            self.out.append('<script type="application/ld+json" data-hf-provenance>')
            return
        if tag == "iframe" and names.count("src") == 1 and trusted_player(dict(attrs)["src"] or ""):
            # Closed at once, so a missing `</iframe>` does not swallow the rest of the body.
            self.out.append(self._tag(tag, attrs) + "</iframe>")
            self._players += 1
            return
        if tag in _DROP_WITH_CONTENT:
            if tag not in _VOID:
                self._skip, self._depth = tag, 1
            return
        if tag in _ALLOWED:
            self.out.append(self._tag(tag, attrs))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _VOID:
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if self._skip is not None:
            if tag == self._skip:
                self._depth -= 1
                if self._depth == 0:
                    self._skip = None
            return
        if tag == "iframe" and self._players:
            self._players -= 1  # already closed on output
        elif tag == "script" and self._label:
            self._label = False
            self.out.append("</script>")
        elif tag in _ALLOWED and tag not in _VOID and tag != "iframe":  # a stray `</iframe>` goes
            self.out.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if self._skip is None:
            # The label is JSON from Tribune Desk; `<` is escaped so it cannot end the element.
            self.out.append(
                data.replace("<", "\\u003c") if self._label else html.escape(data, quote=False)
            )

    def _tag(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        allowed = _ALLOWED[tag]
        kept = []
        for name, value in attrs:
            if name not in allowed and not (tag == "img" and name.startswith("data-td-")):
                continue
            if name in _URL_ATTRS and not safe_url(value or ""):
                continue
            kept.append(name if value is None else f'{name}="{html.escape(value, quote=True)}"')
        return f"<{tag}{''.join(' ' + a for a in kept)}>"


def filter_html(body: str) -> str:
    """Filter `html` with an allow list (guide "A complete integration", Filtering the HTML):
    no `on*` or `style` attributes, no `javascript:` or `data:` addresses, `script` and other
    active elements removed with their content (the AI label block stays), embeds only from a
    trusted player. Run it on every delivery: a delivery arrives with no editor logged in, so a
    filter that depends on the current user's rights may treat it differently. In your own code
    prefer a maintained sanitizer (for Python, `nh3`); this one shows what it must do."""
    parser = _Sanitizer()
    parser.feed(body)
    parser.close()
    return "".join(parser.out)


def publication_state(post: dict, publication: object, now: int) -> tuple[str, str | None]:
    """The post's state after a delivery with `publication` (guide 1, "Publication mode").

    `draft`, `scheduled` (until `at`) or `published`. A published post is never unpublished;
    a time already past is published at once; a field that cannot be read is ignored, like any
    field you do not know. Returns (state, at), `at` in UTC for a scheduled post.
    """
    state, at = post.get("state", "draft"), post.get("publish_at")
    if state == "published" or not isinstance(publication, dict):
        return state, at
    mode = publication.get("mode")
    if mode in ("draft", "publish"):
        return ("draft" if mode == "draft" else "published"), None
    try:
        moment = datetime.fromisoformat(str(publication.get("at")).replace("Z", "+00:00"))
    except ValueError:
        return state, at
    if mode != "schedule" or moment.tzinfo is None:
        return state, at
    if moment.timestamp() <= now:
        return "published", None
    return "scheduled", moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def handle_delivery(
    body: bytes,
    headers: Mapping[str, str],
    *,
    secret: str,
    store: dict[str, dict],
    now: int | None = None,
) -> dict:
    """Verify one delivery, make or update its draft, and return the answer for Tribune Desk.

    The same `article_id` comes again when an editor sends the article again: update the post
    made the first time instead of making a second one. A repeated attempt of one send (same
    `webhook-id`) lands here too and only updates the same post.
    """
    verify_signature(secret, headers, body, now=now)
    article = json.loads(body)
    if not isinstance(article, dict):
        raise ValueError("the body is not a JSON object")
    article_id = article["article_id"]
    sent_at = datetime.fromisoformat(article["sent_at"])
    existing = store.get(article_id)
    post_id = existing["cms_post_id"] if existing else str(len(store) + 1)
    edit_url = f"https://cms.example.com/posts/{post_id}/edit"
    if existing and sent_at < existing["sent_at"]:
        # An attempt of an older send that arrived after a newer one: keep the newer post.
        return {"cms_post_id": post_id, "status": "updated", "edit_url": edit_url}
    current = int(time.time()) if now is None else now
    state, publish_at = publication_state(existing or {}, article.get("publication"), current)
    store[article_id] = {
        "cms_post_id": post_id,
        "sent_at": sent_at,
        "title": article["title"],
        "html": filter_html(article["html"]),
        "excerpt": article.get("excerpt"),
        "featured_image_url": (article.get("featured_image") or {}).get("url"),
        # A scheduled post is published at `publish_at` by your CMS's own scheduler.
        "state": state,
        "publish_at": publish_at,
    }
    return {
        "cms_post_id": post_id,
        "status": "updated" if existing else "created",
        "permalink": None,  # the public address is reported by level 2
        "edit_url": edit_url,
        # The post's state after this delivery, so the editor sees what really happened.
        "publication": {
            "status": state,
            "at": publish_at if state == "scheduled" else None,
        },
    }


def content_length(value: str | None) -> int:
    """Return the body length from a `Content-Length` header, or raise `ValueError`.

    Only ASCII digits are accepted: `int()` alone would also take signs, spaces and digits of
    other scripts, and an unhandled error would drop the connection instead of answering 400.
    """
    if value is None:
        return 0
    if not (value.isascii() and value.isdigit()):
        raise ValueError("invalid Content-Length")
    length = int(value)
    if length > MAX_BODY_BYTES:
        raise BodyTooLarge(length)
    return length


def main() -> None:
    secret = os.environ["TD_WEBHOOK_SECRET"]
    check_secret(secret)  # fail at startup, not on every delivery
    port = int(os.environ.get("PORT", "8080"))
    store: dict[str, dict] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            try:
                body = self.rfile.read(content_length(self.headers.get("Content-Length")))
                answer = handle_delivery(body, dict(self.headers), secret=secret, store=store)
            except BodyTooLarge:
                self._reply(413, {"error": "body too large"})
                return
            except InvalidSignature:
                self._reply(401, {"error": "invalid signature"})
                return
            except (ValueError, KeyError, TypeError):
                self._reply(400, {"error": "invalid body"})
                return
            self._reply(200, answer)

        def _reply(self, status: int, data: dict) -> None:
            payload = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    HTTPServer(("", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
