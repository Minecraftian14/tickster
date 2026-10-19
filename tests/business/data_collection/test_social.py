from datetime import datetime, timezone

from data_collection.collection.social import SocialCollector
from data_collection.domains import Provenance, SocialPost


class FakeReddit:
    def search(self, query, *, subreddits, instrument_ids, limit):
        now = datetime.now(timezone.utc)
        post = SocialPost(social_id="reddit:1", instrument_ids=instrument_ids, platform="reddit", text="TEST discussion", provenance=Provenance(source="reddit", source_type="fixture", retrieved_at=now))
        return [post, post], [{"fixture": True}]


def test_social_collector_deduplicates_and_keeps_raw_payload():
    result = SocialCollector(reddit=FakeReddit()).forum_search("TEST", instrument_ids=["NSE:TEST"])
    assert [post.social_id for post in result.records] == ["reddit:1"]
    assert result.raw_payloads[0].request["query"] == "TEST"


def test_social_collector_records_unconfigured_provider():
    result = SocialCollector().forum_search("TEST")
    assert result.records == []
    assert result.errors[0]["source"] == "reddit"
