<!-- translated-from: guide/3-full-content.md sha256:7fb80ec40d73bdcb -->
# Poziom 3 – Pełna treść

Poziom 3 korzysta z tych samych dostaw co poziom 1 i odczytuje więcej ich pól. Nic tutaj nie wymaga nowej trasy.

## Linki wewnętrzne

Linki w `html` do innych artykułów twojej organizacji wskazują albo na twój adres tego artykułu (gdy Tribune Desk go zna, z `permalink` lub z linku zwrotnego), albo na zastępnik: `link_placeholder_prefix`, po którym następuje `article_id` artykułu docelowego. Nie wpisuj prefiksu na sztywno; odczytuj go z każdej dostawy. Przy publikacji zastąp każdy zastępnik swoim adresem artykułu o tym `article_id`; gdy go nie masz, zostaw tekst linku, a sam link usuń. Później, gdy artykuł docelowy zostanie opublikowany, możesz wrócić do wcześniejszych wpisów i zastąpić tam zastępnik. `internal_links` wymienia każdy taki link wraz z jego `kind` (`cms` lub `placeholder`).

Każdy element `internal_links` zawiera:

- `href`: adres, na który wskazuje link w `html`, twój adres albo zastępnik;
- `article_id`: identyfikator linkowanego artykułu w Tribune Desk, klucz do odnalezienia twojego wpisu;
- `kind`: `cms`, gdy linkowany artykuł ma adres w twoim CMS, w przeciwnym razie `placeholder`; `null`, razem z `null` w `article_id`, dla linku do strony spoza Tribune Desk: zostaw taki link bez zmian;
- `anchor_text`, `url` i `headline`: tekst linku, bieżący adres linkowanego artykułu i jego tytuł.

Krok po kroku, gdy przychodzi dostawa:

1. Dla każdego elementu z `kind` = `placeholder` odszukaj swój wpis utworzony z `article_id`.
2. Znaleziony i publiczny: zastąp `href` w `html` adresem wpisu.
3. Nieznaleziony lub niepubliczny: zostaw tekst linku, a sam link usuń.
4. Zachowaj element, aby wykonać krok 2 później, gdy ten wpis zostanie opublikowany.

## Boks „Czytaj więcej”

`backlink_sources` wymienia starsze artykuły, które powinny linkować do tego, każdy z `article_id` i `distance` (niższa wartość oznacza większą bliskość tematyczną). Użyj go, aby pokazać ten artykuł w boksie „Czytaj więcej” na tych starszych wpisach. Zasady:

- brak klucza oznacza: nie ruszaj istniejących linków;
- pusta lista oznacza: żaden starszy artykuł nie powinien tu linkować; usuń ten artykuł z ich boksów;
- lista zastępuje poprzednią listę dla tego artykułu;
- `null` znaczy to samo co brak klucza.

Wygląd boksu i jego miejsce zależą od twojego CMS. Tribune Desk mówi tylko, które artykuły do siebie pasują.

## SEO, autor i język

`seo_title`, `meta_description` i `focus_keyphrase` to wybór redaktora na potrzeby wyszukiwarek. `author` to osoba, która zamówiła artykuł; użyj jej jako autora wpisu, gdy `sent_by`, czyli osoby, która kliknęła „Wyślij do CMS”, nie da się dopasować do użytkownika twojego CMS. Osobę dopasowuj najpierw po `id` we własnym powiązaniu użytkowników Tribune Desk z użytkownikami CMS, potem po `email`; `name` służy tylko do wyświetlania. Bez dopasowania użyj domyślnego autora. `language` to język, w którym pisze redakcja, znacznik BCP 47 (na przykład `pl`), o ile jest ustawiony. `evergreen` jest informacyjne: artykuł nie traci aktualności, więc możesz go trzymać poza archiwami według dat. Pola tekstowe nie mają limitu długości po stronie Tribune Desk: przycinaj je do limitów swojego CMS.

## Oznaczenie AI

Zgodnie z rozporządzeniem o sztucznej inteligencji (AI Act), art. 50 ust. 2, tekst wytworzony z użyciem AI musi być oznaczony w formacie nadającym się do odczytu maszynowego. `ai_provenance` jest tym oznaczeniem i źródłem prawdy: `claims` (to, co jest deklarowane: `article_id`, `generated_at`, `content_sha256`, `generator`, `v` (wersja tego formatu claims), `models`, `digital_source_type`) oraz `jws`, czyli claims podpisane jako kompaktowy JWS. Ma wartość `null`, gdy redakcja wyłączyła oznaczanie.

Umieść je w `<head>` publicznej strony jako JSON-LD, na przykład:

```
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "NewsArticle",
 "identifier": "<claims.article_id>", "dateCreated": "<claims.generated_at>",
 "digitalSourceType": "<claims.digital_source_type>", "hfProvenanceJws": "<jws>"}
</script>
```

Koniec `html` niesie tę samą deklarację jako blok `<script type="application/ld+json" data-hf-provenance>`. To kopia przeznaczona dla integracji, które publikują `html` bez zmian; gdy umieszczasz JSON-LD w `<head>`, możesz usunąć ten blok z treści.

Każdy może sprawdzić oznaczenie bez tokenu, pod `https://api.tribunedesk.com`:

- `GET /.well-known/hf-provenance.json` zwraca klucz publiczny (JWK Set) do weryfikacji `jws` oraz informację, kto jest producentem;
- `POST /v2/verify` z `{"text": "..."}` odpowiada, czy tekst pochodzi z Tribune Desk (`generated`), i podaje datę, kiedy pojawił się tam po raz pierwszy (`generated_at`). Nigdy nie mówi, która organizacja go wytworzyła. Wyślij treść artykułu: `html` w postaci dostarczonej albo jego czysty tekst, bez tytułu (`title` nie jest częścią `html`). Przed sprawdzeniem Tribune Desk usuwa tagi i bloki `<script>`, zamienia tekst na małe litery i scala białe znaki, więc znaczniki i blok pochodzenia nie mają znaczenia, ale każda zmiana w słowach już tak: zredagowany artykuł daje odpowiedź `generated: false`. Trasa przyjmuje 30 żądań na minutę z jednego adresu IP i powyżej tego odpowiada `429`; `503` oznacza chwilową niedostępność rejestru, więc spróbuj ponownie później.

## Gotowe, gdy

- Zastępniki są zastępowane twoimi adresami albo tekst linku zostaje bez linku, a wcześniejsze wpisy są aktualizowane, gdy artykuł docelowy zostanie opublikowany.
- Boks „Czytaj więcej” działa zgodnie z `backlink_sources`, łącznie z zasadami dla brakującego klucza i pustej listy.
- Pola SEO, autor i język są zapisane przy wpisie.
- Oznaczenie AI jest w `<head>` każdej publicznej strony utworzonej z dostawy, której `ai_provenance` nie jest `null`.
