<!-- translated-from: guide/1-article-delivery.md sha256:c6e9f504394195b4 -->
# Poziom 1 – Dostawa artykułu

## Webhook dostawy artykułu

To jedyne wywołanie, które Tribune Desk kieruje do ciebie: gdy redaktor kliknie „Wyślij do CMS”, Tribune Desk wysyła artykuł na adres webhooka ustawiony dla twojej organizacji. Dokument OpenAPI opisuje je w sekcji `webhooks` jako `article.delivered`. Twój webhook nie potrzebuje żadnego tokenu z tego API; to osobny adres po twojej stronie.

**Żądanie.** `POST` z treścią JSON (`ArticleDelivery`) i tymi nagłówkami:

- `webhook-id`, `webhook-timestamp`, `webhook-signature`: podpis żądania (zob. [Weryfikacja podpisu](#weryfikacja-podpisu)), wysyłany, gdy twoja organizacja ma sekret podpisu. Sprawdź go i odpowiedz `401`, gdy weryfikacja się nie powiedzie. Podpis to jedyny dowód, że żądanie pochodzi od Tribune Desk, więc poproś o sekret podpisu przed uruchomieniem integracji.
- `X-Delivery-Id`: taki sam dla każdej próby jednej wysyłki, więc możesz odrzucać duplikaty. Równy `webhook-id`.
- `X-Delivery-Attempt`: numer próby, liczony od 1.

**Twoja odpowiedź.** Dowolny `2xx` w ciągu 30 sekund oznacza dostarczenie. Po błędzie sieci, przekroczeniu czasu, `5xx`, `408`, `425` lub `429` Tribune Desk ponawia próbę po 2, 10, 30, 120, 360 i 840 minutach (około doby). Każdy inny status (inny `4xx` albo `3xx`: przekierowania nie są obsługiwane) od razu kończy wysyłkę. Ten sam artykuł przychodzi ponownie z tym samym `article_id`, gdy redaktor wyśle go jeszcze raz: zaktualizuj wpis utworzony za pierwszym razem.

**Poziomy.** Nie potrzebujesz wszystkich pól, a każdy poziom działa bez tych powyżej. Poziom 1 (odbiór artykułu) tworzy szkic wpisu z `title`, `html`, `excerpt` i `featured_image`. Poziom 2 (link zwrotny) informuje Tribune Desk, gdzie wpis został opublikowany, aby inne artykuły mogły do niego linkować: odpowiedz z `permalink`. Poziom 3 (pełna treść) korzysta z tych samych dostaw z większą liczbą pól: linki wewnętrzne i boks „Czytaj więcej”, SEO, autor, pochodzenie AI. Poziom 4 (biblioteka mediów) ponownie wykorzystuje pliki, które twój CMS już przechowuje. Pola oznaczone jako *opcjonalne* to dodatki redakcyjne (wpisy do mediów społecznościowych, alternatywne tytuły, fakty), z których możesz skorzystać albo je pominąć. Nowe pola mogą pojawić się w wersji minor, więc ignoruj te, których nie znasz.

## Poziom 1 bez publicznego endpointu: tryb odczytu

Gdy twój CMS nie może przyjmować żądań z internetu, superadmin przełącza organizację w tryb odczytu. „Wyślij do CMS” nie wysyła wtedy do ciebie żadnego żądania. Zamiast tego:

1. Odpytuj `GET /v3/cms/changes` tokenem z zakresem `articles:read`. Wysłany artykuł pojawia się jako zmiana rodzaju `article_sent` ze swoim `article_id`. Token widzi tylko rodzaje odpowiadające jego zakresom: `article_sent` wymaga `articles:read`, każdy inny rodzaj `media:read`; kursor i tak przesuwa się za rodzaje, których nie widzisz. Tryb odczytu wymaga integracji włączonej przez superadmina.
2. Pobierz artykuł przez `GET /v3/cms/articles/{article_id}`. Treść to ten sam `ArticleDelivery`, który niesie webhook, zbudowany z bieżącego stanu artykułu. Artykuł, który nigdy nie został wysłany, daje `404`.
3. Utwórz lub zaktualizuj wpis, a potem zgłoś wynik przez `POST /v3/cms/articles/{article_id}/result` tokenem z zakresem `articles:write`. Treść to ten sam `ArticleDeliveryResult`, którym odpowiedziałby twój webhook. W odróżnieniu od odpowiedzi webhooka jest ona walidowana: pole złego typu daje `422`. Artykuł, który nigdy nie został wysłany, daje `409` i nic nie zostaje zapisane. Ponowne zgłoszenie wyniku jest bezpieczne; redaktor widzi wysyłkę jako dostarczoną.

## Weryfikacja podpisu

Gdy twoja organizacja ma sekret podpisu, Tribune Desk podpisuje każdą dostawę zgodnie ze specyfikacją [Standard Webhooks](https://www.standardwebhooks.com/), więc zamiast pisać weryfikację samodzielnie możesz użyć jednej z jej gotowych bibliotek. Sekret podpisu dla twojej organizacji generuje superadmin; zaczyna się od `whsec_` i jest pokazywany jeden raz. Sekret podpisu nie jest poświadczeniem do żadnej trasy tego API.

1. Weź surową treść żądania jako bajty, przed jakimkolwiek parsowaniem JSON.
2. Zbuduj podpisywaną treść: `webhook-id`, kropka, `webhook-timestamp`, kropka, treść żądania: `{webhook-id}.{webhook-timestamp}.{body}`.
3. Kluczem jest zdekodowana z base64 część sekretu po `whsec_`. Oblicz HMAC-SHA256 podpisywanej treści tym kluczem i zakoduj wynik w base64.
4. `webhook-signature` zawiera jeden lub więcej podpisów oddzielonych spacjami, każdy w postaci `v1,`, po którym następuje wartość base64. Żądanie jest poprawne, gdy którykolwiek z nich jest równy twojemu; porównuj w stałym czasie.
5. Odrzuć żądanie, którego `webhook-timestamp` (sekundy Unix) różni się od twojego zegara o więcej niż 5 minut, aby nagranego żądania nie dało się później odtworzyć.

**Rotacja.** Organizacja może mieć jednocześnie dwa sekrety podpisu. Dopóki oba są aktywne, każde żądanie niesie dwa podpisy, po jednym na sekret: dodaj nowy sekret po swojej stronie, a potem superadmin unieważni stary. Każda próba jest podpisywana od nowa sekretami aktywnymi w danej chwili i z nowym znacznikiem czasu; `webhook-id` pozostaje taki sam dla każdej próby jednej wysyłki.

## Pola żądania

Pola oznaczone jako pomijane są nieobecne w treści, a nie `null`, gdy nie mają zastosowania.

| Pole | Poziom | Znaczenie |
|---|---|---|
| `article_id` | 1 | Identyfikator artykułu w Tribune Desk. Ponowne wysyłki tego samego artykułu niosą ten sam identyfikator: zaktualizuj wpis utworzony za pierwszym razem. |
| `org_code` | 1 | Kod redakcji w Tribune Desk. |
| `sent_at` | 1 | Kiedy wykonano tę wysyłkę (ISO 8601). |
| `title` | 1 | Tytuł artykułu. Nie jest powtarzany w `html`. |
| `html` | 1 | Treść artykułu jako HTML, bez tytułu. Linki wewnętrzne są już rozwiązane (zob. `internal_links`). |
| `excerpt` | 1 | Krótkie podsumowanie artykułu na zajawkę wpisu (wybrany meta description); null, gdy go nie ma. |
| `featured_image` | 1 | Obraz główny: ten sam obiekt co pierwszy element `generated_images`; null, gdy artykuł nie ma obrazów. |
| `metadata` | 1 | Skąd pochodzi artykuł. |
| `language` | 1 | Język, w którym pisze redakcja (np. `pl`). Pomijane, gdy nie jest ustawiony. |
| `internal_links` | 3 | Linki do innych artykułów redakcji umieszczone w `html`. |
| `link_placeholder_prefix` | 3 | Każdy link w `html` do artykułu, który nie ma jeszcze adresu w twoim CMS, to `link_placeholder_prefix`, po którym następuje `article_id` tego artykułu. Zastąp go swoim adresem tego artykułu albo zostaw sam tekst linku. Nie wpisuj prefiksu na sztywno. |
| `evergreen` | 3 | True, gdy artykuł pozostaje aktualny (nie jest związany z bieżącymi wiadomościami). |
| `generated_images` | 3 | Obrazy wygenerowane dla artykułu; pierwszy z nich to obraz główny. |
| `seo_title` | 3 | Wybrany tytuł SEO. |
| `meta_description` | 3 | Wybrany meta description. |
| `focus_keyphrase` | 3 | Fraza kluczowa SEO. |
| `ai_provenance` | 3 | Deklaracja pochodzenia AI, osadzona także w `html`; null, gdy redakcja wyłączyła oznaczanie. |
| `sent_by` | 3 | Kto kliknął „Wyślij do CMS”; null dla wysyłek automatycznych. |
| `author` | 3 | Kto zamówił artykuł. Użyj go jako autora wpisu, gdy nie da się dopasować `sent_by`. |
| `backlink_sources` | 3 | Starsze artykuły, które powinny linkować do tego. Pominięte = nie ruszaj istniejących linków; pusta lista = żaden artykuł nie powinien tu linkować. |
| `topic` | opcjonalne | Temat, na który napisano artykuł. |
| `alternative_titles` | opcjonalne | Inne propozycje tytułu; może być puste. |
| `twitter_posts` | opcjonalne | Proponowane wpisy na X. |
| `reel_captions` | opcjonalne | Proponowane podpisy do rolek. |
| `custom_content` | opcjonalne | Dodatkowe bloki tekstu zdefiniowane przez redakcję. |
| `facebook_title` | opcjonalne | Wybrany tytuł na Facebooka. Używaj go tylko na Facebooku, nie jako tytułu wpisu. |
| `facebook_titles` | opcjonalne | Wszystkie propozycje tytułu na Facebooka. |
| `facebook_teaser` | opcjonalne | Wybrany teaser na Facebooka. |
| `facebook_teasers` | opcjonalne | Wszystkie propozycje teasera na Facebooka. |
| `raw_facts` | opcjonalne | Fakty, na podstawie których napisano artykuł, po jednym w wierszu. |
| `related_topics` | opcjonalne | Tematy kontynuacji. |

## Pola twojej odpowiedzi

Treść twojej odpowiedzi (`ArticleDeliveryResult`) jest opcjonalna: sam `2xx` oznacza dostarczenie. Wyślij ją jako `application/json`, do 64 KB. Tribune Desk odczytuje każde pole osobno i ignoruje pole niezgodne z jego typem. Pole, które pominiesz, zachowuje wartość zapisaną wcześniej przez Tribune Desk: odpowiedź z samym `edit_url` nie kasuje `cms_post_id` z wcześniejszej odpowiedzi.

| Pole | Poziom | Znaczenie |
|---|---|---|
| `cms_post_id` | 1 | Twój identyfikator wpisu, jako tekst. Tribune Desk zapisuje go przy artykule. |
| `status` | 1 | `created`, `updated` albo `skipped_already_published`, gdy nie ruszyłeś już opublikowanego wpisu. Informacyjne: Tribune Desk obecnie na nie nie reaguje. |
| `edit_url` | 1 | Adres `http(s)`, pod którym redaktor edytuje wpis; wyświetlany jako „Edytuj w CMS”. Inne schematy są ignorowane. Dostawa to wywołanie serwer–serwer bez zalogowanego redaktora, więc buduj adres bez sprawdzania uprawnień bieżącego użytkownika: funkcja CMS-a zwracająca link edycji dla bieżącego użytkownika (w WordPressie `get_edit_post_link()`) nic tam nie zwróci. |
| `permalink` | 2 | Publiczny adres wpisu. Tribune Desk używa go do linkowania do tego artykułu z innych artykułów. |
| `featured_image` | 4 | Załącznik utworzony z obrazu głównego, aby Tribune Desk mógł go następnym razem użyć ponownie. |
| `post_id` | – | Przestarzały (wycofywany): to samo co `cms_post_id`, odczytywany tylko wtedy, gdy tego brak. |

## Skąd pochodzą obrazy

`GET /v3/cms/settings` zwraca listę `image_hosts`: hostów, z których pochodzą adresy URL obrazów w dostawach i w strumieniu zmian. Pobieraj obrazy tylko z tych hostów i odrzucaj każdy inny adres.

## Przykład

Działający odbiornik w Pythonie, bez zależności, znajdziesz w [`examples/python/level1_receiver.py`](../../examples/python/level1_receiver.py). Weryfikuje podpis, tworzy lub aktualizuje szkic i odpowiada wynikiem. We własnym kodzie korzystaj z oficjalnej biblioteki Standard Webhooks; przykład pokazuje, co taka biblioteka sprawdza. Kompletna przykładowa treść żądania jest w [`examples/payloads/article-delivered.json`](../../examples/payloads/article-delivered.json).

## Gotowe, gdy

- „Wyślij do CMS” kliknięte przez redaktora tworzy szkic wpisu z `title`, `html`, `excerpt` i `featured_image`.
- Twoja odpowiedź niesie `cms_post_id`, `status` i `edit_url`, więc redaktor dostaje link „Edytuj w CMS”.
- Żądanie, którego podpis nie przechodzi weryfikacji albo którego `webhook-timestamp` odbiega o więcej niż 5 minut, dostaje `401` i niczego nie zmienia.
- Ponowna próba z tym samym `webhook-id` nie tworzy drugiego szkicu, a nowa wysyłka tego samego `article_id` aktualizuje wpis utworzony za pierwszym razem.
- Pola, których nie znasz, są ignorowane, a nie odrzucane.
