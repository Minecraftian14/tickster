from datetime import datetime, timezone

from data_collection.domains.events import CompanyEvent
from data_collection.domains.models import Provenance
from data_foundation.temporal import temporal_envelope, is_visible_at


def test_published_time_controls_knowledge_visibility():
    observed = datetime(2026, 5, 20, tzinfo=timezone.utc)
    published = datetime(2026, 5, 15, tzinfo=timezone.utc)
    record = CompanyEvent(
        event_id="E1",
        instrument_id="I1",
        event_type="announcement",
        event_date=datetime(2026, 5, 14, tzinfo=timezone.utc),
        provenance=Provenance(source="nse", source_type="exchange", observed_at=observed, published_at=published, retrieved_at=datetime(2026, 5, 21, tzinfo=timezone.utc)),
    )
    env = temporal_envelope(record)
    assert env.availability_basis == "published"
    assert env.available_at == published
    assert is_visible_at(record, datetime(2026, 5, 15, 1, tzinfo=timezone.utc))
    assert not is_visible_at(record, datetime(2026, 5, 14, tzinfo=timezone.utc))
