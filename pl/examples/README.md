<!-- translated-from: examples/README.md sha256:76a905edd3fee3c9 -->
# Przykłady

Minimalni klienci dla pierwszych dwóch poziomów, w Pythonie, wyłącznie z biblioteką standardową (Python 3.10 lub nowszy). Są testowani na prawdziwym kontrakcie przy każdej zmianie API.

| Plik | Poziom | Co pokazuje |
|---|---|---|
| `python/level1_receiver.py` | 1. Dostawa artykułu | weryfikację podpisu, tworzenie lub aktualizację szkicu, odpowiedź z wynikiem |
| `python/level2_link_back.py` | 2. Link zwrotny | zgłaszanie, gdzie artykuł został opublikowany |
| `payloads/article-delivered.json` | 1 i 3 | kompletne body dostawy, ze wszystkimi polami |
| `payloads/article-delivery-result.json` | 1 | odpowiedź na dostawę |

Wszystkie nazwy, adresy i identyfikatory w próbkach są zmyślone. Przewodnik dla każdego poziomu jest w [`guide/`](../guide).
