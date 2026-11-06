# Level 1 – Article delivery

## Article delivery webhook

This is the one call Tribune Desk makes to you: when an editor clicks “Send to CMS”, Tribune Desk sends the article to the webhook address set for your organization. The OpenAPI document describes it under `webhooks` as `article.delivered`. Your webhook needs no token from this API; it is a separate address on your side.

**The request.** A `POST` with a JSON body (`ArticleDelivery`) and these headers:

- `webhook-id`, `webhook-timestamp`, `webhook-signature`: the signature of the request (see [Verifying the signature](#verifying-the-signature)), sent when your organization has a signing secret. Check it and answer `401` when it does not verify. The signature is the only proof that a request comes from Tribune Desk, so ask for a signing secret before you go live.
- `X-Delivery-Id`: the same for every attempt of one send, so you can drop duplicates. Equal to `webhook-id`.
- `X-Delivery-Attempt`: the attempt number, starting at 1.

**Your answer.** Any `2xx` within 30 seconds means delivered. After a network error, a timeout, `5xx`, `408`, `425` or `429`, Tribune Desk tries again after 2, 10, 30, 120, 360 and 840 minutes (about a day). Any other status (another `4xx`, or a `3xx`: redirects are not followed) ends the send at once. The same article comes again with the same `article_id` when an editor sends it again: update the post you created the first time.

**Levels.** You do not need every field, and each level works without the ones above it. Level 1 (receive article) makes a draft post from `title`, `html`, `excerpt` and `featured_image`. Level 2 (link back) tells Tribune Desk where the post was published, so other articles can link to it: answer with `permalink`. Level 3 (full content) uses the same deliveries with more fields: internal links and the “read more” box, SEO, author, AI provenance. Level 4 (media library) reuses files your CMS already holds. Fields marked *optional* are editorial extras (social posts, alternative titles, facts) that you may use or ignore. New fields may appear in a minor version, so ignore the ones you do not know.

## Level 1 without a public endpoint: read mode

When your CMS cannot receive requests from the internet, a super admin switches the organization to read mode. “Send to CMS” then makes no request to you. Instead:

1. Poll `GET /v3/cms/changes` with a token that has `articles:read`. A sent article appears as a change of kind `article_sent` with its `article_id`. A token sees only the kinds of its scopes: `article_sent` needs `articles:read`, every other kind `media:read`; the cursor still moves past the kinds you do not see. Read mode needs the integration enabled by a super admin.
2. Fetch the article with `GET /v3/cms/articles/{article_id}`. The body is the same `ArticleDelivery` the webhook carries, built from the current state of the article. An article that was never sent gives `404`.
3. Create or update the post, then report the outcome with `POST /v3/cms/articles/{article_id}/result` and a token with `articles:write`. The body is the same `ArticleDeliveryResult` your webhook would answer with. Unlike a webhook answer it is validated: a field of the wrong type gives `422`. An article that was never sent gives `409` and nothing is stored. Repeating the result is safe; the editor sees the send as delivered.

## Verifying the signature

When your organization has a signing secret, Tribune Desk signs each delivery following the [Standard Webhooks](https://www.standardwebhooks.com/) specification, so you can use one of its ready libraries instead of writing the check yourself. A super admin generates the signing secret for your organization; it starts with `whsec_` and is shown once. The signing secret is not a credential for any route of this API.

1. Take the raw request body as bytes, before any JSON parsing.
2. Build the signed content: `webhook-id`, a dot, `webhook-timestamp`, a dot, the body: `{webhook-id}.{webhook-timestamp}.{body}`.
3. The key is the base64-decoded part of the secret after `whsec_`. Compute HMAC-SHA256 of the signed content with that key and encode the result in base64.
4. `webhook-signature` holds one or more signatures separated by spaces, each as `v1,` followed by the base64 value. The request is valid when any of them equals yours; compare in constant time.
5. Reject a request whose `webhook-timestamp` (Unix seconds) is more than 5 minutes away from your clock, so a recorded request cannot be replayed later.

**Rotation.** An organization can have two signing secrets at once. While both are active every request carries two signatures, one per secret: add the new secret on your side, then the super admin revokes the old one. Each attempt is signed again with the secrets active at that moment and a new timestamp; `webhook-id` stays the same for every attempt of one send.

## Fields of the request

Fields marked as omitted are absent from the body, not `null`, when they do not apply.

| Field | Level | Meaning |
|---|---|---|
| `article_id` | 1 | Tribune Desk id of the article. Repeated sends of the same article carry the same id: update the post you created the first time. |
| `org_code` | 1 | The newsroom's code in Tribune Desk. |
| `sent_at` | 1 | When this send was made (ISO 8601). |
| `title` | 1 | The article's headline. Not repeated in `html`. |
| `html` | 1 | The article body as HTML, without the headline. Internal links are already resolved (see `internal_links`). |
| `excerpt` | 1 | A short summary of the article for the post excerpt (the chosen meta description); null when there is none. |
| `featured_image` | 1 | The main image: the same object as the first entry of `generated_images`; null when the article has no images. |
| `metadata` | 1 | Where the article comes from. |
| `language` | 1 | The newsroom's writing language (e.g. `pl`). Omitted when not set. |
| `internal_links` | 3 | Links to other articles of the newsroom placed in `html`. |
| `link_placeholder_prefix` | 3 | Every link in `html` to an article that has no address in your CMS yet is `link_placeholder_prefix` followed by that article’s `article_id`. Replace it with your address of that article, or keep only the link text. Do not hard-code the prefix. |
| `evergreen` | 3 | True when the article stays current (not tied to news). |
| `generated_images` | 3 | Images made for the article; the first one is the main image. |
| `seo_title` | 3 | The chosen SEO title. |
| `meta_description` | 3 | The chosen meta description. |
| `focus_keyphrase` | 3 | The focus keyphrase for SEO. |
| `ai_provenance` | 3 | AI provenance statement, also embedded in `html`; null when the newsroom turned marking off. |
| `sent_by` | 3 | Who clicked "Send to CMS"; null for automatic sends. |
| `author` | 3 | Who ordered the article. Use it as the post author when `sent_by` cannot be matched. |
| `backlink_sources` | 3 | Older articles that should link to this one. Omitted = leave existing links alone; an empty list = no article should link here. |
| `topic` | optional | The topic the article was written on. |
| `alternative_titles` | optional | Other headline proposals; may be empty. |
| `twitter_posts` | optional | Proposed posts for X. |
| `reel_captions` | optional | Proposed captions for reels. |
| `custom_content` | optional | Extra text blocks defined by the newsroom. |
| `facebook_title` | optional | The chosen title for Facebook. Use it only on Facebook, not as the post title. |
| `facebook_titles` | optional | All title proposals for Facebook. |
| `facebook_teaser` | optional | The chosen teaser for Facebook. |
| `facebook_teasers` | optional | All teaser proposals for Facebook. |
| `raw_facts` | optional | Facts the article was written from, one per line. |
| `related_topics` | optional | Follow-up topics. |

## Fields of your answer

The body of your answer (`ArticleDeliveryResult`) is optional: a `2xx` alone means delivered. Send it as `application/json`, up to 64 KB. Tribune Desk reads each field on its own and ignores one that does not match its type. A field you leave out keeps the value Tribune Desk stored before: an answer with only `edit_url` does not erase the `cms_post_id` from an earlier answer.

| Field | Level | Meaning |
|---|---|---|
| `cms_post_id` | 1 | Your identifier of the post, as text. Tribune Desk stores it with the article. |
| `status` | 1 | `created`, `updated`, or `skipped_already_published` when you left an already published post alone. Informational: Tribune Desk does not act on it today. |
| `edit_url` | 1 | An `http(s)` address where the editor edits the post; shown as "Edit in CMS". Other schemes are ignored. The delivery is a server-to-server call with no editor logged in, so build the address without checking the current user's permissions: a CMS helper that returns the edit link for the current user (in WordPress `get_edit_post_link()`) returns nothing there. |
| `permalink` | 2 | The public address of the post. Tribune Desk uses it to link to this article from other articles. |
| `featured_image` | 4 | The attachment made from the featured image, so Tribune Desk can reuse it next time. |
| `post_id` | – | Deprecated: the same as `cms_post_id`, read only when that is absent. |

## Where images come from

`GET /v3/cms/settings` lists `image_hosts`: the hosts that image URLs in deliveries and in the change feed come from. Download images only from these hosts and refuse any other address.

## Example

A working receiver in Python, with no dependencies, is in [`examples/python/level1_receiver.py`](../examples/python/level1_receiver.py). It verifies the signature, makes or updates a draft and answers with the result. Prefer an official Standard Webhooks library in your own code; the example shows what such a library checks. A complete sample body is in [`examples/payloads/article-delivered.json`](../examples/payloads/article-delivered.json).

## Done when

- An editor's “Send to CMS” makes a draft post with `title`, `html`, `excerpt` and `featured_image`.
- Your answer carries `cms_post_id`, `status` and `edit_url`, so the editor gets an “Edit in CMS” link.
- A request whose signature does not verify, or whose `webhook-timestamp` is more than 5 minutes off, gets `401` and changes nothing.
- A repeated attempt with the same `webhook-id` makes no second draft, and a new send of the same `article_id` updates the post you made the first time.
- Fields you do not know are ignored, not rejected.
