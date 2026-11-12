<!-- translated-from: guide/1-article-delivery.md sha256:d801ca930a0fd790 -->
# Poziom 1 – Dostawa artykułu

## Webhook dostawy artykułu

To jedyne wywołanie, które Tribune Desk kieruje do ciebie: gdy redaktor kliknie „Wyślij do CMS”, Tribune Desk wysyła artykuł na adres webhooka ustawiony dla twojej organizacji. Dokument OpenAPI opisuje je w sekcji `webhooks` jako `article.delivered`. Twój webhook nie potrzebuje żadnego tokenu z tego API; to osobny adres po twojej stronie.

**Adres webhooka.** Ustawia go dla twojej organizacji osoba kontaktowa w Tribune Desk albo użytkownik redakcji w Ustawieniach Tribune Desk, w sekcji Integracje; żadna trasa tego API go nie zmienia. Musi to być `https://` na publicznym hoście (port dowolny); `http://`, adresy prywatne i `localhost` są odrzucane. Przekierowania nie są obsługiwane. Żeby wypróbować odbiornik na własnym komputerze, postaw przed nim tunel (na przykład `cloudflared tunnel` albo `ngrok http 8080`) i podaj adres `https://`, który wypisze.

**Kilka organizacji pod jednym adresem.** Każda treść niesie `org_code`, ale zanim jej zaufasz, potrzebujesz właściwego sekretu podpisu. Lepiej użyć osobnego adresu dla każdej organizacji (na przykład `/td/webhook/{org_code}`). Przy jednym wspólnym adresie odczytaj `org_code` z surowej treści, wybierz sekret tej organizacji, zweryfikuj podpis na tych samych surowych bajtach i dopiero wtedy działaj na treści.

**Żądanie.** `POST` z treścią JSON (`ArticleDelivery`) i tymi nagłówkami:

