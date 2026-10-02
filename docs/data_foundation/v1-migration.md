# Migrating from v0.5.x to v1.0.0

`data_foundation` v1.0 preserves the v0.5 domain concepts and establishes them as the stable public contract.

## What remains compatible

- Identity and temporal queries retain their v0.3 semantics.
- Reconciliation statuses and quality findings retain their v0.4 semantics.
- Relationship and timeline structures retain their v0.5 semantics.
- Persisted canonical/source-observation/raw-artifact records remain readable when the new optional
  `contract_version` field is absent; it defaults to `1.0` when loaded by the v1 models.

## New v1 facilities

- machine-readable `contract_manifest()`
- evidence-chain validation
- persisted-store validation
- loading methods on `FoundationStore`
- explicit public API contract and persistence-format version
- `py.typed` marker for type-aware consumers

## Collection dependency

The package continues to depend on `indian-equity-data-platform==1.1.0`. The collection package remains independently
versioned and is not changed by the foundation release.
