# Index / Benchmark / Sector Context

## Scope

This domain covers:

- historical NSE index OHLC from the `ind_close_all` archive;
- daily index valuation fields such as P/E, P/B and dividend yield from the NSE `PE` report;

- current NSE index snapshots from `GET /api/allIndices`;
- current index constituents from `GET /api/equity-stockIndices?index=...`;
- NSE company sector/industry/basic-industry classification from `GET /api/quote-equity?symbol=...`.

NSE's current index pages publish downloadable constituent lists for major indexes such as Nifty 50, Nifty 100, Nifty 200 and Nifty 500, while its reports catalogue exposes daily index/market-cap/weightage reports. The live JSON constituent endpoint is a convenient collection path; historical membership is a separate capability that should be reconstructed from dated snapshots/rebalance sources rather than inferred from today's list.

## Canonical objects

- `IndexSnapshot`
- `IndexConstituent`
- `SectorClassification`

All retain the raw provider payload and provenance.

## Source notes

`yfinance` also exposes sector/industry helpers and ticker `info` fields, but the primary classification for the Indian project should remain NSE-derived. The yfinance sector/industry API is useful as a secondary cross-check rather than as the canonical Indian classification.

## Historical membership limitation

The live NSE constituent endpoint is a point-in-time snapshot. Historical membership should not be reconstructed by assuming the current list applies to the past. For that later phase, dated constituent snapshots/rebalance disclosures should be stored as membership intervals.
