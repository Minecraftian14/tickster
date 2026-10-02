# Data Collection Architecture

## Strategy

Develop **domain-first**, with provider adapters hidden underneath each domain.

The platform is a provider-agnostic Indian NSE cash-equity data layer. The public application depends on domain contracts; individual sources remain replaceable.

## Layers

1. **Provider** — yfinance, Upstox, NSE archive/access paths, RBI, MOSPI, SEBI, RSS and later alternatives.
2. **Collection** — high-level functions by data kind; preserve raw responses, request parameters, provenance and diagnostics.
3. **Canonical domain model** — stable Pydantic objects independent of provider schemas.
4. **Processing/enrichment** — validation, source-aware deduplication, reconciliation, then indicators/events/NLP/entity resolution.
5. **Representation/export** — JSON/JSONL/Markdown/Parquet and later RAG-oriented views.
6. **Persistent evidence** — raw provider payloads are stored separately using content-addressed artifacts.

## Identity

For cash equities, `instrument_id` prefers ISIN. Provider identifiers remain separate fields. Upstox `instrument_key` is retained for API calls.

## Time semantics

Canonical records distinguish:

- `published_at`: when information was published/disseminated.
- `observed_at`: when a market observation occurred.
- `retrieved_at`: when our collector fetched it.

These are deliberately separate to reduce look-ahead bias in later research/backtests.

## Market source strategy

- **yfinance** — broad historical aggregation and research convenience.
- **NSE** — exchange-originated reference/archive data.
- **Upstox** — operational market data and structured company fundamentals.
- **NSE wrappers** — `indian-market-data`, `jugaad-data`, and `NSEPython` are alternative access mechanisms to the NSE information universe rather than independent sources.
- **Other brokers** — FYERS, Dhan, Angel One and Zerodha remain interchangeable alternatives for broker market data.

## Raw evidence

A `CollectionResult` can contain:

- canonical records,
- raw payloads,
- related records (for example filing assets),
- request errors,
- parser/data-quality issues.

Raw payloads can be persisted as immutable, content-addressed JSON artifacts under `storage/raw.py`.

## Market reconciliation

Multiple provider observations are retained by source until reconciliation. `deduplicate_price_bars(..., preserve_sources=True)` is the default. Explicit cross-source collapsing is available through `collapse_price_sources()`.

## Scope

v1 is **NSE cash equities only**. F&O is deliberately excluded.
