from datetime import datetime, timezone

from data_collection.collection.news import NewsCollector, deduplicate_news
from data_collection.domains.models import NewsItem, Provenance
from data_collection.providers.rss import (
    BusinessStandardRSSProvider,
    EconomicTimesRSSProvider,
    GoogleNewsRSSProvider,
    RSSNewsProvider,
    parse_rss_or_atom,
)
from data_collection.providers.yfinance import parse_yfinance_news_item

NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)


RSS_FIXTURE = b'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Market News</title>
    <item>
      <title>Reliance announces new capacity</title>
      <link>https://example.com/reliance-capacity</link>
      <guid>abc-1</guid>
      <pubDate>Fri, 02 Oct 2026 09:30:00 +0530</pubDate>
      <description>&lt;p&gt;New capacity details.&lt;/p&gt;</description>
      <category>Companies</category>
    </item>
  </channel>
</rss>'''


ATOM_FIXTURE = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>TCS outlook update</title>
    <id>tag:example.com,2026:tcs-1</id>
    <link href="https://example.com/tcs" />
    <updated>2026-10-02T09:45:00+05:30</updated>
    <summary>Business outlook update</summary>
  </entry>
</feed>'''


def test_parse_rss_extracts_metadata_and_normalizes_time():
    records = parse_rss_or_atom(RSS_FIXTURE, source_name="Example", source_url="https://example.com/feed")
    assert len(records) == 1
    item = records[0]
    assert item["title"] == "Reliance announces new capacity"
    assert item["url"] == "https://example.com/reliance-capacity"
    assert item["summary"] == "New capacity details."
    assert item["published_at"] == datetime(2026, 10, 2, 4, 0, tzinfo=timezone.utc)
    assert item["categories"] == ["Companies"]


def test_parse_atom_extracts_link_and_time():
    records = parse_rss_or_atom(ATOM_FIXTURE, source_name="Example", source_url="https://example.com/feed")
    assert len(records) == 1
    assert records[0]["url"] == "https://example.com/tcs"
    assert records[0]["published_at"] == datetime(2026, 10, 2, 4, 15, tzinfo=timezone.utc)


def test_rss_provider_preserves_raw_entry_and_source_provenance():
    class StubProvider(RSSNewsProvider):
        def fetch(self):
            return parse_rss_or_atom(RSS_FIXTURE, source_name=self.source_name, source_url=self.feed_url), {"status_code": 200}

    provider = StubProvider("https://example.com/feed", source_name="Example News")
    raw, _ = provider.fetch()
    items = provider.records_to_news(raw, instrument_ids=["INE002A01018"])
    assert len(items) == 1
    item = items[0]
    assert item.instrument_ids == ["INE002A01018"]
    assert item.source_name == "Example News"
    assert item.provenance.source == "rss"
    assert item.metadata["guid"] == "abc-1"
    assert "<item>" in item.metadata["raw_entry"]


def test_google_news_search_builds_india_feed_url():
    provider = GoogleNewsRSSProvider.search("Reliance Industries stock")
    assert provider.feed_url.startswith("https://news.google.com/rss/search?q=Reliance+Industries+stock")
    assert "hl=en-IN" in provider.feed_url
    assert "gl=IN" in provider.feed_url
    assert "ceid=IN%3Aen" in provider.feed_url


def test_publisher_feed_presets_have_current_urls():
    assert EconomicTimesRSSProvider.DEFAULT_FEED_URL == "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"
    assert BusinessStandardRSSProvider.DEFAULT_FEED_URL == "https://www.business-standard.com/rss/markets-106.rss"


def test_yfinance_news_parser_handles_epoch_and_is_stable():
    raw = {
        "id": "yahoo-123",
        "content": {
            "title": "Reliance update",
            "pubDate": "2026-10-02T09:30:00+05:30",
            "canonicalUrl": {"url": "https://example.com/reliance"},
            "provider": {"displayName": "Example Wire"},
            "summary": "Company update",
        },
    }
    item = parse_yfinance_news_item(raw, instrument_ids=["INE002A01018"], retrieved_at=NOW)
    assert item is not None
    assert item.news_id == parse_yfinance_news_item(raw, instrument_ids=["INE002A01018"], retrieved_at=NOW).news_id
    assert item.published_at == datetime(2026, 10, 2, 4, 0, tzinfo=timezone.utc)
    assert item.source_name == "Example Wire"
    assert item.text == "Company update"


def test_news_deduplication_prefers_unique_urls():
    base = dict(title="Same", published_at=NOW, url="https://example.com/a", source_name="x", provenance=Provenance(source="test", source_type="fixture", retrieved_at=NOW))
    from data_collection.collection.results import CollectionResult
    coll = CollectionResult(domain="news", records=[NewsItem(news_id="1", **base), NewsItem(news_id="2", **base)])
    deduplicate_news(coll)
    assert len(coll.records) == 1


def test_collector_returns_error_without_yfinance():
    result = NewsCollector().ticker_news("RELIANCE")
    assert result.domain == "news"
    assert result.errors[0]["source"] == "yfinance"
