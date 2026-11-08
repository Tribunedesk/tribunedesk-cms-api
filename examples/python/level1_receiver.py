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
import json
import os
import time
from collections.abc import Mapping
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

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
        return {"cms_post_id": post_id, "edit_url": edit_url}
    store[article_id] = {
        "cms_post_id": post_id,
        "sent_at": sent_at,
        "title": article["title"],
        "html": article["html"],
        "excerpt": article.get("excerpt"),
        "featured_image_url": (article.get("featured_image") or {}).get("url"),
        "state": "draft",
    }
    return {
        "cms_post_id": post_id,
        "status": "updated" if existing else "created",
        "permalink": None,  # a draft has no public address yet; see level 2
        "edit_url": edit_url,
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
