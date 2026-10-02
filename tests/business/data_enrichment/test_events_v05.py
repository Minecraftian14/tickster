from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from data_foundation import CanonicalRecord
from data_enrichment import CompanyEventSummaryEnricher, EnrichmentContext, EventReactionEnricher

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def rec(rid, instrument, payload):
    return CanonicalRecord(record_id=rid, domain="test", record_type="X", payload={"instrument_id": instrument, **payload})


def bar(rid, day, close):
    ts = BASE + timedelta(days=day)
    return rec(rid, "TARGET", {"timestamp": ts, "close": close, "published_at": ts})


def event(rid, day, kind="acquisition", subject="Event"):
    ts = BASE + timedelta(days=day)
    return rec(rid, "TARGET", {"event_date": ts, "event_type": kind, "subject": subject, "published_at": ts})


def test_company_event_summary_counts_types():
    events = [event("e1", 1, "acquisition"), event("e2", 2, "acquisition"), event("e3", 10, "board_meeting")]
    result = CompanyEventSummaryEnricher(windows_days=(30,)).enrich(EnrichmentContext([], instrument_id="TARGET", metadata={"event_records": events}))
    values = result.summaries[0].values
    assert values["event_count"] == 3
    assert values["event_type_counts"] == {"acquisition": 2, "board_meeting": 1}
    assert values["distinct_event_types"] == 2


def test_event_summary_respects_as_of_visibility():
    events = [event("e1", 1), event("e2", 20)]
    result = CompanyEventSummaryEnricher(windows_days=(365,)).enrich(EnrichmentContext(
        [], instrument_id="TARGET", as_of=BASE + timedelta(days=10), metadata={"event_records": events}
    ))
    assert result.summaries[0].values["event_count"] == 1


def test_event_reaction_uses_subsequent_price_observations():
    prices = [bar(f"p{i}", i, 100 + 5 * i) for i in range(0, 8)]
    events = [event("e1", 1, "acquisition", "Deal announced")]
    result = EventReactionEnricher(horizons=(1, 3)).enrich(EnrichmentContext(
        prices, instrument_id="TARGET", metadata={"event_records": events}
    ))
    values = result.summaries[0].values
    # First price after event is day 2 = 110. One period ahead = day 3 = 115.
    assert values["forward_return_1p"] == pytest.approx(115 / 110 - 1)
    assert values["forward_return_3p"] == pytest.approx(125 / 110 - 1)
    assert result.summaries[0].metadata["uses_future_outcome"] is True
    assert {"e1", "p2", "p3", "p5"}.issubset(set(result.summaries[0].lineage.source_record_ids))


def test_event_reaction_does_not_look_before_event():
    prices = [bar("p0", 0, 100), bar("p1", 1, 101), bar("p2", 2, 102)]
    events = [event("e1", 1)]
    result = EventReactionEnricher(horizons=(1,)).enrich(EnrichmentContext(prices, instrument_id="TARGET", metadata={"event_records": events}))
    assert result.summaries[0].values["forward_return_1p"] is None


def test_event_reaction_respects_as_of_for_events():
    prices = [bar("p0", 0, 100), bar("p1", 1, 101), bar("p2", 2, 102), bar("p3", 3, 104)]
    events = [event("e1", 1), event("e2", 5)]
    result = EventReactionEnricher(horizons=(1,)).enrich(EnrichmentContext(
        prices, instrument_id="TARGET", as_of=BASE + timedelta(days=3), metadata={"event_records": events}
    ))
    assert len(result.summaries) == 1
    assert result.summaries[0].values["event_time"] == BASE + timedelta(days=1)
