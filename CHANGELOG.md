# Changelog

Changes of the Tribune Desk CMS API contract, newest first. Versions follow [Versioning](VERSIONING.md).

## 3.4.0-draft – 2026-11-07

- Every delivery is signed: an organization without a signing secret gets no deliveries.
- Schemas of what Tribune Desk sends no longer forbid unknown properties (`additionalProperties`); request bodies still do.
- `sent_at` is when the editor made the send, the same in every attempt (retries used to carry the time of the attempt).
- `ArticleDeliveryResult`: optional `social_queue_exclude`, stored before `permalink`.
- Read mode: `GET /v3/cms/articles/{article_id}` returns the `X-Delivery-Id` header; `POST /v3/cms/articles/{article_id}/result` takes `ArticleResultReport` with optional `delivery_id` and `error` and answers with `ignored_fields`; new `GET /v3/cms/articles/awaiting`.
- `DeliveryImage.cms_media_id` and `FeaturedImageResult.cms_media_id`: the file identifier as text. `cms_attachment_id` and `attachment_id` are deprecated.
- `GET /v3/cms/status` lists `image_hosts`.
- `409` descriptions name only the codes each route returns; `POST /result` documents `state_conflict` (it said `conflict`).
- Webhook headers are declared as parameters; `429` and `503` declare `Retry-After`; `GET /v3/cms/openapi.json` is in `paths`.
- A path id that is not a UUID gives `404 not_found` (it gave `422`).
- `POST /v3/cms/articles/published`: an article of another organization is `not_found`; `forbidden` is no longer returned.
- Retries honour `Retry-After` of your answer, up to one hour.

## 3.3.0-draft – 2026-11-06

- `POST /v3/cms/articles/published`: optional `social_queue_exclude` per item keeps a post off the Tribune Desk Facebook queue. Leaving it out keeps the stored value.
- **Breaking** (2026-11-06): `X-Webhook-Secret` is no longer sent with deliveries. The signature (`webhook-id`, `webhook-timestamp`, `webhook-signature`) is the only authentication of a delivery.
- **Breaking** (2026-11-06): `POST /v2/cms/published-urls` is removed. Use `POST /v3/cms/articles/published`.

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
