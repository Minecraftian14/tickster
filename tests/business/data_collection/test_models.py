from datetime import datetime, timezone
from decimal import Decimal

from data_collection.domains.models import PriceBar, Provenance


def test_price_bar_preserves_provenance():
    bar = PriceBar(
        instrument_id="NSE_EQ|TEST",
        timestamp=datetime(2026, 10, 1, tzinfo=timezone.utc),
        timeframe="1d",
        open=Decimal("100.0"),
        high=Decimal("105.0"),
        low=Decimal("99.0"),
        close=Decimal("104.0"),
        volume=12345,
        provenance=Provenance(
            source="test",
            source_type="fixture",
            retrieved_at=datetime(2026, 10, 2, tzinfo=timezone.utc),
        ),
    )
    assert bar.close == Decimal("104.0")
    assert bar.provenance.source == "test"
