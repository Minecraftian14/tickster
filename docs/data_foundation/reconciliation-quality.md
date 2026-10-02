# v0.4.0 — Reconciliation and Quality Engine

This milestone makes source comparison and data quality explicit foundation concerns.
It does not perform predictive interpretation or semantic enrichment.

## Reconciliation

Numeric observations are grouped by `(entity_key, field)` and classified as:

- `agree`
- `minor_difference`
- `conflicting`
- `missing`
- `unresolvable`

Thresholds can be configured with absolute and relative tolerances. Expected source names can
be supplied so missing provider coverage is visible rather than silently ignored.

`reconcile_numeric_with_decisions()` returns both the finding and an explicit
`ReconciliationDecision`. Canonical selection is deterministic according to a source-priority
policy. Material conflicts are left unresolved unless the caller explicitly allows a conflict
selection.

## Quality

`build_quality_report()` combines independent checks for:

- missing required fields
- stale observations
- duplicates
- timestamp anomalies
- JSON-like schema drift
- identity ambiguity
- invalid numeric values

The report exposes category and severity summaries and a `passed` property. Quality findings are
kept separate from the older value-level `DataQuality` status so that `None` does not have to carry
the explanation for a detected data problem.

## Boundary

The engine works from canonical records, source observations, identity registries, and raw-like
payloads. It does not change the `data_collection` package and does not infer investment meaning.
