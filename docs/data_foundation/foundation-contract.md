# v1.0.0 — Foundation contract

This document defines the stable boundary between `data_collection` and downstream packages.

## Contract metadata

- Package: `indian-equity-data-foundation`
- Package version: `1.0.0`
- Foundation contract: `1.0`
- Upstream collection package: `indian-equity-data-platform`
- Minimum collection version: `1.1.0`
- Persistence format: `1`

The machine-readable equivalent is available through `data_foundation.contract_manifest()`.

## Stable guarantees

### Evidence
Canonical records reference source observations; source observations reference raw artifacts. Raw artifacts
are immutable and content-addressed.

### Time
Point-in-time queries use published/received/observed availability before retrieval-only availability.
Effective dates do not, by themselves, prove prior market knowledge.

### Identity
Provider aliases are resolved through `IdentityRegistry`; ambiguous resolution raises
`IdentityAmbiguityError` rather than silently choosing a candidate.

### Reconciliation
Cross-source comparison produces explicit statuses and optional deterministic decisions. Material conflicts are
not silently resolved.

### Graph/timeline
Relationships are factual and evidence-carrying. Timelines are chronological views of records and retain
provenance. No semantic or predictive inference occurs here.

## Persistence

The stable persistence layout is described in the package README. Consumers should use `FoundationStore` and
not depend on provider-specific filenames or payload formats.

## Public API

The intended public surface is exported from `data_foundation`. Consumers should prefer those root imports over
internal modules. Internal modules may be reorganized in minor/patch releases so long as the public contract remains
compatible.

## Downstream boundary

The next package, `data_enrichment`, may depend on this contract without depending directly on any collection
provider.
