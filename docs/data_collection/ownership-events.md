# Ownership and Market Events

## Scope

This slice covers structured ownership and market-event disclosures for NSE cash equities:

- Quarterly shareholding patterns
- SEBI PIT insider transactions
- Bulk deals
- Block deals
- Short-selling daily reports

It intentionally excludes F&O and mutual-fund data.

## Sources

### NSE public corporate APIs

- `corporate-share-holdings-master`: per-symbol shareholding filing history and XBRL links.
- `corporates-pit`: Regulation 7(2) insider-trading disclosures over a date range.
- `snapshot-capital-market-largedeal`: current bulk/block/short-deal snapshots.

The adapter warms an NSE session before API calls and preserves raw payloads. These endpoints are exchange-published, but they are public web APIs rather than a stable, formally versioned developer API; callers should expect session/cookie or schema changes.

### NSE archives

The archive adapter additionally exposes dated bulk-deal, block-deal and short-selling reports. The raw archive row remains attached to the canonical object so the parser can be expanded without recollecting historical files.

## Canonical objects

`ShareholdingSnapshot`, `InsiderTransaction`, and `LargeDeal` are intentionally richer than the first set of promoted fields. Each retains `details` plus source provenance.

## Point-in-time rule

For any future backtest, do not use the quarter-end/shareholding period as the information-availability time. Preserve filing/broadcast timestamps where available. The same principle applies to insider and deal disclosures.

## Redundancy

`NSEPublicProvider` and `NSEArchivesProvider` are not independent market-data vendors: both expose NSE-originated information through different access paths. They are useful as complementary access mechanisms and for validation, not as distinct economic sources.
