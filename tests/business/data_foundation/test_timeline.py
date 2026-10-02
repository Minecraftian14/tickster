from datetime import datetime, timezone

from data_collection.domains.events import CompanyEvent
from data_collection.domains.models import Provenance
from data_foundation.timeline import build_company_timeline


def test_company_timeline_orders_events_and_keeps_evidence():
    p = Provenance(source="nse", source_type="exchange", retrieved_at=datetime.now(timezone.utc), raw_ref="raw-1")
    records = [
        CompanyEvent(event_id="E2", instrument_id="I1", event_type="results", event_date=datetime(2026, 6, 10, tzinfo=timezone.utc), subject="Results", provenance=p),
        CompanyEvent(event_id="E1", instrument_id="I1", event_type="board", event_date=datetime(2026, 5, 10, tzinfo=timezone.utc), subject="Board", provenance=p),
    ]
    timeline = build_company_timeline("I1", records)
    assert [entry.source_record_id for entry in timeline.entries] == ["E1", "E2"]
    assert timeline.entries[0].evidence_ids == ["raw-1"]
