from datetime import datetime, timezone
from decimal import Decimal

from data_collection.providers.upstox import UpstoxProvider


def test_normalize_instrument_prefers_isin():
    item = {"segment": "NSE_EQ", "name": "RELIANCE INDUSTRIES LTD", "exchange": "NSE", "isin": "INE002A01018", "instrument_type": "EQ", "instrument_key": "NSE_EQ|INE002A01018", "exchange_token": "2885", "tick_size": 5, "trading_symbol": "RELIANCE", "short_name": "Reliance", "security_type": "NORMAL", "cas_eligible": True}
    inst = UpstoxProvider.normalize_instrument(item, retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert inst.instrument_id == "INE002A01018"
    assert inst.instrument_key == "NSE_EQ|INE002A01018"
    assert inst.tick_size == Decimal("5")
    assert inst.cas_eligible is True


def test_parse_candles():
    payload = {"status": "success", "data": {"candles": [["2026-01-01T00:00:00+05:30", 100, 110, 95, 105, 12345, 0]]}}
    records = UpstoxProvider.parse_candles(payload, "INE1", timeframe="1d")
    assert len(records) == 1
    assert records[0].close == Decimal("105")
    assert records[0].volume == 12345


def test_parse_ltp():
    payload = {"status": "success", "data": {"NSE_EQ|INE1": {"ltp": 105.25, "ltq": 10, "volume": 1234, "cp": 104.0}}}
    records = UpstoxProvider.parse_ltp(payload, {"NSE_EQ|INE1": "INE1"})
    assert len(records) == 1
    assert records[0].instrument_id == "INE1"
    assert records[0].last_price == Decimal("105.25")
    assert records[0].previous_close == Decimal("104.0")


def test_parse_full_quote():
    payload = {"status": "success", "data": {"NSE_EQ|INE1": {
        "last_price": 105.25, "prev_close_price": 104.0, "volume": 1234,
        "year_high": 150, "year_low": 80,
        "live_ohlc": {"open": 103, "high": 106, "low": 102, "close": 105.25, "volume": 1234, "ts": 1767225600000}
    }}}
    records = UpstoxProvider.parse_full_quotes(payload, {"NSE_EQ|INE1": "INE1"})
    assert records[0].last_price == Decimal("105.25")
    assert records[0].day_high == Decimal("106")
    assert records[0].year_low == Decimal("80")


def test_parse_compressed_instrument_file():
    import gzip, json
    payload = gzip.compress(json.dumps([{"segment": "NSE_EQ", "instrument_key": "NSE_EQ|INE1"}]).encode())
    rows = UpstoxProvider.parse_instrument_file(payload)
    assert rows == [{"segment": "NSE_EQ", "instrument_key": "NSE_EQ|INE1"}]
