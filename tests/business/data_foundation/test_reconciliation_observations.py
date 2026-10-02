from datetime import datetime, timezone

from data_collection.domains.models import PriceBar, Provenance
from data_foundation.reconciliation import observations_from_record


def test_observations_from_price_bar_extracts_scalars_and_provenance():
    record = PriceBar(
        instrument_id="I1", timeframe="1d", timestamp=datetime(2026, 5, 1, tzinfo=timezone.utc),
        close="100.0", volume=123, provenance=Provenance(source="nse", source_type="exchange", retrieved_at=datetime(2026, 5, 2, tzinfo=timezone.utc), raw_ref="raw-1"),
    )
    items = observations_from_record(record)
    assert {x.field for x in items} == {"close", "volume"}
    assert {x.raw_ref for x in items} == {"raw-1"}
