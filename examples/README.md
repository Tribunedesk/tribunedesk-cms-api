# Examples

Minimal clients for the first two levels, in Python, with the standard library only (Python 3.10 or newer). They are tested against the real contract on every change of the API.

| File | Level | What it shows |
|---|---|---|
| `python/level1_receiver.py` | 1. Article delivery | verifying the signature, making or updating a draft, answering with the result |
| `python/level2_link_back.py` | 2. Link back | reporting where an article was published |
| `payloads/article-delivered.json` | 1 and 3 | a complete delivery body, with every field |
| `payloads/article-delivery-result.json` | 1 | an answer to a delivery |

All names, addresses and ids in the samples are made up. The guide for each level is in [`guide/`](../guide).
