from datetime import datetime, timezone
from decimal import Decimal

from data_collection.domains.models import Instrument, PriceBar, Provenance
from data_collection.processing.instruments import canonical_instrument_id, deduplicate_instruments
from data_collection.processing.market import collapse_price_sources, deduplicate_price_bars, reconcile_prices, validate_price_bars


def prov(source: str) -> Provenance:
    return Provenance(source=source, source_type="test", retrieved_at=datetime.now(timezone.utc))


def test_isin_is_canonical_identity():
    assert canonical_instrument_id(isin="ine002a01018", exchange="NSE", symbol="RELIANCE") == "INE002A01018"


def test_symbol_fallback_is_exchange_qualified():
    assert canonical_instrument_id(isin=None, exchange="NSE", symbol="ABC") == "NSE:ABC"


def test_instruments_deduplicate():
    a = Instrument(instrument_id="INE001", symbol="ABC", exchange="NSE", isin="INE001", provenance=prov("a"))
    b = a.model_copy(update={"name": "Updated", "provenance": prov("b")})
    out = deduplicate_instruments([a, b])
    assert len(out) == 1
    assert out[0].name == "Updated"


def test_price_bars_deduplicate_and_sort():
    ts1 = datetime(2026, 1, 2, tzinfo=timezone.utc)
    ts2 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    a = PriceBar(instrument_id="INE1", timestamp=ts1, timeframe="1d", close=Decimal("101"), provenance=prov("a"))
    b = PriceBar(instrument_id="INE1", timestamp=ts1, timeframe="1d", close=Decimal("102"), provenance=prov("b"))
    c = PriceBar(instrument_id="INE1", timestamp=ts2, timeframe="1d", close=Decimal("99"), provenance=prov("a"))
    out = deduplicate_price_bars([a, b, c])
    assert len(out) == 3
    assert [x.timestamp for x in out] == [ts2, ts1, ts1]
    assert [x.provenance.source for x in out[-2:]] == ["a", "b"]
    collapsed = collapse_price_sources([a, b, c])
    assert [x.timestamp for x in collapsed] == [ts2, ts1]
    assert collapsed[-1].close == Decimal("102")


def test_validation_and_reconciliation():
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    a = PriceBar(instrument_id="INE1", timestamp=ts, timeframe="1d", low=Decimal("10"), high=Decimal("8"), close=Decimal("9"), provenance=prov("a"))
    b = a.model_copy(update={"high": Decimal("10"), "close": Decimal("9.5"), "provenance": prov("b")})
    assert any("high < low" in x for x in validate_price_bars([a]))
    assert reconcile_prices([a, b], tolerance=Decimal("0.01"))
