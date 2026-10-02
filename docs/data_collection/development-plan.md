# Development plan

## Chosen strategy: domain-first with provider probes inside each domain

We will not start by installing every candidate library. That produces lots of disconnected demos and does not establish the canonical data model.

Instead:

1. **Instrument domain**: define canonical identity and mapping requirements (ISIN, NSE symbol, instrument key, company name, active status, sector/industry where available).
2. **Market domain**: finish daily OHLCV end-to-end using yfinance + NSE, then add one operational broker feed (Upstox). Keep raw responses and provenance.
3. **Corporate actions**: normalize dividends/splits/bonus/rights/buybacks and test reconciliation against price history.
4. **Fundamentals/shareholding**: collect statements, ratios, profiles, ownership. Candidate structured sources such as Stoxim are evaluated here.
5. **Company events/filings**: build the document ingestion path from exchange/regulatory/company sources.
6. **News**: build event-oriented news collection, not just sentiment scores.
7. **Macro**: RBI data and release metadata.

Every domain has a provider-test matrix. The matrix is evidence for source selection, not the primary development objective.

## Storage principle

For every fetched item we retain:

- the raw provider payload (or immutable reference to it),
- the canonical normalized record,
- source/provider,
- source dataset/endpoint,
- observed/published/retrieved timestamps where applicable,
- request parameters,
- retrieval errors.

## No F&O in v1

The project is equities-only. Futures/options/open-interest/Greeks/option-chain collectors are excluded from v1, though the interfaces can be extended later.

## No BSE in v1

BSE is intentionally excluded from the working architecture. It can be added as an independent provider later without changing domain models.
