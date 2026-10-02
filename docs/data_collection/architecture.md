# Architecture

## Collection -> canonical -> enrichment -> export

```text
SOURCE ADAPTERS
  yfinance / NSE / Upstox / wrappers / RBI / SEBI / etc.
                 |
                 v
DOMAIN COLLECTORS
  instruments / market / corporate_actions / fundamentals /
  shareholding / company_events / filings / news / macro
                 |
                 v
RAW STORE + CANONICAL OBJECTS
  normalized records carrying provenance and source references
                 |
                 v
PROCESSING / ENRICHMENT
  normalize -> dedupe -> reconcile -> adjust -> derive -> NLP
                 |
                 v
EXPORT / REPRESENTATION
  JSON / Markdown / Parquet / LLM context / RAG / search / KG
```

## Domain-first development order

1. Instruments
2. Market/price history
3. Corporate actions
4. Fundamentals + shareholding
5. Company events + filings
6. News
7. Macro

Each domain gets a small source-probe suite. The probe is not the architecture; it is evidence used to select/replace provider adapters.

## Why provider adapters are separate

`yfinance`, `indian-market-data`, `jugaad-data`, and `NSEPython` overlap heavily on NSE access. Likewise Upstox, FYERS, Dhan, Angel One and Zerodha overlap as broker data APIs. They should therefore be interchangeable implementations behind a domain contract rather than dependencies spread throughout the codebase.
