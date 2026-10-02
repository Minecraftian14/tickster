from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
from html import unescape
from typing import Any
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

import httpx

from data_collection.domains.models import NewsItem, Provenance


def _strip_markup(value: Any) -> str | None:
    if value is None:
        return None
    text = unescape(str(value))
    # Lightweight, dependency-free HTML cleanup suitable for RSS excerpts.
    import re
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, "", 0):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    try:
        parsed = parsedate_to_datetime(text)
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        from dateutil.parser import parse
        parsed = parse(text)
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _children_by_local_name(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(element) if _local_name(child.tag) == name.lower()]


def _first_text(element: ET.Element, *names: str) -> str | None:
    wanted = {name.lower() for name in names}
    for child in list(element):
        if _local_name(child.tag) in wanted:
            value = "".join(child.itertext()).strip()
            if value:
                return value
    return None


def _first_link(element: ET.Element) -> str | None:
    for child in list(element):
        if _local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        if href:
            return href.strip()
        value = "".join(child.itertext()).strip()
        if value:
            return value
    return None


def parse_rss_or_atom(payload: bytes | str, *, source_name: str, source_url: str) -> list[dict[str, Any]]:
    root = ET.fromstring(payload)
    root_name = _local_name(root.tag)
    if root_name == "rss":
        containers = _children_by_local_name(root, "channel")
        container = containers[0] if containers else root
        entries = _children_by_local_name(container, "item")
    elif root_name == "feed":
        container = root
        entries = _children_by_local_name(container, "entry")
    else:
        entries = [node for node in root.iter() if _local_name(node.tag) in {"item", "entry"}]

    records: list[dict[str, Any]] = []
    for entry in entries:
        title = _first_text(entry, "title") or ""
        link = _first_link(entry)
        summary = _first_text(entry, "description", "summary", "content", "encoded")
        published = _parse_datetime(_first_text(entry, "pubdate", "published", "updated", "date"))
        guid = _first_text(entry, "guid", "id")
        author = _first_text(entry, "creator", "author")
        categories = [
            "".join(node.itertext()).strip()
            for node in entry
            if _local_name(node.tag) == "category" and "".join(node.itertext()).strip()
        ]
        records.append({
            "title": _strip_markup(title) or "",
            "url": link,
            "summary": _strip_markup(summary),
            "published_at": published,
            "guid": guid,
            "author": author,
            "categories": categories,
            "source_name": source_name,
            "feed_url": source_url,
            "raw": ET.tostring(entry, encoding="unicode"),
        })
    return records


class RSSNewsProvider:
    """Generic RSS/Atom collector with no source-specific scraping."""

    name = "rss"
    source_type = "rss"

    def __init__(self, feed_url: str, *, source_name: str | None = None, timeout: float = 20.0, headers: dict[str, str] | None = None):
        self.feed_url = feed_url
        self.source_name = source_name or feed_url
        default_headers = {
            "User-Agent": "IndianEquityDataPlatform/0.6+ (RSS reader)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        }
        if headers:
            default_headers.update(headers)
        self.client = httpx.Client(timeout=timeout, headers=default_headers, follow_redirects=True)

    def close(self) -> None:
        self.client.close()

    def health(self) -> dict[str, Any]:
        return {"provider": self.name, "source_name": self.source_name, "feed_url": self.feed_url, "configured": True}

    def fetch(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        response = self.client.get(self.feed_url)
        response.raise_for_status()
        body = response.content
        records = parse_rss_or_atom(body, source_name=self.source_name, source_url=self.feed_url)
        return records, {
            "url": str(response.url),
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "byte_size": len(body),
            "sha256": sha256(body).hexdigest(),
        }

    def records_to_news(self, records: list[dict[str, Any]], *, instrument_ids: list[str] | None = None) -> list[NewsItem]:
        now = datetime.now(timezone.utc)
        ids = instrument_ids or []
        items: list[NewsItem] = []
        for record in records:
            fingerprint = record.get("guid") or record.get("url") or f"{record.get('title','')}|{record.get('published_at')}"
            news_id = f"rss:{sha256(f'{self.feed_url}|{fingerprint}'.encode('utf-8')).hexdigest()[:32]}"
            items.append(NewsItem(
                news_id=news_id,
                instrument_ids=ids.copy(),
                title=record["title"],
                published_at=record.get("published_at"),
                url=record.get("url"),
                text=record.get("summary"),
                source_name=self.source_name,
                metadata={
                    "guid": record.get("guid"),
                    "author": record.get("author"),
                    "categories": record.get("categories", []),
                    "feed_url": self.feed_url,
                    "raw_entry": record.get("raw"),
                },
                provenance=Provenance(
                    source=self.name,
                    source_type=self.source_type,
                    source_dataset=self.source_name,
                    source_url=self.feed_url,
                    retrieved_at=now,
                    published_at=record.get("published_at"),
                ),
            ))
        return items

    def collect_news(self, *, instrument_ids: list[str] | None = None) -> list[NewsItem]:
        records, _ = self.fetch()
        return self.records_to_news(records, instrument_ids=instrument_ids)


class GoogleNewsRSSProvider(RSSNewsProvider):
    """Convenience provider for a Google News search RSS feed.

    Google News exposes RSS feeds for searches; this provider intentionally
    stores the syndicated item and link, rather than scraping the destination.
    """

    name = "google_news_rss"
    source_type = "rss_aggregator"

    @classmethod
    def search(cls, query: str, *, hl: str = "en-IN", gl: str = "IN", ceid: str = "IN:en", **kwargs: Any) -> "GoogleNewsRSSProvider":
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl={quote_plus(hl)}&gl={quote_plus(gl)}&ceid={quote_plus(ceid)}"
        return cls(url, source_name=f"Google News: {query}", **kwargs)


class EconomicTimesRSSProvider(RSSNewsProvider):
    """Economic Times Markets/Stocks RSS feed. Publisher terms apply."""

    name = "economic_times_rss"
    source_type = "publisher_rss"
    DEFAULT_FEED_URL = "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"

    def __init__(self, feed_url: str = DEFAULT_FEED_URL, **kwargs: Any):
        super().__init__(feed_url, source_name="Economic Times Markets/Stocks", **kwargs)


class BusinessStandardRSSProvider(RSSNewsProvider):
    """Business Standard Market News RSS feed."""

    name = "business_standard_rss"
    source_type = "publisher_rss"
    DEFAULT_FEED_URL = "https://www.business-standard.com/rss/markets-106.rss"

    def __init__(self, feed_url: str = DEFAULT_FEED_URL, **kwargs: Any):
        super().__init__(feed_url, source_name="Business Standard Market News", **kwargs)
