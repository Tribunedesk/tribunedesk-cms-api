"""Level 2 of the Tribune Desk CMS API: report where delivered articles were published.

Contract: `POST /v3/cms/articles/published` with a `tdcms_` token that has `articles:write`.
Guide: guide/2-link-back.md.

Standard library only. Example:

    TD_CMS_TOKEN=tdcms_... python level2_link_back.py <article_id> <public url>
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

BASE_URL = "https://api.tribunedesk.com"


def build_request(base_url: str, token: str, items: list[dict]) -> urllib.request.Request:
    """The request for 1 to 100 items, each `{article_id, url, published_at?}`."""
    body = json.dumps({"items": items}).encode()
    return urllib.request.Request(
        f"{base_url.rstrip('/')}/v3/cms/articles/published",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )


def report_published(base_url: str, token: str, items: list[dict]) -> dict:
    """Send the items and return the answer: one `{article_id, status}` per item, in order.

    `status` is `ok`, `not_found`, `forbidden` or `invalid_url`. A bad item does not fail the
    others; log it rather than sending it again unchanged. On `429` wait `retry_after` seconds.
    """
    with urllib.request.urlopen(build_request(base_url, token, items), timeout=30) as response:
        return json.load(response)


def main() -> None:
    token = os.environ["TD_CMS_TOKEN"]
    article_id, url = sys.argv[1], sys.argv[2]
    now = datetime.now(timezone.utc).isoformat()  # noqa: UP017 - timezone.utc keeps Python 3.10
    item = {"article_id": article_id, "url": url, "published_at": now}
    print(json.dumps(report_published(BASE_URL, token, [item]), indent=2))


if __name__ == "__main__":
    main()
