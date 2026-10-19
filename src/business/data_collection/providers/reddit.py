"""Public Reddit JSON provider for India-market discussion evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

import httpx

from data_collection.domains import Provenance, SocialPost


class RedditProvider:
    """Read public subreddit search results without credentials or hidden state."""

    name = "reddit"
    source_type = "reddit_json"

    def __init__(self, *, timeout: float = 20.0, client: httpx.Client | None = None) -> None:
        self.timeout = timeout
        self.client = client

    def search(self, query: str, *, subreddits: tuple[str, ...], instrument_ids: list[str] | None = None, limit: int = 25) -> tuple[list[SocialPost], list[dict[str, Any]]]:
        posts: list[SocialPost] = []
        raw: list[dict[str, Any]] = []
        headers = {"User-Agent": "TicksterResearch/0.1 public evidence collector"}
        for subreddit in subreddits:
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            params = {"q": query, "restrict_sr": "on", "sort": "new", "limit": min(limit, 100)}
            client = self.client or httpx.Client(timeout=self.timeout, headers=headers)
            close_client = self.client is None
            try:
                response = client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
                raw.append({"subreddit": subreddit, "payload": payload})
                now = datetime.now(timezone.utc)
                for child in payload.get("data", {}).get("children", []):
                    item = child.get("data", {})
                    permalink = item.get("permalink")
                    post_url = f"https://www.reddit.com{permalink}" if permalink else None
                    created = item.get("created_utc")
                    published = datetime.fromtimestamp(created, timezone.utc) if isinstance(created, (int, float)) else None
                    text = (item.get("selftext") or item.get("title") or "").strip()
                    if not text:
                        continue
                    post_id = str(item.get("id") or sha256(f"{subreddit}|{post_url}|{text}".encode()).hexdigest())
                    posts.append(SocialPost(
                        social_id=f"reddit:{post_id}", instrument_ids=instrument_ids or [], platform="reddit",
                        author=item.get("author"), title=item.get("title"), text=text, url=post_url,
                        published_at=published, metadata={"subreddit": subreddit, "score": item.get("score")},
                        provenance=Provenance(source=self.name, source_type=self.source_type, source_url=post_url or url,
                                              retrieved_at=now, published_at=published),
                    ))
            finally:
                if close_client:
                    client.close()
        return posts, raw
