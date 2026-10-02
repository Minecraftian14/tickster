from datetime import datetime, timezone

from data_collection.domains.events import CompanyEvent
from data_collection.domains.models import Provenance
from data_foundation.query import records_visible_at


def test_query_filters_by_instrument_and_publication_time():
    p = Provenance(source="nse", source_type="exchange", published_at=datetime(2026, 5, 10, tzinfo=timezone.utc), retrieved_at=datetime(2026, 5, 12, tzinfo=timezone.utc))
    a = CompanyEvent(event_id="A", instrument_id="I1", event_type="announcement", provenance=p)
    b = CompanyEvent(event_id="B", instrument_id="I2", event_type="announcement", provenance=p)
    visible = records_visible_at([a, b], datetime(2026, 5, 11, tzinfo=timezone.utc), instrument_id="I1")
    assert [x.event_id for x in visible] == ["A"]
