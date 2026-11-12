<!-- translated-from: guide/2-link-back.md sha256:2ccaa62f759f7fb5 -->
# Poziom 2 – Link zwrotny

## Zgłaszanie opublikowanego adresu

Gdy wpis utworzony z dostarczonego artykułu staje się publiczny, wywołaj `POST /v3/cms/articles/published` tokenem z zakresem `articles:write`. Wyślij `items`, od 1 do 100 na żądanie, każdy z `article_id` (z dostawy), `url` (publiczny adres `http(s)`) i opcjonalnie `published_at` (ISO 8601 ze strefą czasową; czas bez strefy kończy całe żądanie kodem `422`). Odpowiedź zawiera jeden wynik na każdy element, w tej samej kolejności: `ok`, `not_found` (nie ma takiego artykułu w organizacji tokenu) lub `invalid_url`. Starsi klienci mogą wciąż oczekiwać `forbidden`; ten status nie jest już zwracany. Błędny element nie powoduje niepowodzenia pozostałych. Trasa dzieli limit żądań tokenu (600 żądań na minutę).

Odpowiedź na dostawę z `permalink` (i `social_queue_exclude`, niżej) robi to samo dla wpisu opublikowanego od razu; tej trasy używaj dla wpisów publikowanych później. Gdy wpis zostanie wycofany z publikacji, Tribune Desk zachowuje ostatni adres: dziś żadna trasa go nie cofa, więc wyślij nowy adres, gdy wpis wróci albo się przeniesie.

## Wpis nie na Facebooka

Jeśli Twój CMS ma ustawienie, które nie pozwala wpisowi trafić na Facebooka, wysyłaj je w każdym elemencie jako `social_queue_exclude`. Przy `true` Tribune Desk nie dodaje artykułu do swojej kolejki na Facebooka, a artykuł, który już w niej czeka, zostaje zdjęty ze wszystkich kolejek; opublikowane już posty zostają. Przy `false` wpis może znów trafić na Facebooka: artykuł, który nigdy nie trafił do kolejki i został opublikowany najwyżej 48 godzin temu, wchodzi do niej jak nowy, a każdy inny tylko wtedy, gdy doda go redaktor. Redaktor nadal może ręcznie dodać wykluczony artykuł. Pominięcie pola zachowuje zapisaną wartość, więc klient, który tego pola nie zna, nigdy go nie kasuje. Gdy Twój CMS ma takie ustawienie, wysyłaj pole za każdym razem, także jako `false`; inaczej zdjęcie ustawienia nigdy nie dotrze do Tribune Desk. Gdy ustawienie zmieni się w opublikowanym wpisie, wyślij element ponownie; ten sam adres nie zmienia niczego innego.

Działający klient w Pythonie znajdziesz w [`examples/python/level2_link_back.py`](../../examples/python/level2_link_back.py).

## Gotowe, gdy

- Każdy wpis utworzony z dostarczonego artykułu jest zgłaszany, gdy tylko stanie się publiczny: przez `permalink` w odpowiedzi na dostawę albo przez `POST /v3/cms/articles/published`.
- Ponowne zgłoszenie tego samego wpisu niczego nie psuje, a element z odpowiedzią `not_found` lub `invalid_url` jest logowany, a nie ponawiany bez zmian.
- Twój token do tej trasy to token `tdcms_` z zakresem `articles:write`, a nie sekret webhooka.
- Jeśli twój CMS ma ustawienie, które trzyma wpis z dala od Facebooka, każde zgłoszenie niesie `social_queue_exclude`, także `false`.
