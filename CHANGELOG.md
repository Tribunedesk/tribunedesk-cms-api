# Changelog

Changes of the Tribune Desk CMS API contract, newest first. Versions follow [Versioning](VERSIONING.md).

## 3.3.0-draft – 2026-11-06

- `POST /v3/cms/articles/published`: optional `social_queue_exclude` per item keeps a post off the Tribune Desk Facebook queue. Leaving it out keeps the stored value.
- `X-Webhook-Secret` is no longer sent with deliveries. The signature (`webhook-id`, `webhook-timestamp`, `webhook-signature`) is the only authentication of a delivery.
- `POST /v2/cms/published-urls` is removed. Use `POST /v3/cms/articles/published`.

## 3.2.0-draft – 2026-11-04

- Deliveries are signed following Standard Webhooks (`webhook-id`, `webhook-timestamp`, `webhook-signature`) when the organization has a signing secret. `X-Webhook-Secret` is deprecated.
- Scopes `articles:read` and `articles:write` for `tdcms_` tokens.
- `POST /v3/cms/articles/published`: the link back with a `tdcms_` token. `POST /v2/cms/published-urls` is deprecated.
- Read mode: change kind `article_sent`, `GET /v3/cms/articles/{article_id}` and `POST /v3/cms/articles/{article_id}/result`.
- `link_placeholder_prefix` in `ArticleDelivery`.
- `image_hosts` in `GET /v3/cms/settings`.
- `GET /v3/cms/status` and `GET /v3/cms/changes` accept `articles:read`.

## 3.1.0-draft – 2026-11-03

- The `article.delivered` webhook is part of the contract, with `ArticleDelivery` and `ArticleDeliveryResult`.
- New fields `excerpt` and `featured_image` next to the existing ones.
- Tribune Desk stores `cms_post_id` and `edit_url` from your answer.

## 3.0.0-draft – 2026-10-31

- First version of `/v3/cms`: media sync (changes feed, new files, field changes, deletions, resync, held batches, settings, historical import).
