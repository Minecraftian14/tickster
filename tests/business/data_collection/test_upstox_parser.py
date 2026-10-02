from datetime import datetime
from data_collection.providers.upstox import UpstoxProvider


def test_parse_upstox_candles():
    payload = {
        "data": {
            "candles": [
                ["2026-10-01T00:00:00+05:30", 100, 105, 99, 104, 12345, 0],
            ]
        }
    }
    records = UpstoxProvider.parse_candles(payload, "NSE_EQ|TEST", timeframe="1d")
    assert len(records) == 1
    assert float(records[0].close) == 104.0
    assert records[0].volume == 12345
