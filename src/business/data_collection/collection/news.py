from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Iterable

from data_collection.collection.results import CollectionResult, RawPayload
from data_collection.domains.models import Instrument, NewsItem
from data_collection.providers.rss import RSSNewsProvider
from data_collection.providers.yfinance import YahooFinanceProvider, parse_yfinance_news_item


class NewsCollector:
    """Provider-neutral collector for Indian-equity news and syndicated items."""

    domain = "news"

    def __init__(self, *, yfinance: YahooFinanceProvider | None = None, rss_providers: Iterable[RSSNewsProvider] = ()):
        self.yfinance = yfinance
        self.rss_providers = list(rss_providers)

    @staticmethod
    def _canonical_ids(instrument: Instrument | None, instrument_ids: list[str] | None) -> list[str]:
        if instrument_ids:
            return list(dict.fromkeys(instrument_ids))
        return [instrument.instrument_id] if instrument else []

    def ticker_news(
        self,
        symbol: str,
        *,
        instrument: Instrument | None = None,
        count: int = 10,
        tab: str = "news",
    ) -> CollectionResult[NewsItem]:
        result: CollectionResult[NewsItem] = CollectionResult(domain=self.domain)
        if self.yfinance is None:
            result.errors.append({"source": "yfinance", "error": "provider is not configured"})
            return result
        try:
            raw = self.yfinance.get_news_raw(symbol, count=count, tab=tab)
            ids = self._canonical_ids(instrument, None)
            now = datetime.now(timezone.utc)
            records = [parse_yfinance_news_item(item, instrument_ids=ids, retrieved_at=now) for item in raw]
            result.records.extend([item for item in records if item is not None])
            result.raw_payloads.append(RawPayload(
                source="yfinance",
                domain=self.domain,
                retrieved_at=now,
                payload=raw,
                request={"symbol": symbol, "count": count, "tab": tab},
            ))
        except Exception as exc:
            result.errors.append({"source": "yfinance", "error": str(exc)})
        return result

    def feeds(self, *, instrument_ids: list[str] | None = None, limit: int | None = None) -> CollectionResult[NewsItem]:
        result: CollectionResult[NewsItem] = CollectionResult(domain=self.domain)
        for provider in self.rss_providers:
            try:
                raw_records, fetch_meta = provider.fetch()
                now = datetime.now(timezone.utc)
                records = provider.records_to_news(raw_records, instrument_ids=instrument_ids)
                if limit is not None:
                    records = records[:limit]
                result.records.extend(records)
                result.raw_payloads.append(RawPayload(
                    source=provider.name,
                    domain=self.domain,
                    retrieved_at=now,
                    payload=raw_records,
                    request={"feed_url": provider.feed_url, "fetch": fetch_meta},
                ))
            except Exception as exc:
                result.errors.append({"source": provider.name, "feed_url": provider.feed_url, "error": str(exc)})
        return deduplicate_news(result)

    def company_search(self, query: str, *, instrument: Instrument | None = None, count: int = 10) -> CollectionResult[NewsItem]:
        """Search Yahoo Finance for news by company name/ticker.

        This complements Ticker.news: Yahoo's Search API can return news for a
        company-name query rather than requiring a resolved ticker.
        """
        result: CollectionResult[NewsItem] = CollectionResult(domain=self.domain)
        if self.yfinance is None:
            result.errors.append({"source": "yfinance", "error": "provider is not configured"})
            return result
        try:
            raw = self.yfinance.search_news_raw(query, news_count=count)
            now = datetime.now(timezone.utc)
            ids = self._canonical_ids(instrument, None)
            records = [parse_yfinance_news_item(item, instrument_ids=ids, retrieved_at=now) for item in raw]
            result.records.extend([item for item in records if item is not None])
            result.raw_payloads.append(RawPayload(
                source="yfinance",
                domain=self.domain,
                retrieved_at=now,
                payload=raw,
                request={"query": query, "news_count": count},
            ))
        except Exception as exc:
            result.errors.append({"source": "yfinance", "error": str(exc)})
        return result


def deduplicate_news(result: CollectionResult[NewsItem]) -> CollectionResult[NewsItem]:
    seen: set[str] = set()
    unique: list[NewsItem] = []
    for item in result.records:
        key = item.url or sha256(f"{item.title}|{item.published_at}|{item.source_name}".encode("utf-8")).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    result.records = unique
    return result
