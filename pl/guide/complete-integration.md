<!-- translated-from: guide/complete-integration.md sha256:a82016d3090ee4c6 -->
# Pełna integracja w dowolnym CMS

Rozdziały poziomów mówią, co znaczy każde pole i każda trasa. Ten rozdział mówi, co pełna integracja robi z nimi na produkcji: co działa w tle, jak filtrować HTML, co każda nowa wysyłka artykułu zmienia we wpisie i jak na brzegach zachowują się zdjęcia, link zwrotny i kategorie. Wtyczka Tribune Desk dla WordPressa trzyma się tych reguł; z nimi zbudujesz to samo zachowanie w dowolnym CMS, także we własnym. Tam, gdzie wtyczka znanym sposobem nie dorasta do reguły, trzymaj się reguły z tego rozdziału, nie wtyczki.

Słowa używane niżej: wpis jest **niepubliczny**, gdy jest szkicem, czeka na przegląd albo jest zaplanowany; jest **publiczny**, gdy jest opublikowany. Wpis prywatny liczy się jako publiczny: zostaw go w spokoju jak opublikowany.

## Czego potrzebuje twój CMS

- **Unikalnego klucza i blokady na artykuł.** Trzymaj `article_id` jako unikalny we wpisie i szereguj zapisy jednego artykułu (blokada w bazie albo blokada wiersza na czas zapisu). Dwie próby jednej wysyłki mogą na siebie zachodzić.
- **Pracy w tle.** Harmonogramu albo kolejki, która uruchamia zadania później (cron, kolejka zadań, timer). Bez niej nigdy nie dojdą zdjęcia, których nie udało się pobrać, nieudane linki zwrotne, wpisy zaplanowane ani dzienna synchronizacja kategorii. Zobacz [Zadania w tle](#zadania-w-tle).
- **Sanitizera HTML opartego na parserze**, ustawionego jak w [Filtrowanie HTML](#filtrowanie-html). Nie pisz go na wyrażeniach regularnych.
- **Klienta HTTP z limitami czasu**, który nie idzie za przekierowaniem, gdy wysyła token.
- **Miejsca na ustawienia i krótki dziennik dostaw** (zobacz [Ustawienia i eksploatacja](#ustawienia-i-eksploatacja)).
- **Serwera, który obsługuje żądania równolegle**, gdy testujesz. Jednowątkowy serwer deweloperski (na przykład `php -S`) odpowiada na jedno żądanie naraz, więc test nakładających się prób przechodzi, nie dowodząc działania blokady. Ten przypadek testuj na serwerze z kilkoma workerami.

## Zadania w tle

| Zadanie | Kiedy | Co robi | Poziom |
|---|---|---|---|
| Ponowienie zdjęć | Minutę po dostawie, która nie zdążyła pobrać zdjęć | Pobiera brakujące zdjęcie główne i zdjęcia z treści z dłuższym limitem (60 sekund) i wstawia je do wpisu. Co najmniej jedno ponowienie; więcej, z rosnącym odstępem, też jest w porządku. Odmówionego hosta się nie ponawia. | 1 |
| Ponowienie linku zwrotnego | Po błędzie sieci, `429` albo `5xx` | Wysyła zgłoszenie ponownie po `Retry-After` albo po 5 minutach. Co najmniej jedno ponowienie; więcej, z rosnącym odstępem, jest lepsze. Po ostatnim zapisz to w dzienniku: dosyłanie wyśle je później. | 2 |
| Publikacja masowa | Gdy redaktor publikuje wiele wpisów naraz | Odkłada jedno zgłoszenie na wpis zamiast wołać Tribune Desk w żądaniu redaktora. Odłożone zgłoszenia mają te same ponowienia co każde inne. | 2 |
| Publikacja zaplanowana | Gdy twój CMS publikuje zaplanowany wpis | Wykonuje te same [kroki publikacji](#gdy-wpis-staje-się-publiczny) co przy wpisie opublikowanym ręcznie. | 2, 3 |
| Hosty zdjęć | Raz na godzinę, gdy masz token | Czyta `image_hosts` z `GET /v3/cms/status`; po nieudanym odczycie zostaw ostatnią listę i spróbuj znów za godzinę, nie przy każdym zdjęciu. | 1 |
| Synchronizacja kategorii | Raz dziennie i raz zaraz po zapisaniu tokenu | Pełny przebieg `POST /v3/cms/taxonomy/terms` plus kolejka pojedynczych zmian. Zobacz [Wysyłanie i ustawianie terminów](#wysyłanie-i-ustawianie-terminów). | 3 |
| Synchronizacja mediów | Tak często, jak mówi przewodnik 4 | Odpytuje `GET /v3/cms/changes` i wysyła twoje zmiany. | 4 |

Zadanie, które zapisuje wpis, bierze tę samą blokadę artykułu co dostawa i trzyma ją tylko na czas zapisu: najpierw pobierz, potem weź blokadę, przeczytaj wpis ponownie i zapisz. Zadanie, które trzyma blokadę podczas pobierania, blokuje dostawy tego artykułu, a Tribune Desk widzi je jako nieudane.

## Filtrowanie HTML

Traktuj `html` jak treść od zaufanego redaktora, która mimo to nie może uruchamiać kodu na twoich stronach. Kroki, w tej kolejności:

1. Wyjmij blok etykiety AI (`<script type="application/ld+json" data-hf-provenance>`) z surowego `html`. Odłóż go, jeśli publikujesz go w treści; w przeciwnym razie go usuń, bo `ai_provenance` niesie to samo oświadczenie (zobacz [Przechowywanie etykiety AI](#przechowywanie-etykiety-ai)). Po tym kroku filtr może usunąć każdy `script`.
2. Przepuść resztę przez sanitizer z listą dozwolonych:
   - **Znaczniki:** co najmniej `p`, `h2`–`h6`, `strong`, `b`, `em`, `i`, `u`, `br`, `hr`, `ul`, `ol`, `li`, `blockquote`, `a`, `figure`, `figcaption`, `img`, `table` z jej częściami oraz `iframe` według reguły niżej. Usuń `script`, `style`, `object`, `embed`, `form`, `svg` i `math` razem z zawartością; każdy inny znacznik spoza listy traci sam znacznik, a jego tekst zostaje.
   - **Atrybuty:** zostaw `href`, `target`, `rel` i `title` na `a`; `src`, `alt`, `width`, `height` i każdy atrybut `data-td-*` na `img`; `class` na `figure`. Usuń każdy atrybut `on*` i `style` (chyba że twój sanitizer filtruje CSS).
   - **Adresy** w `href` i `src`: tylko `https:`, `http:`, `mailto:`, adresy względne i kotwice `#`. Usuń `javascript:`, `data:`, `vbscript:` i każdy inny schemat, także zapisany encjami, wielkimi literami albo ze spacjami w środku.
   - **Embedy:** zostaw `iframe` tylko wtedy, gdy jego `src`, odczytany jako URL, ma schemat `https`, host dokładnie z hostów, którym ufasz, a ścieżka zaczyna się od ścieżki odtwarzacza (na przykład `www.youtube.com` i `/embed/`). Zostaw w nim tylko `src`, `width`, `height`, `frameborder`, `allowfullscreen`, `allow` i `title`. `iframe` z dwoma atrybutami `src` albo taki, którego twój parser nie odczyta, jest usuwany.
3. Rozwiąż linki wewnętrzne (przewodnik 3), potem zamień figury z biblioteki na natywne zdjęcia (zobacz [Zdjęcia w szczegółach](#zdjęcia-w-szczegółach)).

Dostawa działa bez zalogowanego redaktora. Jeśli twój CMS przy zapisie filtruje treść drugi raz według uprawnień bieżącego użytkownika, upewnij się, że ten drugi filtr zostawia te same embedy, bo inaczej znikną przy zapisie. Gdy sanitizer zawiedzie, nie zapisuj nic i odpowiedz `500`: Tribune Desk spróbuje ponownie. Nigdy nie zapisuj niefiltrowanej treści.

Użyj utrzymywanego sanitizera: w PHP `symfony/html-sanitizer` albo HTML Purifier, w Pythonie `nh3`, w Node `sanitize-html` albo DOMPurify, w Ruby `rails-html-sanitizer`, w Go `bluemonday`, w Javie OWASP Java HTML Sanitizer.

Do wpisu nie mogą trafić: `<img src="x" onerror="alert(1)">` (atrybut jest usuwany), `<a href="javascript:alert(1)">`, `<a href="JaVa&#115;cript:alert(1)">`, `<svg onload="alert(1)">`, `iframe` z `www.youtube.com.example.net`, `iframe` bez `</iframe>` ani `iframe` z niezaufanego hosta, którego `title` zawiera zaufany adres. Muszą przetrwać: `iframe` odtwarzacza YouTube, `<figure class="alignleft"><img src="…" data-td-asset-id="…" data-td-cms-media-id="…"></figure>`, `<a href="https://…" target="_blank" rel="noopener">`.

## Jedna dostawa krok po kroku

1. Zweryfikuj podpis na surowym body (przewodnik 1). Odpowiedz `401` tylko wtedy, gdy podpis się nie zgadza.
2. Odczytaj body; bez `article_id` albo `html` odpowiedz `400`. Pomijaj pola, których nie znasz.
3. Weź blokadę artykułu. Jeśli nie zwolni się w ciągu około 20 sekund, odpowiedz `503`: Tribune Desk spróbuje ponownie.
4. Znajdź wpis po `article_id`. Wpis, który redaktor przeniósł do kosza, też się liczy: przywróć go jako szkic i zaktualizuj, żeby artykuł nigdy nie dostał drugiego wpisu. Jeśli zapisany w nim `sent_at` jest nowszy niż w body, nie stosuj niczego i odpowiedz `2xx` z obecnym stanem wpisu (`status` `updated`).
5. Przefiltruj HTML i rozwiąż linki jak wyżej.
6. Utwórz albo zaktualizuj wpis tak, jak mówi tabela niżej, potem zdjęcia, pola SEO i etykietę AI.
7. Zapisz `sent_at`, zwolnij blokadę i odpowiedz z `cms_post_id`, `status`, `edit_url`, `publication` oraz `permalink`, gdy wpis jest publiczny. Gdy coś się nie udało, odpowiedz `500` bez szczegółów wewnętrznych; szczegóły zostaw w swoim dzienniku.

## Co zmienia każda wysyłka

| Część wpisu | Nowy wpis | Wpis jeszcze niepubliczny | Wpis publiczny |
|---|---|---|---|
| Tytuł | `title` albo `topic`, gdy tytułu brak | zastąpiony | bez zmian |
| Treść | przefiltrowany `html` | zastąpiona | bez zmian |
| Autor | [wybrany](#wybór-autora) | wybrany ponownie z tej wysyłki | bez zmian |
| Zajawka | `excerpt` | wypełniana tylko, gdy wpis jej nie ma: zajawka napisana przez redaktora zostaje | bez zmian |
| Tytuł SEO, meta description, fraza kluczowa | ustawione | wypełniane tylko, gdy puste | wypełniane tylko, gdy puste |
| Zdjęcie główne | ustawione | zastąpione, gdy główne zdjęcie dostawy różni się od ustawionego przez poprzednią dostawę, chyba że redaktor wybrał inne zdjęcie ręcznie | ustawiane tylko, gdy wpis go nie ma |
| Zdjęcia w treści | zamienione | zamienione | bez zmian |
| Etykieta AI (`ai_provenance`) | zapisana | zastąpiona albo usunięta, gdy jest `null` | bez zmian |
| Dane linków wewnętrznych | zapisane | zastąpione | bez zmian |
| `backlink_sources` | zapisane | zapisane | zapisane, a wiersze „czytaj także” przebudowane |
| Kategorie i tagi | ustawione | ustawione | bez zmian |
| Język | ustawiony | bez zmian (redaktor mógł przenieść wpis) | bez zmian |
| Stan publikacji | [jak w żądaniu](#stan-publikacji-i-daty) | jak w żądaniu | bez zmian |
| `status` w odpowiedzi | `created` | `updated` | `skipped_already_published` |

Prawa kolumna to powód, dla którego `skipped_already_published` nadal ma znaczenie: zdjęcie główne zrobione po pierwszej wysyłce, puste pola SEO i nowa lista „czytaj także” docierają do opublikowanego wpisu. Jego treść, tytuł i autor zostają takie, jakie zostawiła redakcja.

## Stan publikacji i daty

- `draft`: wpis zostaje nieopublikowany i nie ma własnej daty publikacji.
- `publish`: wpis jest publikowany teraz, a jego data to teraz, także gdy był zaplanowany na później.
- `schedule`: wpis jest planowany na `at`, przeliczone z UTC na strefę czasową twojej strony. `at` bez przesunięcia strefy albo takie, którego nie odczytasz, pomijasz jak nieznane pole. `at`, które już minęło, oznacza publikację teraz.
- Brak `publication`: nowy wpis idzie za ustawieniem twojej strony (domyślnie szkic albo publikacja od razu, jeśli strona tak wybrała); istniejący zachowuje swój stan.

Daj stronie sposób, by to ograniczyć: ustawienie, które nie pozwala Tribune Desk publikować (domyślnie wyłączone, więc Tribune Desk może publikować). Gdy jest włączone, traktuj `publish` i `schedule` tak, jakby dostawa nie miała `publication`: nowy wpis idzie za ustawieniem strony, istniejący zachowuje swój stan; `draft` działa dalej. Odpowiadaj stanem, jaki wpis naprawdę ma, żeby redakcja, której CMS pilnuje, kto może publikować, zachowała tę kontrolę.

`publication` w odpowiedzi bierz z wpisu po zapisie: szkic albo wpis czekający na przegląd daje `draft` z `at` równym `null`; wpis zaplanowany `scheduled` z jego czasem; opublikowany `published` z jego czasem. Pomiń `publication` dla wpisu prywatnego i każdego innego stanu.

## Zdjęcia w szczegółach

**Najpierw szukaj, potem pobieraj.** Dla zdjęcia głównego (`generated_images[0]`) i każdej figury w treści z `data-td-asset-id` szukaj pliku, który już masz, w tej kolejności:

1. Twoje id od Tribune Desk (`cms_attachment_id` albo `cms_media_id` zdjęcia, `data-td-cms-media-id` zdjęcia w treści). Użyj go tylko wtedy, gdy ten plik istnieje, a twoje zapisy wiążą go z tym zdjęciem: ma ten sam `asset_id` albo nie ma żadnego i jego adres lub adres, z którego go pobrałeś, równa się URL zdjęcia, albo sam wysłałeś ten plik do Tribune Desk (poziom 4). Plik z innym `asset_id` albo nigdy niewysłany i z innym adresem to nie to zdjęcie, nawet jeśli jest zdjęciem: pomiń wskazówkę i szukaj dalej.
2. Plik, który zapisałeś z tym `asset_id`.
3. Plik pobrany wcześniej z tego samego URL.
4. Plik, którego URL leży w twoim własnym magazynie mediów.

Zapisz `asset_id` przy pliku, który znalazłeś albo pobrałeś. Plik, który już miałeś, zachowuje tytuł, tekst alternatywny, podpis i opis: redakcja mogła je poprawić.

**Pobieraj w budżecie.** Pobieraj tylko adresy `https` z hostów z `image_hosts`; odmówiony host zapisz w dzienniku i go nie ponawiaj. W dostawie daj zdjęciu głównemu około 15 sekund, a wszystkim zdjęciom z treści razem około 10 sekund, żeby odpowiedź wyszła w ciągu 30 sekund. Co się nie zmieści, jest zapisywane bez zdjęcia i przychodzi z [ponowienia zdjęć](#zadania-w-tle).

**Nazwij i opisz nowe pliki.** Nazwij plik z `filename` albo ze sluga tytułu skróconego do około 60 znaków; rozszerzenie weź z URL, gdy to typ obrazu, inaczej `jpg`. Nie używaj ostatniej części URL: Tribune Desk podaje wiele zdjęć pod tą samą nazwą pliku. Tytuł, tekst alternatywny, podpis i opis ustaw ze zdjęcia na pliku pobranym teraz. Oznacz go jako pochodzący z Tribune Desk, żeby poziom 4 nie odesłał go jako nowego pliku.

**Figury w treści.** `figure` z dokładnie jednym `img` i z `data-td-asset-id` staje się twoim natywnym zdjęciem z tekstem alternatywnym, podpisem i wyrównaniem (`alignleft`, `alignright`, `aligncenter`). `figure` bez `data-td-asset-id` zamieniasz tylko wtedy, gdy plik już jest w twojej bibliotece; nigdy nie pobieraj pliku, na który nikt nie wskazał. Figura, której nie zamieniasz, zostaje bajt w bajt.

## Gdy wpis staje się publiczny

Niezależnie od tego, co go upubliczniło (redaktor, twój harmonogram, publikacja masowa, wywołanie API):

1. **Rozwiąż jego własne linki.** Zastąp każdy placeholder, którego cel jest publiczny, adresem celu. Na publicznej stronie żaden adres placeholdera nie może zostać linkiem: prowadzi do aplikacji Tribune Desk za logowaniem. Pokaż sam tekst linku i zachowaj dane `internal_links`, żeby link mógł wrócić, gdy cel zostanie opublikowany.
2. **Napraw wcześniejsze wpisy.** Znajdź publiczne wpisy, których `internal_links` wskazują ten artykuł, i rozwiąż ich placeholdery. Ogranicz pracę jednej publikacji (wtyczka WordPress naprawia do 50 wpisów) i zapisz w dzienniku, gdy dojdziesz do limitu; resztę naprawi ich własny zapis.
3. **Przebuduj wiersze „czytaj także”** tego wpisu z zapisanych `backlink_sources`: tylko źródła publiczne, nigdy sam wpis.
4. **Zgłoś adres** linkiem zwrotnym.

Zgłoś adres ponownie, gdy zmieni się adres publicznego wpisu (nowy slug albo data) i gdy zmieni się jego ustawienie „nie na Facebooka”. Inne zapisy publicznego wpisu niczego nie zgłaszają.

## Zgłaszanie adresów

- Wysyłaj `article_id` małymi literami i pomijaj wpisy, których `article_id` nie jest UUID: jedno złe id kończy całe żądanie kodem `422`.
- `published_at` to czas publikacji w UTC z przesunięciem. Jeśli twój CMS nie ma czasu UTC dla wpisu opublikowanego przez harmonogram, przelicz czas lokalny.
- W żądaniu redaktora czekaj najwyżej około 5 sekund; nigdy nie blokuj publikacji na Tribune Desk. Niepowodzenie trafia do [ponowień](#zadania-w-tle).
- Wpisy publiczne, zanim twoja integracja dostała token: daj możliwość ich dosłania w żądaniach do 100, od najstarszych, z kursorem, żeby przerwane dosyłanie szło dalej od miejsca przerwania. Po `429` odczekaj `Retry-After` i wyślij to samo żądanie ponownie.
- Zapisz w dzienniku wynik każdego elementu: `not_found` i `invalid_url` to różne usterki; nie ponawiaj ich bez zmian.

## Wysyłanie i ustawianie terminów

**Ustawianie terminów dostawy** (przewodnik 3): szukaj terminu po `cms_term_id` we właściwej taksonomii, potem po `name` bez względu na wielkość liter, a także na znaki diakrytyczne, jeśli twoja baza tak porównuje. Termin znaleziony tylko w drugiej taksonomii to `wrong_taxonomy`; nieznaleziony nigdzie to `unknown_term`. Niepusta lista, z której nie znaleziono żadnego terminu, zostawia tę taksonomię bez zmian: wyczyścić ją może tylko prawdziwie pusta lista (wtedy wpis dostaje kategorię domyślną). Terminy bez nazwy są pomijane. Ustaw terminy przed zapisem i publikacją wpisu, bo permalink może zawierać kategorię.

**Wysyłanie twoich terminów:**

- Pełny przebieg raz dziennie i zaraz po zapisaniu tokenu: strony do 1000 terminów w kolejności twojego id, ten sam `run_id` na każdej stronie, `is_last: true` na ostatniej.
- Zapisuj pozycję po każdej stronie, którą Tribune Desk przyjmie, żeby przerwany przebieg szedł dalej od niej. Przebieg otwarty dłużej niż 23 godziny zaczyna się od nowa z nowym `run_id`: Tribune Desk odrzuca ostatnią stronę przebiegu otwartego od 24 godzin.
- Jeden przebieg naraz: weź blokadę na przebieg.
- Wysyłaj nazwy jako zwykły tekst (odkoduj encje HTML, które twój CMS może przechowywać) i pomijaj termin bez nazwy.
- Pojedyncze zmiany idą do kolejki, którą zadanie w tle wysyła bez `run_id`: nowy albo przemianowany termin z bieżącą nazwą, usunięty z `deleted: true` i nazwą, którą miał. Wiersz wychodzi z kolejki dopiero, gdy Tribune Desk go przyjmie. Po `403` (brak `articles:write`) albo `501` zostaw kolejkę; najbliższy pełny przebieg i tak przeniesie terminy. Gdy kolejka urośnie za bardzo, odrzucaj zmiany: pełny przebieg je nadrobi.

## Wybór autora

Próbuj `sent_by`, potem `author`. Dla każdej osoby najpierw twoje własne przypisanie id osób Tribune Desk do użytkowników, potem użytkownik z tym samym e-mailem. Liczy się tylko użytkownik, który może pisać wpisy: konto czytelnika z tym samym e-mailem nie zostaje autorem. Brak dopasowania: domyślny autor strony. Zapamiętuj osoby, które widziałeś (id, imię i nazwisko, e-mail, ostatnio widziana), żeby ekran ustawień mógł je zaproponować do przypisania.

## SEO i inne pola

- Pola SEO wypełniają tylko puste wartości; możesz też kopiować `meta_description` i `facebook_title` do pól, które czyta twój motyw, według tej samej reguły.
- Opcja może wstawiać `facebook_teaser` do zajawki przed `excerpt`, dla motywu, który używa zajawki jako opisu w serwisach społecznościowych.
- `language` ustawiasz tylko w nowym wpisie. Język, którego twój CMS nie ma, zostawia domyślny i trafia do dziennika.
- Tekst z dostaw to zwykły tekst: usuń znaczniki i scal białe znaki, zanim zapiszesz tytuł, zajawkę albo pole SEO.

## Przechowywanie etykiety AI

Zapisz `ai_provenance` (jego `claims` i `jws`) przy wpisie: to źródło prawdy, a blok na końcu `html` jest jego kopią. Gdy wpis dostaje nową treść, zastąp zapisaną etykietę; wysyłka, w której `ai_provenance` jest `null` albo nie da się go odczytać, ją usuwa, bo stary podpis przy nowym tekście wygląda na fałszerstwo. Wpis publiczny zachowuje swoją etykietę. Drukuj ją w `<head>` strony wpisu jako JSON-LD (przewodnik 3), kodując JSON samodzielnie, a nie drukując tekstu z dostawy, żeby `</script>` w wartości nie zamknął elementu. Jeśli twoja warstwa SEO już opisuje artykuł w JSON-LD, dodaj pola etykiety do tego obiektu zamiast drukować drugi.

## Ustawienia i eksploatacja

Ekran ustawień (albo plik konfiguracji) z:

- sekretem podpisu i tokenem API, przechowywanymi poza kodem źródłowym i nigdy nie pokazywanymi ponownie w całości;
- adresem API, domyślnie `https://api.tribunedesk.com`; odrzuć adres `http` i nigdy nie idź za przekierowaniem z tokenem;
- domyślnym autorem, przypisaniem osób Tribune Desk do użytkowników, publikacją od razu albo szkicami i tym, czy Tribune Desk może publikować;
- opcjonalnymi mapowaniami pól (pola SEO twojego motywu, pole „nie na Facebooka”, zajawka z teasera);
- używanymi hostami zdjęć, przyciskiem dosłania linków zwrotnych i przyciskiem pełnego przebiegu kategorii.

Dziennik dostaw z ostatnich kilkudziesięciu zdarzeń (dostawy, linki zwrotne, błędy zdjęć, przebiegi kategorii), ze zdarzeniami mediów trzymanymi osobno, żeby nie wypychały dostaw. Zapisuj przyczynę słowami; nigdy nie zapisuj sekretu ani tokenu.

Jeśli twoja integracja aktualizuje się sama, sprawdzaj podpis każdej paczki przed instalacją.

## Gotowe, gdy

- Zadanie w tle wykonuje ponowienia zdjęć, ponowienia linku zwrotnego, zgłoszenia publikacji masowej i zaplanowanej, cogodzinne hosty zdjęć i dzienny przebieg kategorii.
- Dwie nakładające się próby jednej wysyłki, testowane na serwerze z kilkoma workerami, dają jeden wpis.
- Żadna z niebezpiecznych próbek z [Filtrowanie HTML](#filtrowanie-html) nie trafia do wpisu, a bezpieczne przetrwają; dostawa filtruje tak samo bez zalogowanego użytkownika.
- Nowa wysyłka zmienia każdą część wpisu tak, jak mówi [tabela](#co-zmienia-każda-wysyłka); opublikowany wpis dostaje późne zdjęcie główne i wypełnione puste pola SEO, a zachowuje tytuł, treść i autora.
- Zaplanowany wpis opublikowany przez twój harmonogram jest zgłaszany linkiem zwrotnym, a jego placeholdery są rozwiązywane; żadna publiczna strona nie linkuje do placeholdera.
- Zdjęcie, które już jest w twojej bibliotece, jest używane ponownie, nie pobierane drugi raz; wskazówka wskazująca plik, który nie jest tym zdjęciem, jest pomijana.
- Nieudany link zwrotny jest wysyłany ponownie później, także ten z publikacji masowej.
- Przerwany przebieg kategorii idzie dalej od ostatniej przyjętej strony, a przebieg pozostawiony otwarty zaczyna się od nowa, zanim minie 24 godziny.
- Ustawienia pozwalają stronie nie dać Tribune Desk publikować: `publish` i `schedule` liczą się wtedy jak brak `publication`, a odpowiedź podaje prawdziwy stan wpisu.
