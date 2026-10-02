# Indian Equity Data Coverage

The project is **domain-first**. Providers are adapters behind domain collectors; raw payloads and diagnostics are retained alongside canonical records.

## Completed domains

- Instruments: NSE cash-equity identity, identifier mapping, Upstox search/BOD paths.
- Market: daily history, exchange EOD/delivery, current LTP/full quotes, historical chunking, source reconciliation.
- Fundamentals: Upstox profile, period-aware income statement/balance sheet/cash-flow snapshots, ratios, shareholding, competitor profiles.
- Corporate actions: Upstox company actions + NSE archive actions.
- Company events: NSE announcements + board meetings.
- Ownership / market events: shareholding, insider/PIT transactions, bulk deals, block deals, short-selling disclosures.
- Filings / documents: NSE filing catalogs, attachments, XBRL facts, annual reports and related metadata.
- News: yfinance news plus RSS/Google News/publisher feeds.
- Indices / context: index snapshots, constituents, historical index data, valuation, sector/industry classifications.
- Macro: RBI/DBIE and MOSPI CPI/IIP collection.
- Regulatory: SEBI listings, detail records and linked documents.

## Hardening milestone

The next implementation milestone tightens the collection foundation rather than adding another large data universe:

1. package/import identity,
2. version metadata,
3. historical-request chunking,
4. richer market quotes,
5. period-aware fundamentals,
6. persistent raw evidence,
7. source-aware observation preservation,
8. filing/asset relationships,
9. observable parser issues,
10. synchronized documentation/source registry.

## Scope exclusions

- BSE is intentionally excluded from the working architecture.
- F&O is excluded from v1.
- AMFI/mutual-fund data is deferred.
- Intraday is supported but is not the latency/optimization focus.
