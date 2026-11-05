# Level 2 – Link back

## Reporting the published address

When a post made from a delivered article goes public, call `POST /v3/cms/articles/published` with a token that has `articles:write`. Send `items`, 1 to 100 per request, each with `article_id` (from the delivery), `url` (the public `http(s)` address) and, optionally, `published_at` (ISO 8601 with a time zone). The answer has one result per item, in order: `ok`, `not_found` (no such article), `forbidden` (the article belongs to another organization than the token) or `invalid_url`. A bad item does not fail the others. The route shares the limit of the token (600 requests per minute). The older `POST /v2/cms/published-urls`, authenticated with the webhook secret, is deprecated and keeps working until every integration has moved.

Answering a delivery with `permalink` does the same for a post published at once; use this route for posts published later.

A working client in Python is in [`examples/python/level2_link_back.py`](../examples/python/level2_link_back.py).

## Done when

- Every post made from a delivered article is reported once it is public, either by `permalink` in the delivery answer or by `POST /v3/cms/articles/published`.
- Reporting the same post again does no harm, and an item answered `not_found`, `forbidden` or `invalid_url` is logged, not retried unchanged.
- Your token for this route is a `tdcms_` token with `articles:write`, not the webhook secret.
