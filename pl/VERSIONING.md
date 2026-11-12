<!-- translated-from: VERSIONING.md sha256:e0e7493e9e70ed8b -->
# Wersjonowanie

> Kontrakt jest **wersją roboczą** (`3.4.2-draft`) i może się zmieniać, dopóki nie zostanie ogłoszony jako stabilny. Nie obiecujemy żadnych dat.

Wersja kontraktu to `info.version` w dokumencie OpenAPI i `contract_version` w `GET /v3/cms/status`. Jest zgodna z wersjonowaniem semantycznym:

- **Główna** (`4.0.0`): zmiana łamiąca, na przykład usunięte pole lub trasa albo pole, które zmienia znaczenie. Pojawia się tylko z nową wersją główną, po okresie przejściowym, w którym dotychczasowe zachowanie nadal działa.
- **Podrzędna** (`3.4.0`): coś dodanego, na przykład nowe pole, trasa, zakres albo rodzaj zmiany. Ignoruj pola i rodzaje, których nie znasz; aktualizacja nie wymaga od Ciebie niczego.
- **Poprawka** (`3.3.1`): opisy i poprawki, które nie zmieniają żadnego kształtu.
- **`-draft`**: kontrakt może się jeszcze zmienić, zanim zostanie ogłoszony jako stabilny. Dopóki jest wersją roboczą, zmiana łamiąca może przyjść w wersji minor; CHANGELOG oznacza ją jako **Breaking** i podaje datę.

Ignorowanie tego, czego nie znasz, jest częścią kontraktu: schematy tego, co wysyła Tribune Desk, nie zabraniają nieznanych właściwości, więc nie generuj walidatora, który ich zabrania.

Każda zmiana kontraktu ma wpis w [CHANGELOG](../CHANGELOG.md).
