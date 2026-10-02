# Data Collection Architecture

## Strategy

Develop **domain-first**, with provider adapters hidden underneath each domain.

The first completed spine is:

`Instrument → Market → Processing → Export`

## Layers

1. **Provider** — yfinance, Upstox, NSE archive access, and later alternatives.
2. **Collection** — high-level functions by data kind; preserve raw responses and provenance.
3. **Canonical domain model** — stable Pydantic objects independent of provider schemas.
4. **Processing/enrichment** — validation, deduplication, reconciliation, then indicators/events/NLP.
5. **Representation/export** — JSON/JSONL/Markdown/Parquet and later RAG-oriented views.

## Identity

For cash equities, `instrument_id` prefers ISIN. Provider identifiers remain in separate fields. Upstox recommends `instrument_key` rather than `exchange_token` for API identity because exchange tokens can be reused. This gives us a stable internal identity while retaining the provider key needed for API calls.

## Market providers

- **yfinance** — broad, easy historical aggregation.
- **NSE** — exchange-originated archive/reference data.
- **Upstox** — live/current and intraday market API plus structured company fundamentals.

The collection layer can retain multiple observations; processing decides how to reconcile them.

## Scope

v1 is **NSE cash equities only**. F&O is deliberately excluded.
