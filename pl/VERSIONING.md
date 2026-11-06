<!-- translated-from: VERSIONING.md sha256:9c62cb07f970477b -->
# Wersjonowanie

> Kontrakt jest **wersją roboczą** (`3.2.0-draft`) i może się zmieniać, dopóki nie zostanie ogłoszony jako stabilny. Nie obiecujemy żadnych dat.

Wersja kontraktu to `info.version` w dokumencie OpenAPI i `contract_version` w `GET /v3/cms/status`. Jest zgodna z wersjonowaniem semantycznym:

- **Główna** (`4.0.0`): zmiana łamiąca, na przykład usunięte pole lub trasa albo pole, które zmienia znaczenie. Pojawia się tylko z nową wersją główną, po okresie przejściowym, w którym dotychczasowe zachowanie nadal działa.
- **Podrzędna** (`3.3.0`): coś dodanego, na przykład nowe pole, trasa, zakres albo rodzaj zmiany. Ignoruj pola i rodzaje, których nie znasz; aktualizacja nie wymaga od Ciebie niczego.
- **Poprawka** (`3.2.1`): opisy i poprawki, które nie zmieniają żadnego kształtu.
- **`-draft`**: kontrakt może się jeszcze zmienić, zanim zostanie ogłoszony jako stabilny.

Każda zmiana kontraktu ma wpis w [CHANGELOG](../CHANGELOG.md).
