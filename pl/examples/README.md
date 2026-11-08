<!-- translated-from: examples/README.md sha256:3c65702e6aa0b501 -->
# Przykłady

Minimalni klienci dla pierwszych dwóch poziomów, w Pythonie, wyłącznie z biblioteką standardową (Python 3.10 lub nowszy). Są testowani na prawdziwym kontrakcie przy każdej zmianie API.

| Plik | Poziom | Co pokazuje |
|---|---|---|
| `python/level1_receiver.py` | 1. Dostawa artykułu | weryfikację podpisu, tworzenie lub aktualizację szkicu, odpowiedź z wynikiem |
| `python/level2_link_back.py` | 2. Link zwrotny | zgłaszanie, gdzie artykuł został opublikowany |
| `payloads/article-delivered.json` | 1 i 3 | kompletne body dostawy, ze wszystkimi polami |
| `payloads/article-delivery-result.json` | 1 | odpowiedź na dostawę |
| `vectors/webhook-signature.json` | 1 | wektory testowe podpisu: przepuść każdy przez swoją weryfikację i porównaj z `valid` |

Wszystkie nazwy, adresy i identyfikatory w próbkach są zmyślone. Przewodnik dla każdego poziomu jest w [`guide/`](../guide).
