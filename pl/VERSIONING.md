<!-- translated-from: VERSIONING.md sha256:a4bbbf1f76f0e315 -->
# Wersjonowanie

> Kontrakt jest **wersją roboczą** (`3.9.1-draft`) i może się zmieniać, dopóki nie zostanie ogłoszony jako stabilny. Nie obiecujemy żadnych dat.

Wersja kontraktu to `info.version` w dokumencie OpenAPI i `contract_version` w `GET /v3/cms/status`. Jest zgodna z wersjonowaniem semantycznym:

- **Główna** (`4.0.0`): zmiana łamiąca, na przykład usunięte pole lub trasa albo pole, które zmienia znaczenie. Pojawia się tylko z nową wersją główną, po okresie przejściowym, w którym dotychczasowe zachowanie nadal działa.
- **Podrzędna** (`3.4.0`): coś dodanego, na przykład nowe pole, trasa, zakres albo rodzaj zmiany. Ignoruj pola i rodzaje, których nie znasz; aktualizacja nie wymaga od Ciebie niczego.
- **Poprawka** (`3.3.1`): opisy i poprawki, które nie zmieniają żadnego kształtu.
- **`-draft`**: kontrakt może się jeszcze zmienić, zanim zostanie ogłoszony jako stabilny. Dopóki jest wersją roboczą, zmiana łamiąca może przyjść w wersji minor; CHANGELOG oznacza ją jako **Breaking** i podaje datę.

Ignorowanie tego, czego nie znasz, jest częścią kontraktu: schematy tego, co wysyła Tribune Desk, nie zabraniają nieznanych właściwości, więc nie generuj walidatora, który ich zabrania.

Każda zmiana kontraktu ma wpis w [CHANGELOG](../CHANGELOG.md).

Każda wersja, która trafia na main, dostaje tag; wersja nadpisana w PR-ze synchronizacji dokumentacji, zanim został scalony, zachowuje tylko swoją sekcję w CHANGELOG, a jej zmiany wychodzą w następnym tagu (np. 3.6.1-draft niesie v3.7.0-draft).
