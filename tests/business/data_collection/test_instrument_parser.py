from data_collection.collection.instruments import InstrumentCollector
from data_collection.providers.upstox import UpstoxProvider


def test_instrument_search_normalizes_nse_equity():
    provider = UpstoxProvider("test-token")
    monkey_payload = {
        "status": "success",
        "data": [{
            "name": "RELIANCE INDUSTRIES LTD",
            "exchange": "NSE",
            "segment": "NSE_EQ",
            "isin": "INE002A01018",
            "instrument_key": "NSE_EQ|INE002A01018",
            "exchange_token": "2885",
            "trading_symbol": "RELIANCE",
            "instrument_type": "EQ",
            "tick_size": 5.0,
            "lot_size": 1,
        }],
    }
    provider.search_instruments = lambda *args, **kwargs: monkey_payload  # type: ignore[method-assign]
    result = InstrumentCollector(upstox=provider).search_equities("RELIANCE")
    assert len(result.records) == 1
    item = result.records[0]
    assert item.isin == "INE002A01018"
    assert item.instrument_key == "NSE_EQ|INE002A01018"
    assert item.symbol == "RELIANCE"
    assert int(item.lot_size) == 1
