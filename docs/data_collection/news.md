# News collection

The news domain is intentionally split into **syndicated news** and **official company disclosures**.
Official NSE announcements/filings remain authoritative company-event/document sources. This domain adds third-party or aggregator news that may provide context, reactions, interviews and coverage that are not present in exchange filings.

## Sources currently supported

### yfinance

The current yfinance API exposes `Ticker.get_news(count, tab)` and `Search(query, news_count=...)`. We retain the raw Yahoo payload and normalize title, URL, publisher and publication timestamp. yfinance is an aggregator rather than an Indian-exchange authority.

### Generic RSS/Atom

`RSSNewsProvider` consumes a configured RSS or Atom URL without scraping the destination article. It stores the feed item, excerpt/summary where provided, canonical link, publication time, categories and raw entry XML.

`GoogleNewsRSSProvider` is a convenience wrapper for a Google News search RSS URL. Google News exposes RSS feeds for searches, allowing company/sector queries without a dedicated API key.

Useful publisher feeds currently discoverable from publisher pages include:

- Economic Times markets/stocks RSS
- Business Standard market-news RSS

Publisher terms differ. In particular, the Economic Times RSS terms state that its RSS is provided for personal, non-commercial use and restrict storage/republication. The collector therefore treats publisher RSS as a metadata/excerpt source and does not fetch full articles by default.

## Design rule

News collection does **not** perform event extraction, sentiment analysis, entity linking, deduplication across publishers, or article summarization beyond preserving source-provided excerpts. Those are processing/enrichment tasks for a later layer.

Each `NewsItem` preserves provenance and distinguishes publication time from retrieval time so later point-in-time research can exclude information that was not yet available.
