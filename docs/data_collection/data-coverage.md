# Indian Equity Data Coverage

This project is **domain-first**. Providers are adapters behind domain collectors; raw payloads are retained as evidence and canonical models carry provenance.

## Completed domains

- Instruments: NSE cash-equity identity via Upstox search/BOD data path.
- Market: daily/intraday history, LTP, full quote, NSE EOD/delivery, reconciliation hooks.
- Fundamentals: Upstox profile, statements, ratios, shareholding.
- Corporate actions: Upstox company-level actions + NSE archive actions.
- Company events: NSE corporate announcements + board meetings.

## Next high-value domains

1. Ownership / insider transactions / bulk-block deals
2. Filings and document ingestion
3. News and event enrichment
4. Index membership and benchmark context
5. Macro / regulatory context

## Source strategy

- `yfinance`: broad secondary aggregation and research convenience.
- `NSE`: primary Indian exchange reference and archive source.
- `Upstox`: operational market data and structured company fundamentals.
- `jugaad-data`, `NSEPython`, `indian-market-data`: alternative NSE access mechanisms, not independent information universes.
- Other broker APIs (`FYERS`, `Dhan`, `Angel One`, `Zerodha`) remain interchangeable alternatives to Upstox for market-data access.

## Time semantics

All canonical records should preserve, where available:

- `published_at`: when the information was published/disseminated.
- `observed_at`: when the market observation occurred.
- `retrieved_at`: when our collector fetched it.

These are intentionally separate to reduce look-ahead bias in later research/backtests.
