<!-- translated-from: guide/2-link-back.md sha256:0203e9bf47733463 -->
# Poziom 2 – Link zwrotny

## Zgłaszanie opublikowanego adresu

Gdy wpis utworzony z dostarczonego artykułu staje się publiczny, wywołaj `POST /v3/cms/articles/published` tokenem z zakresem `articles:write`. Wyślij `items`, od 1 do 100 na żądanie, każdy z `article_id` (z dostawy), `url` (publiczny adres `http(s)`) i opcjonalnie `published_at` (ISO 8601 ze strefą czasową). Odpowiedź zawiera jeden wynik na każdy element, w tej samej kolejności: `ok`, `not_found` (nie ma takiego artykułu), `forbidden` (artykuł należy do innej organizacji niż token) lub `invalid_url`. Błędny element nie powoduje niepowodzenia pozostałych. Trasa dzieli limit żądań tokenu (600 żądań na minutę). Starsza trasa `POST /v2/cms/published-urls`, uwierzytelniana sekretem webhooka, jest przestarzała (wycofywana) i działa, dopóki każda integracja nie przejdzie na nową.

Odpowiedź na dostawę z `permalink` robi to samo dla wpisu opublikowanego od razu; tej trasy używaj dla wpisów publikowanych później.

Działający klient w Pythonie znajdziesz w [`examples/python/level2_link_back.py`](../../examples/python/level2_link_back.py).

## Gotowe, gdy

- Każdy wpis utworzony z dostarczonego artykułu jest zgłaszany, gdy tylko stanie się publiczny: przez `permalink` w odpowiedzi na dostawę albo przez `POST /v3/cms/articles/published`.
- Ponowne zgłoszenie tego samego wpisu niczego nie psuje, a element z odpowiedzią `not_found`, `forbidden` lub `invalid_url` jest logowany, a nie ponawiany bez zmian.
- Twój token do tej trasy to token `tdcms_` z zakresem `articles:write`, a nie sekret webhooka.
