"""Provider-neutral collection of public India-market forum evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from data_collection.collection.results import CollectionResult, RawPayload
from data_collection.domains import SocialPost
from data_collection.providers.reddit import RedditProvider


DEFAULT_INDIA_MARKET_SUBREDDITS = ("IndianStreetBets", "IndianStockMarket", "IndiaInvestments")


class SocialCollector:
    domain = "social"

    def __init__(self, *, reddit: RedditProvider | None = None) -> None:
        self.reddit = reddit

    def forum_search(self, query: str, *, instrument_ids: Iterable[str] = (), subreddits: tuple[str, ...] = DEFAULT_INDIA_MARKET_SUBREDDITS, limit: int = 25) -> CollectionResult[SocialPost]:
        result: CollectionResult[SocialPost] = CollectionResult(domain=self.domain)
        if self.reddit is None:
            result.errors.append({"source": "reddit", "operation": "forum_search", "error": "provider is not configured"})
            return result
        try:
            records, raw = self.reddit.search(query, subreddits=subreddits, instrument_ids=list(instrument_ids), limit=limit)
            unique: dict[str, SocialPost] = {record.social_id: record for record in records}
            result.records.extend(unique.values())
            result.raw_payloads.append(RawPayload(source="reddit", domain=self.domain, retrieved_at=datetime.now(timezone.utc), payload=raw, request={"query": query, "subreddits": subreddits, "limit": limit}))
        except Exception as exc:
            result.add_error(source="reddit", operation="forum_search", exc=exc, query=query)
        return result
