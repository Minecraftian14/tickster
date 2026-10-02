# v0.3.0 — Identity + Temporal Engine

## Identity

The identity layer provides a canonical instrument registry with source-specific aliases.
Aliases can carry `valid_from` and `valid_to`; resolution can therefore be evaluated at a
historical point in time. Ambiguity is explicit via `IdentityAmbiguityError`.

## Temporal availability

The temporal layer distinguishes event time from knowledge availability. `published_at`,
`received_at`, and `observed_at` are stronger evidence of availability than retrieval time.
Strict point-in-time queries exclude records whose only availability signal is retrieval time.
Effective dates are not treated as disclosure timestamps.

## Core queries

- `IdentityRegistry.company.resolve(query, as_of=...)`
- `IdentityRegistry.instrument.aliases(instrument, as_of=...)`
- `TemporalIndex.what_was_known_at(company_or_instrument, as_of=...)`
- `TemporalIndex.events_between(company_or_instrument, start, end, ...)`
- `TemporalIndex.documents_available_at(company_or_instrument, as_of=...)`

All queries are factual and non-predictive. They form the point-in-time substrate for later
enrichment and LLM representation packages.