- `webhook-id`, `webhook-timestamp`, `webhook-signature`: podpis żądania (zob. [Weryfikacja podpisu](#weryfikacja-podpisu)). Każda dostawa jest podpisana: organizacja bez sekretu podpisu nie dostaje dostaw, więc żądanie bez tych nagłówków nie pochodzi od Tribune Desk. Sprawdź podpis i odpowiedz `401`, gdy weryfikacja się nie powiedzie; to jedyny dowód, że żądanie pochodzi od Tribune Desk.
- `X-Delivery-Id`: taki sam dla każdej próby jednej wysyłki, więc możesz odrzucać duplikaty. Równy `webhook-id`.
- `X-Delivery-Attempt`: numer próby, liczony od 1.
- `User-Agent`: `ArticleWriter/2`. Dostawy nie przychodzą ze stałego adresu IP, więc nie filtruj po adresie; nadawcę potwierdza podpis.

**Twoja odpowiedź.** Dowolny `2xx` w ciągu 30 sekund oznacza dostarczenie. Po błędzie sieci, przekroczeniu czasu, `5xx`, `408`, `425` lub `429` Tribune Desk ponawia próbę po 2, 10, 30, 120, 360 i 840 minutach (około doby). Każdy inny status (inny `4xx` albo `3xx`: przekierowania nie są obsługiwane) od razu kończy wysyłkę. Ten sam artykuł przychodzi ponownie z tym samym `article_id`, gdy redaktor wyśle go jeszcze raz: zaktualizuj wpis utworzony za pierwszym razem. Odpowiadaj `401` tylko przy podpisie, który się nie weryfikuje: każdy `4xx` kończy wysyłkę na dobre, więc odbiornik, którego zegar rozjechał się o więcej niż 5 minut, gubi artykuły. Pilnuj synchronizacji zegara.

**Kolejność wysyłek.** Nowsza wysyłka tego samego artykułu anuluje czekające ponowienia starszej, a każda próba niesie bieżący stan artykułu. Próba starszej wysyłki, która była już w drodze, może jednak dotrzeć po nowszej: zapamiętuj ostatnio zastosowane `sent_at` dla każdego `article_id` i pomijaj treść ze starszym `sent_at`. `sent_at` to chwila, w której redaktor wysłał artykuł, ta sama w każdej próbie tej wysyłki; czas samej próby to `webhook-timestamp`.

**Zapisuj pod unikalnym kluczem.** Dwie próby jednej wysyłki mogą na siebie zachodzić (Tribune Desk przestaje czekać po 30 sekundach i ponawia później, choć twoja pierwsza odpowiedź jeszcze powstaje). Trzymaj `article_id` jako unikalny w bazie i blokuj wiersz na czas zapisu, inaczej powstaną dwa wpisy.

**Poziomy.** Nie potrzebujesz wszystkich pól, a każdy poziom działa bez tych powyżej. Poziom 1 (odbiór artykułu) tworzy szkic wpisu z `title`, `html`, `excerpt` i `featured_image`. Poziom 2 (link zwrotny) informuje Tribune Desk, gdzie wpis został opublikowany, aby inne artykuły mogły do niego linkować: odpowiedz z `permalink`. Poziom 3 (pełna treść) korzysta z tych samych dostaw z większą liczbą pól: linki wewnętrzne i boks „Czytaj więcej”, SEO, autor, pochodzenie AI. Poziom 4 (biblioteka mediów) ponownie wykorzystuje pliki, które twój CMS już przechowuje. Pola oznaczone jako *opcjonalne* to dodatki redakcyjne (wpisy do mediów społecznościowych, alternatywne tytuły, fakty), z których możesz skorzystać albo je pominąć. Nowe pola mogą pojawić się w wersji minor, więc ignoruj te, których nie znasz.

## Poziom 1 bez publicznego endpointu: tryb odczytu

Gdy twój CMS nie może przyjmować żądań z internetu, superadmin przełącza organizację w tryb odczytu. „Wyślij do CMS” nie wysyła wtedy do ciebie żadnego żądania. Zamiast tego:

1. Odpytuj `GET /v3/cms/changes` tokenem z zakresem `articles:read`. Wysłany artykuł pojawia się jako zmiana rodzaju `article_sent` ze swoim `article_id`. Token widzi tylko rodzaje odpowiadające jego zakresom: `article_sent` wymaga `articles:read`, każdy inny rodzaj `media:read`; kursor i tak przesuwa się za rodzaje, których nie widzisz. Tryb odczytu wymaga integracji włączonej przez superadmina.
2. Pobierz artykuł przez `GET /v3/cms/articles/{article_id}`. Treść to ten sam `ArticleDelivery`, który niesie webhook, zbudowany z bieżącego stanu artykułu, z `sent_at` wysyłki. Nagłówek `X-Delivery-Id` wskazuje tę wysyłkę; zachowaj go. Artykuł, który nigdy nie został wysłany, daje `404`.
3. Utwórz lub zaktualizuj wpis, a potem zgłoś wynik przez `POST /v3/cms/articles/{article_id}/result` tokenem z zakresem `articles:write`. Treść (`ArticleResultReport`) to to, czym odpowiedziałby twój webhook, plus `delivery_id`: `X-Delivery-Id` z kroku 2. Z nim wynik zamyka dokładnie tę wysyłkę; jeśli zastąpiła ją nowsza wysyłka artykułu, dostajesz `409` ze `state_conflict` i nic nie zostaje zapisane, więc pobierz artykuł jeszcze raz. Bez `delivery_id` wynik zamyka najnowszą czekającą wysyłkę. Jeśli twój CMS nie mógł przyjąć artykułu, wyślij zamiast tego `error` z krótkim powodem: redaktor zobaczy wysyłkę jako nieudaną z tym tekstem. W odróżnieniu od odpowiedzi webhooka treść jest walidowana: pole złego typu daje `422`. Pole dobrego typu, którego Tribune Desk nie zapisał, jest na liście `ignored_fields` odpowiedzi. Artykuł, który nigdy nie został wysłany, daje `409` i nic nie zostaje zapisane. Ponowne zgłoszenie wyniku jest bezpieczne.
4. Po `410 cursor_expired` z `GET /changes` token bez `media:write` nie uruchomi resynchronizacji. Pobierz listę wysyłek, które wciąż czekają, przez `GET /v3/cms/articles/awaiting` (`articles:read`, najstarsze pierwsze, strony przez `next_cursor`), obsłuż każdą jak w krokach 2 i 3, a potem odpytuj `GET /changes` od nowa, bez kursora. Odpytanie bez kursora zaczyna się od teraz i nie zwraca historii, niezależnie od zakresów tokenu; wysyłka zrobiona między ostatnią stroną `GET /articles/awaiting` a tym odpytaniem nadal jest na tamtej liście, więc przeczytaj ją raz jeszcze po odpytaniu. `GET /articles/awaiting` stronicuje według czasu wysyłki: wysyłka zrobiona w trakcie stronicowania pojawia się na późniejszej stronie, a wysyłka, dla której zgłosisz wynik, znika bez przesuwania pozostałych. Czytaj, dopóki `next_cursor` nie jest `null`.

## Weryfikacja podpisu

Tribune Desk podpisuje każdą dostawę zgodnie ze specyfikacją [Standard Webhooks](https://www.standardwebhooks.com/), więc zamiast pisać weryfikację samodzielnie możesz użyć jednej z jej gotowych bibliotek. Sekret podpisu dla twojej organizacji generuje superadmin; zaczyna się od `whsec_` i jest pokazywany jeden raz. Sekret podpisu nie jest poświadczeniem do żadnej trasy tego API.

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
| `sent_at` | 1 | Kiedy redaktor wykonał tę wysyłkę (ISO 8601); to samo w każdej jej próbie. Pomiń treść, której `sent_at` jest starsze niż ostatnio zastosowane. |
| `title` | 1 | Tytuł artykułu. Nie jest powtarzany w `html`. |
| `html` | 1 | Treść artykułu jako HTML, bez tytułu. Linki wewnętrzne są już rozwiązane (zob. `internal_links`). |
| `excerpt` | 1 | Krótkie podsumowanie artykułu na zajawkę wpisu (wybrany meta description); null, gdy go nie ma. |
| `featured_image` | 1 | Obraz główny: ten sam obiekt co pierwszy element `generated_images`; null, gdy artykuł nie ma obrazów. |
| `metadata` | 1 | Skąd pochodzi artykuł. |
| `language` | 1 | Język, w którym pisze redakcja: znacznik BCP 47 do 16 znaków (dziś `pl` lub `en`). Pomijane, gdy nie jest ustawiony. |
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

## Treść HTML

`html` to treść artykułu taka, jaką zostawili autor i redaktor. Tribune Desk nie zawęża jej do stałego zestawu elementów: redaktor może edytować surowy HTML. Traktuj ją jak treść od zaufanego redaktora i przepuść przez filtr, którego twój CMS używa dla treści redaktorów.

- **Typowe elementy:** `h2`, `h3`, `p`, `strong`, `b`, `em`, `i`, `br`, `ul`, `ol`, `li`, `blockquote` i `a`. Nagłówka nie ma w `html`: jest w `title`.
- **Linki:** `<a href="…">`; gdy redakcja otwiera linki w nowej karcie, `target="_blank" rel="noopener"`; link sponsorowany ma `rel="sponsored"`. Linki do innych artykułów redakcji opisuje poziom 3.
- **Bez mediów w treści:** Tribune Desk nie wstawia do `html` elementów `img`, `figure` ani `iframe`; obrazy przychodzą jako `featured_image` i `generated_images`. Redaktor może jednak wkleić embed ręcznie.
- **Blok etykiety AI:** gdy redakcja oznacza treści AI, `html` kończy się blokiem `<script type="application/ld+json" data-hf-provenance>…</script>`, tym samym oświadczeniem co `ai_provenance` (zob. poziom 3). Zostaw go, jeśli twój CMS na to pozwala, albo usuń i wstaw `ai_provenance` do nagłówka strony.

## Pola twojej odpowiedzi

Treść twojej odpowiedzi (`ArticleDeliveryResult`) jest opcjonalna: sam `2xx` oznacza dostarczenie. Wyślij ją jako `application/json`, do 64 KB. Tribune Desk odczytuje każde pole osobno i ignoruje pole niezgodne z jego typem. Pole, które pominiesz, zachowuje wartość zapisaną wcześniej przez Tribune Desk: odpowiedź z samym `edit_url` nie kasuje `cms_post_id` z wcześniejszej odpowiedzi.

| Pole | Poziom | Znaczenie |
|---|---|---|
| `cms_post_id` | 1 | Twój identyfikator wpisu, jako tekst. Tribune Desk zapisuje go przy artykule. |
| `status` | 1 | `created`, `updated` albo `skipped_already_published`, gdy nie ruszyłeś już opublikowanego wpisu. Informacyjne: Tribune Desk obecnie na nie nie reaguje. |
| `edit_url` | 1 | Adres `http(s)`, pod którym redaktor edytuje wpis; wyświetlany jako „Edytuj w CMS”. Inne schematy są ignorowane. Dostawa to wywołanie serwer–serwer bez zalogowanego redaktora, więc buduj adres bez sprawdzania uprawnień bieżącego użytkownika: funkcja CMS-a zwracająca link edycji dla bieżącego użytkownika (w WordPressie `get_edit_post_link()`) nic tam nie zwróci. |
| `permalink` | 2 | Publiczny adres wpisu. Tribune Desk używa go do linkowania do tego artykułu z innych artykułów. |
| `featured_image` | 4 | Załącznik utworzony z obrazu głównego, aby Tribune Desk mógł go następnym razem użyć ponownie. |
| `social_queue_exclude` | 2 | `true` trzyma wpis z dala od kolejki Facebooka w Tribune Desk, `false` przywraca go; ta sama flaga co w linku zwrotnym. Wysyłaj ją razem z `permalink`, gdy publikujesz od razu, żeby oznaczony wpis nigdy nie trafił do kolejki. Pomiń ją, żeby zachować zapisaną wartość. |
| `post_id` | – | Przestarzały (wycofywany): to samo co `cms_post_id`, odczytywany tylko wtedy, gdy tego brak. |

## Skąd pochodzą obrazy

Adresy URL obrazów w dostawach pochodzą z magazynu plików Tribune Desk albo z twojego CMS-a (obraz, który twój CMS już ma). Pobieraj obrazy tylko z tych hostów i odrzucaj każdy inny adres. `GET /v3/cms/status` (z `articles:read` lub `media:read`) i `GET /v3/cms/settings` zwracają je jako `image_hosts`; lista nigdy nie jest pusta, więc pustą traktuj jako błąd i niczego nie pobieraj. Bez tokenu dopuszczaj hosty magazynu Tribune Desk, które poda ci osoba kontaktowa, domenę twojej organizacji i host twojego webhooka. Jeśli możesz, pobieraj w tle: odpowiedź musi przyjść w ciągu 30 sekund, z obrazem czy bez.

## Przykład

Działający odbiornik w Pythonie, bez zależności, znajdziesz w [`examples/python/level1_receiver.py`](../../examples/python/level1_receiver.py). Weryfikuje podpis, tworzy lub aktualizuje szkic i odpowiada wynikiem. We własnym kodzie korzystaj z oficjalnej biblioteki Standard Webhooks; przykład pokazuje, co taka biblioteka sprawdza. Kompletna przykładowa treść żądania jest w [`examples/payloads/article-delivered.json`](../../examples/payloads/article-delivered.json).

## Gotowe, gdy

- „Wyślij do CMS” kliknięte przez redaktora tworzy szkic wpisu z `title`, `html`, `excerpt` i `featured_image`.
- Twoja odpowiedź niesie `cms_post_id`, `status` i `edit_url`, więc redaktor dostaje link „Edytuj w CMS”.
- Żądanie, którego podpis nie przechodzi weryfikacji albo którego `webhook-timestamp` odbiega o więcej niż 5 minut, dostaje `401` i niczego nie zmienia.
- Ponowna próba z tym samym `webhook-id` nie tworzy drugiego szkicu, a nowa wysyłka tego samego `article_id` aktualizuje wpis utworzony za pierwszym razem.
- Pola, których nie znasz, są ignorowane, a nie odrzucane; nie waliduj treści schematem, który odrzuca nieznane właściwości.
- Próba starszej wysyłki, która dotrze po nowszej, nie nadpisuje wpisu.
- Dwie nakładające się próby jednej wysyłki tworzą jeden wpis, nie dwa.
- Obrazy są pobierane tylko z hostów z `image_hosts`; obraz z innego hosta nie jest pobierany.

W trybie odczytu dodatkowo:

- Każdy wynik niesie `delivery_id` wysyłki, na którą odpowiada, albo `error`, gdy twój CMS nie mógł przyjąć artykułu.
- Po `409 state_conflict` na wynik artykuł jest pobierany ponownie i odpowiedź dotyczy nowszej wysyłki.
- Po `410 cursor_expired` wysyłki z listy `GET /v3/cms/articles/awaiting` są obsłużone, zanim `GET /v3/cms/changes` zostanie znowu odpytany bez kursora.
