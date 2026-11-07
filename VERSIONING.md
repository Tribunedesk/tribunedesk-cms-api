# Versioning

> The contract is a **draft** (`3.4.0-draft`) and may change until it is declared stable. No dates are promised.

The version of the contract is `info.version` in the OpenAPI document and `contract_version` in `GET /v3/cms/status`. It follows semantic versioning:

- **Major** (`4.0.0`): a breaking change, such as a removed field or route, or a field that changes meaning. It comes only with a new major version, after a transition period in which the old behaviour keeps working.
- **Minor** (`3.4.0`): something added, such as a new field, route, scope or kind of change. Ignore fields and kinds you do not know; an upgrade needs nothing from you.
- **Patch** (`3.3.1`): descriptions and fixes that change no shape.
- **`-draft`**: the contract may still change before it is declared stable. While it is a draft a breaking change can come in a minor version; the CHANGELOG marks it **Breaking** with its date.

Ignoring what you do not know is part of the contract: schemas of what Tribune Desk sends do not forbid unknown properties, so do not generate a validator that does.

Every change of the contract has an entry in the [CHANGELOG](CHANGELOG.md).
