<!-- translated-from: README.md sha256:bf723a2942cf39ae -->
# Tribune Desk CMS API: przewodnik integracji

To API łączy system zarządzania treścią (CMS) z Tribune Desk, narzędziem redakcyjnym, które pisze artykuły. Twój CMS odbiera artykuły wysłane przez redaktorów, informuje Tribune Desk, gdzie zostały opublikowane, i może utrzymywać swoją bibliotekę mediów w synchronizacji. Klientem może być dowolny CMS; nic tutaj nie zakłada konkretnego produktu. Wtyczka Tribune Desk dla WordPress jest jedną z jego implementacji; nie potrzebujesz jej, żeby zbudować własną.

Przewodnik, przykłady i dokument OpenAPI znajdują się w publicznym repozytorium [tribunedesk/tribunedesk-cms-api](https://github.com/tribunedesk/tribunedesk-cms-api). Wersja angielska jest w [katalogu głównym repozytorium](https://github.com/tribunedesk/tribunedesk-cms-api).

W zakresie mediów API pozwala CMS-owi utrzymywać metadane jego plików multimedialnych (tytuł, tekst alternatywny, podpis, opis) w synchronizacji z Tribune Desk, w obu kierunkach. CMS jest klientem: pyta Tribune Desk o zmiany i wysyła własne. Tribune Desk nigdy nie wywołuje Twojego API (jedyne wywołanie, jakie wykonuje, to [webhook dostawy artykułu](guide/1-article-delivery.md#webhook-dostawy-artykułu)), ale pobiera adresy URL plików, które wysyłasz, więc muszą być publicznie dostępne do pobrania (bez logowania, bez ograniczeń IP).

## Poziomy integracji

Każdy poziom działa bez wyższych. Zacznij od poziomu 1, który zajmuje dzień pracy, a pozostałe dodawaj, gdy będą Ci potrzebne. Poziom 3 dodaje pola do tych samych dostaw co poziom 1; nie wymaga nowych tras.

| Poziom | Co robi Twój CMS | Czego używa | Co dostaje redakcja |
|---|---|---|---|
| [1. Dostawa artykułu](guide/1-article-delivery.md) | udostępnia endpoint i tworzy szkic wpisu z tytułu, HTML, zajawki i głównego obrazu | webhook `article.delivered` albo tryb odczytu | „Wyślij do CMS” |
| [2. Link zwrotny](guide/2-link-back.md) | zgłasza adres i datę publikacji | `POST /v3/cms/articles/published` | link w Tribune Desk; artykuł staje się celem linków |
| [3. Pełna treść](guide/3-full-content.md) | rozwiązuje linki wewnętrzne, zachowuje boks „Czytaj więcej”, SEO, autora, język, oznaczenie AI | pola poziomu 3 w dostawie | pełna jakość publikacji |
| [4. Biblioteka mediów](guide/4-media-library.md) | synchronizuje pliki i ich opisy w obu kierunkach | trasy media, settings, held, resync i backfill | jedna biblioteka |
| [5. Archiwum](guide/5-archive.md) | wysyła starsze artykuły | planowane | linki do archiwum |

Kontrakt opisuje [dokument OpenAPI](../openapi.json) (dostępny także pod `https://api.tribunedesk.com/v3/cms/openapi.json`). Jak zmieniają się wersje: [Wersjonowanie](VERSIONING.md). Co się zmieniło: [CHANGELOG](../CHANGELOG.md). Działający klienci w Pythonie: [poziom 1](../examples/python/level1_receiver.py) i [poziom 2](../examples/python/level2_link_back.py).

## Zbuduj to z Claude

Otwartoźródłowy plugin do Claude Code buduje i testuje integrację twojego CMS na wybranych przez ciebie poziomach. Czyta ten przewodnik w otagowanej wersji, pyta, czego potrzebujesz, mówi, o co poprosić Tribune Desk, pisze kod i sprawdza go na lokalnej atrapie Tribune Desk, zanim przyjdzie pierwsza prawdziwa dostawa. Gdy kontrakt się zmieni, wypisuje, co musi się zmienić w twojej integracji, i ją aktualizuje.

```
/plugin marketplace add tribunedesk/tribunedesk-cms-kit
/plugin install tribunedesk-integration@tribunedesk
```

Potem napisz: „Zbuduj mi integrację z Tribune Desk”. Plugin nie zamawia tokenów i niczego nie wdraża: konfiguracja po stronie Tribune Desk zostaje u twojej osoby kontaktowej (zobacz [O co poprosić Tribune Desk](#o-co-poprosić-tribune-desk)). W tym samym repozytorium, [tribunedesk/tribunedesk-cms-kit](https://github.com/tribunedesk/tribunedesk-cms-kit), jest `tdkit`: lokalna atrapa i testy zgodności, które uruchomisz także bez Claude. CMS napisany w PHP może korzystać z reguł protokołu z [tribunedesk/tribunedesk-cms-php](https://github.com/tribunedesk/tribunedesk-cms-php).

## Co działa dzisiaj

- **Działa już teraz:** `GET /v3/cms/status` i `GET /v3/cms/changes` (wymagają `media:read` lub `articles:read`), `GET /v3/cms/held` (wymaga `media:read`), `GET /v3/cms/articles/{article_id}` i `GET /v3/cms/articles/awaiting` (wymagają `articles:read`), `POST /v3/cms/articles/{article_id}/result` i `POST /v3/cms/articles/published` (wymagają `articles:write`),`POST /v3/cms/media`, `POST /v3/cms/media/fields`, `POST /v3/cms/media/{asset_id}/link`, `POST /v3/cms/media/push-existing`, `POST /v3/cms/media/deletions`, `POST /v3/cms/resync` i `POST /v3/cms/held/{held_id}/decision` (wymagają `media:write`), `GET /v3/cms/settings` i `PUT /v3/cms/settings` (wymagają `settings:read` i `settings:write`), `GET /v3/cms/backfill/requests` i `POST /v3/cms/backfill/requests/{request_id}/pages` (wymagają `backfill:write`) oraz `GET /v3/cms/openapi.json` (bez tokenu). Integrację dla Twojej organizacji włącza superadmin; pierwsze odpytanie jej nie włącza, ale przełącza Twoją organizację na to API (zob. Przejście na to API). Do tego czasu `state` w `/status` ma wartość `disabled`, a `GET /changes`, `/settings` i `POST /resync` odpowiadają `409` z `state_conflict`. Po włączeniu `state` ma wartość `active` albo `stalled`, gdy przez 24 godziny nie było odpytania. `last_changes_poll_at` i `pending_changes` mają wartość `null`, dopóki integracja jest wyłączona. `held_batches` liczy partie czekające na decyzję (`null`, dopóki integracja jest wyłączona). `recent_errors` jest dziś zawsze puste: nic go jeszcze nie wypełnia, więc pusta lista nie oznacza, że błędów nie było, a plik, którego nie udało się zaimportować, się tam nie pojawia. Dziś strumień zmian niesie zmiany `kind="fields"`, `kind="new_asset"`, `kind="settings"`, przy `td_deletion_marks_in_cms` także `kind="deleted"` i `kind="restored"`, a w trybie odczytu, dla tokenów z `articles:read`, `article_sent`. Organizacja ma jedną potwierdzoną pozycję w strumieniu, niezależnie od tego, który token podaje kursor, i tylko odpytania tokenu z `media:read` ją przesuwają oraz liczą się do `stalled` i `pending_changes`; token mający wyłącznie zakresy artykułów czyta takim samym kursorem, nie przesuwając ich. W trybie odczytu bez klienta mediów `stalled` znaczy, że wysyłka czeka na odczyt przez twój CMS dłużej niż 24 godziny. Nowe pliki, zmiany pól i usunięcia wysyłane przez CMS są już przyjmowane.
- **Planowane trasy:** dziś żadne. Przyszła operacja, która nie jest jeszcze gotowa, ma w dokumencie OpenAPI oznaczenie `x-status: planned`; sprawdza Twój token i zakres, po czym odpowiada `501` z kodem błędu `not_implemented`. Kolejność sprawdzeń na takiej trasie: `401` (token), `403` (zakres), `429` (limit żądań), `409` (zamrożona organizacja, dla zapisów), `422` (kształt żądania), a na końcu `501`. Niepoprawne body JSON jest odrzucane z `422` przed sprawdzeniem tokenu, więc nigdy nie dociera do uwierzytelniania.

## Uzyskanie tokenu i zakresów

Tokeny wydaje Tribune Desk; nie ma samodzielnej rejestracji. Zwróć się do swojej osoby kontaktowej w Tribune Desk. Token należy do jednej organizacji i niesie zestaw zakresów. Wysyłaj go w każdym żądaniu:

```
Authorization: Bearer tdcms_...
```

Trzymaj go w tajemnicy, przechowuj poza systemem kontroli wersji i poproś o nowy, jeśli wycieknie. Token nie wygasa; unieważnić go może tylko superadmin. Organizacja może mieć kilka tokenów naraz, więc wymiana wygląda tak: weź nowy token, przełącz na niego CMS, potem poproś o unieważnienie starego. Brakujący, nieznany lub unieważniony token daje `401`. Ważny token bez zakresu danej trasy daje `403`.

| Zakres | Pozwala |
|---|---|
| `media:read` | odczytywać zmiany, status i wstrzymane partie |
| `media:write` | wysyłać nowe pliki, zmiany pól, usunięcia i powiązania; decydować o wstrzymanych partiach; uruchamiać resync; wypychać istniejące pliki |
| `settings:read` | odczytywać ustawienia synchronizacji |
| `settings:write` | zmieniać ustawienia synchronizacji |
| `backfill:write` | brać udział w jednorazowym imporcie plików historycznych |
| `articles:read` | odczytywać status, a w trybie odczytu zmiany `article_sent` i wysłane artykuły |
| `articles:write` | zgłaszać, gdzie artykuły zostały opublikowane (link zwrotny), oraz wynik dostawy w trybie odczytu |

Sprawdź, co może Twój token:

```
curl -sS https://api.tribunedesk.com/v3/cms/status \
  -H "Authorization: Bearer $TD_CMS_TOKEN"
```

```
{"org_code":"example-org","contract_version":"3.4.2-draft","scopes":["media:read"],"state":"active", ...}
```

## O co poprosić Tribune Desk

Tribune Desk konfiguruje każdą integrację ręcznie. Wybierz poziomy, które budujesz, i poproś swój kontakt w Tribune Desk o to, co podają ich wiersze.

| Poziom | O co poprosić | Dlaczego |
|---|---|---|
| 1, webhook | sekret podpisu (`whsec_`, pokazywany raz) i ustawienie Twojego adresu webhooka dla organizacji (`https://` na publicznym hoście); użytkownik redakcji może go też ustawić sam w Ustawieniach Tribune Desk, w sekcji Integracje | Bez aktywnego sekretu podpisu albo adresu webhooka „Wyślij do CMS” nic nie wysyła. Integracja nie musi być włączona. |
| 1, webhook, hosty obrazów | token z `articles:read` albo listę hostów magazynu plików Tribune Desk | Z tokenem `GET /v3/cms/status` podaje `image_hosts`, czyli hosty, z których wolno pobierać obrazy. |
| 1, tryb odczytu | włączenie trybu odczytu dla organizacji, włączenie integracji i token z `articles:read` i `articles:write` | Tryb odczytu działa tylko przy włączonej integracji; tymi zakresami czytasz wysłane artykuły i zgłaszasz wynik. |
| 2 | token z `articles:write` (token trybu odczytu już go ma) | Link zwrotny wymaga tylko tego zakresu; integracja nie musi być włączona. |
| 3 | nic dla linków, SEO, autora i etykiety AI; dla boksu „Czytaj więcej” poproś Tribune Desk o włączenie go dla organizacji | Dopóki nie jest włączony, dostawy pomijają `backlink_sources`. |
| 4 | włączenie integracji i biblioteki mediów dla organizacji; token z `media:read`, `media:write` i `settings:read`, do tego `settings:write`, jeśli Twój CMS zmienia ustawienia synchronizacji, i `backfill:write` do importu historycznego; dodatkowe hosty, z których serwujesz pliki (CDN, subdomena mediów) | Trasy mediów odpowiadają `409`, dopóki oba nie są włączone; Tribune Desk pobiera Twoje pliki tylko z dozwolonych hostów. |

Jeden token może mieć wszystkie potrzebne zakresy; poproś o jeden token na organizację. Cała reszta jest w tym przewodniku: integrację zbudujesz i przetestujesz, zanim dostaniesz cokolwiek z tej listy.

## Trasy i wymagane zakresy

| Trasa | Zakres | Cel |
|---|---|---|
| `GET /v3/cms/status` | `media:read` lub `articles:read` | Stan integracji i liczniki (działa dzisiaj) |
| `GET /v3/cms/changes` | `media:read` lub `articles:read` | Pobieranie zmian od kursora (działa dzisiaj); każdy token widzi tylko rodzaje zmian ze swoich zakresów |
| `POST /v3/cms/media` | `media:write` | Wysyłanie plików, które są nowe w CMS (działa dzisiaj) |
| `POST /v3/cms/media/{asset_id}/link` | `media:write` | Potwierdzenie, że CMS przejął plik z Tribune Desk (działa dzisiaj) |
| `POST /v3/cms/media/fields` | `media:write` | Wysyłanie zmian pól (działa dzisiaj) |
| `POST /v3/cms/media/deletions` | `media:write` | Zgłaszanie plików usuniętych w CMS (działa dzisiaj) |
| `POST /v3/cms/media/push-existing` | `media:write` | Kolejkowanie istniejących plików Tribune Desk dla CMS (działa dzisiaj) |
| `GET /v3/cms/settings` | `settings:read` | Odczyt ustawień synchronizacji i limitów (działa dzisiaj) |
| `PUT /v3/cms/settings` | `settings:write` | Zapis ustawień synchronizacji (działa dzisiaj) |
| `POST /v3/cms/resync` | `media:write` | Porównanie pól po awarii lub po wygaśnięciu kursora (działa dzisiaj) |
| `GET /v3/cms/held` | `media:read` | Lista wstrzymanych partii (działa dzisiaj) |
| `POST /v3/cms/held/{held_id}/decision` | `media:write` | Wysłanie lub odrzucenie wstrzymanej partii (działa dzisiaj) |
| `GET /v3/cms/backfill/requests` | `backfill:write` | Zlecenia eksportu do importu historycznego |
| `POST /v3/cms/backfill/requests/{request_id}/pages` | `backfill:write` | Przesłanie jednej strony wyników eksportu (do 1000 kandydatów) |
| `GET /v3/cms/articles/awaiting` | `articles:read` | Lista wysyłek czekających na wynik (tryb odczytu) |
| `GET /v3/cms/articles/{article_id}` | `articles:read` | Odczyt wysłanego artykułu (tryb odczytu) |
| `POST /v3/cms/articles/{article_id}/result` | `articles:write` | Zgłoszenie wyniku wysłanego artykułu (tryb odczytu) |
| `POST /v3/cms/articles/published` | `articles:write` | Zgłoszenie, gdzie dostarczone artykuły zostały opublikowane (poziom 2, link zwrotny) |

## Ponowienia

- Ponawiaj przy `429`, `500`, `503`, błędach sieci oraz przy `502` i `504`, którymi bramka może odpowiedzieć bez naszego body JSON: odczekaj co najmniej `retry_after` sekund, a potem wydłużaj odstępy wykładniczo z losowym rozrzutem (jitter). Nasz nagłówek `Retry-After` zawiera tę samą całkowitą liczbę sekund co `retry_after`; bramka może wysłać go jako datę.
- Nie ponawiaj innych błędów `4xx` bez zmian: najpierw popraw żądanie albo stan.
- Dbaj o idempotentność ponowień: zapisuj kursor dopiero po zastosowaniu jego zmian, a własne rekordy kluczuj identyfikatorami z żądania (`cms_media_id`), żeby powtórzenie partii nie tworzyło duplikatów. Powtórzony plik odpowiada `known`, a powtórzona zmiana pola `unchanged`.
- Jeśli Twój proces padł przed zapisaniem kursora, odpytaj ponownie ze starym kursorem i zastosuj zmiany jeszcze raz.

Każdą trasę można bezpiecznie powtórzyć po utraconej odpowiedzi. Co daje powtórzenie:

| Trasa | Odpowiedź na powtórzenie |
|---|---|
| `POST /media` | `known`. |
| `POST /media/fields` | `unchanged` dla zastosowanych wartości; wartości oczekujące zostają w swojej partii. |
| `POST /media/{asset_id}/link` | `known`. |
| `POST /media/deletions` | `known`. |
| `POST /media/push-existing` | Niczego nie kolejkuje dwa razy: pliki z nieodczytaną zmianą są pomijane. Utracone `next_after` jest nieszkodliwe; powtórz to samo wywołanie. |
| `POST /resync`, strona podglądu | Zastępuje tę stronę. Pierwsza strona powtórzona bez `resync_id` rozpoczyna drugą sesję; porzuć pierwszą. Ostatnia strona powtórzona daje `409`: rozpocznij nowy podgląd. |
| `POST /resync`, potwierdzenie | Ta sama odpowiedź i ten sam kursor. |
| `POST /held/{held_id}/decision` | `409`: odczytaj `GET /held` i porównaj `state`. |
| `PUT /settings` | Te same ustawienia. |
| `POST /backfill/requests/{request_id}/pages` | Te same wyniki. Po utraconej odpowiedzi na ostatnią stronę: `409`, co oznacza, że gotowe. |

## Błędy

Każdy błąd zwracany przez aplikację na tych trasach ma to samo body JSON (błędy z bramki lub proxy przed nią mogą go nie mieć): `{"code": "...", "message": "...", "retry_after": 5}`. `retry_after` występuje tylko wtedy, gdy odczekanie pomaga. Komunikaty są dla ludzi; dopasowuj po `code`. Body nigdy nie powtarza wartości, które wysłałeś; błąd walidacji może jednak wymienić nieznane pole.

| Kod | HTTP | Znaczenie i co zrobić |
|---|---|---|
| `unauthorized` | 401 | Brak tokenu, token nieznany lub unieważniony. Sprawdź nagłówek; poproś o nowy token. |
| `forbidden` | 403 | Token nie ma zakresu tej trasy. Poproś o ten zakres. |
| `not_found` | 404 | W Twojej organizacji nie ma takiego obiektu. Sprawdź identyfikator; nie ponawiaj. |
| `project_deactivated` | 409 | Organizacja jest zamrożona i odrzuca zapisy (`POST`, `PUT`). Odczyty, w tym `GET /changes` i `GET /settings`, nadal działają i nigdy nie zwracają tego kodu. Przestań zapisywać i skontaktuj się z Tribune Desk. |
| `option_locked` | 409 | Próbowałeś zmienić ustawienie zablokowane przez Tribune Desk (zob. `locked_options` w ustawieniach). Zostaw je bez zmian. |
| `state_conflict` | 409 | Obiekt nie jest w stanie, który na to pozwala, na przykład wstrzymana partia ma już decyzję, podgląd resync nie jest gotowy, wygasł albo pochodzi sprzed ponownego włączenia integracji, albo integracja nie jest włączona. Odczytaj stan ponownie i działaj zgodnie z nim. Na `GET /changes` i `GET /settings` oznacza wyłącznie, że integracja nie jest włączona. |
| `cursor_expired` | 410 | Twój kursor jest starszy niż 90 dni albo integracja została wyłączona i ponownie włączona, odkąd go dostałeś. Uruchom resync i wznów od kursora, który zwróci. |
| `validation_error` | 422 | Żądanie nie pasuje do schematu; komunikat wymienia pola. Popraw żądanie; nie ponawiaj go bez zmian. |
| `rate_limited` | 429 | Zbyt wiele żądań. Odczekaj `retry_after` sekund, a potem ponów. |
| `internal_error` | 500 | Nasz błąd. Ponawiaj z wydłużanymi odstępami; zgłoś go, jeśli się utrzymuje. |
| `not_implemented` | 501 | Trasa jest planowana i jeszcze niedostępna. Nie ponawiaj. |
| `unavailable` | 503 | Stan przejściowy. Odczekaj `retry_after` sekund, a potem ponów. |

## Limit żądań

600 żądań na minutę na token. Okno jest stałe (jedna minuta zegarowa), nie przesuwne, więc seria żądań na granicy minut może przejść, do dwukrotności limitu w krótkim czasie. Nie polegaj na tym. Po przekroczeniu limitu dostajesz `429` z `rate_limited`, `retry_after` i nagłówkiem `Retry-After`. Ten sam `429` z krótkim czasem oczekiwania (około sekundy) jest zwracany, gdy ogranicznik jest chwilowo zajęty. Obsłuż oba przypadki tak samo: odczekaj, a potem ponów, bez ciasnej pętli. Nie ma nagłówków z pozostałym limitem; zwykła synchronizacja pozostaje daleko poniżej limitu.

Odpowiedź z ustawieniami wymienia limity, które Cię obowiązują (rozmiar partii, długość pola, czas ważności adresu URL pliku, liczba żądań na minutę).
