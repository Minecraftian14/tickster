# data_foundation

Canonical foundation layer for the Indian-equity information corpus.

## Scope

`data_foundation` consumes canonical records produced by `data_collection` 1.1.x. It does **not** fetch external data and should not contain provider-specific API logic.

It owns:

- instrument identity and aliases
- point-in-time temporal semantics
- source observations and reconciliation
- relationship/index structures
- structured data-quality semantics
- company timelines
- canonical JSONL persistence and manifests
- point-in-time record queries

## Dependency boundary

- `data_collection` remains at **1.1.0** for this milestone.
- `data_foundation` starts independently at **0.1.0**.
- A future enrichment package will consume `data_foundation`; enrichment must not reach back into provider APIs.

## Design invariant

Derived/enriched data must be regenerable from raw/canonical evidence. Foundation code does not overwrite collected source evidence.
