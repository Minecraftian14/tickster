from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd

from data_collection.collection.market import MarketCollector
from data_collection.domains.models import Instrument, Provenance, PriceBar
from data_collection.providers.nse_archives import NSEArchivesProvider


class FakeYahoo:
    def collect_history(self, symbol, *, instrument_id, period="1mo", interval="1d", start=None, end=None):
        return [PriceBar(instrument_id=instrument_id, timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc), timeframe=interval, close=Decimal("100"), provenance=Provenance(source="yfinance", source_type="aggregator", retrieved_at=datetime.now(timezone.utc)))]


def test_market_collector_can_use_provider_independently():
    collector = MarketCollector(yfinance=FakeYahoo())
    result = collector.daily_sample(symbol="RELIANCE", sources=("yfinance",))
    assert result.errors == []
    assert result.records[0].instrument_id == "RELIANCE"


def test_nse_normalization_handles_common_column_names():
    frame = pd.DataFrame([{"SYMBOL": "RELIANCE", "OPEN_PRICE": 99, "HIGH_PRICE": 105, "LOW_PRICE": 98, "CLOSE_PRICE": 102, "TTL_TRD_QNTY": 100000, "TURNOVER_LACS": 5000, "DELIV_QTY": 40000, "DELIV_PER": 40}])
    instrument = Instrument(instrument_id="INE002A01018", isin="INE002A01018", symbol="RELIANCE", exchange="NSE", provenance=Provenance(source="test", source_type="test", retrieved_at=datetime.now(timezone.utc)))
    records = NSEArchivesProvider.normalize_equity_daily(frame, instrument=instrument, symbol="RELIANCE", instrument_id=instrument.instrument_id, trading_date=date(2026, 1, 2))
    assert len(records) == 1
    assert records[0].close == Decimal("102")
    assert records[0].delivery_percent == Decimal("40")
