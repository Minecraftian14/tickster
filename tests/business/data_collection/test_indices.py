from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd

from data_collection.collection.indices import IndexContextCollector
from data_collection.domains.indices import IndexConstituent, IndexSnapshot
from data_collection.domains.models import Provenance
from data_collection.providers.nse_indices import NSEIndexProvider


NOW = datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc)


ALL_INDICES = {
    "data": [
        {
            "index": "NIFTY 50",
            "indexSymbol": "NIFTY 50",
            "last": "25123.45",
            "variation": "123.45",
            "percentChange": "0.49",
            "previousClose": "25000.00",
            "open": "25010.00",
            "high": "25150.00",
            "low": "24980.00",
            "yearHigh": "26000.00",
            "yearLow": "21000.00",
            "perChange365d": "12.50",
            "perChange30d": "2.25",
        }
    ]
}


INDEX_CONSTITUENTS = {
    "metadata": {"indexName": "NIFTY 50", "indexSymbol": "NIFTY 50"},
    "data": [
        {
            "symbol": "RELIANCE",
            "identifier": "Reliance Industries Limited",
            "lastPrice": "1500.10",
            "change": "5.10",
            "pChange": "0.34",
            "weight": "9.12",
            "totalTradedVolume": "1000000",
            "totalTradedValue": "1500100000",
        },
        {
            "symbol": "TCS",
            "identifier": "Tata Consultancy Services",
            "lastPrice": "3300.20",
            "change": "-10.10",
            "pChange": "-0.31",
            "weightage": "6.21",
            "totalTradedVolume": "500000",
            "totalTradedValue": "1650100000",
        },
    ],
}


QUOTE = {
    "info": {"symbol": "RELIANCE"},
    "metadata": {
        "lastUpdateTime": "02-Oct-2026 15:30:00",
        "industry": "Oil Exploration & Production",
        "sector": "Energy",
    },
    "industryInfo": {
        "macro": "Commodities",
        "sector": "Energy",
        "industry": "Oil Exploration & Production",
        "basicIndustry": "Oil Exploration & Production",
    },
}


def test_parse_all_indices():
    rows = NSEIndexProvider.parse_index_snapshots(ALL_INDICES, retrieved_at=NOW)
    assert len(rows) == 1
    assert rows[0]["index_symbol"] == "NIFTY 50"
    assert rows[0]["value"] == Decimal("25123.45")
    assert rows[0]["change_percent"] == Decimal("0.49")


def test_parse_constituents():
    rows = NSEIndexProvider.parse_constituents(
        INDEX_CONSTITUENTS,
        instrument_ids_by_symbol={"RELIANCE": "INE002A01018"},
        retrieved_at=NOW,
    )
    assert len(rows) == 2
    assert rows[0]["symbol"] == "RELIANCE"
    assert rows[0]["instrument_id"] == "INE002A01018"
    assert rows[0]["weight_percent"] == Decimal("9.12")
    assert rows[1]["weight_percent"] == Decimal("6.21")


def test_parse_sector_classification():
    row = NSEIndexProvider.parse_sector_classification(
        QUOTE, symbol="RELIANCE", instrument_id="INE002A01018", retrieved_at=NOW
    )
    assert row["sector_macro"] == "Commodities"
    assert row["sector"] == "Energy"
    assert row["industry"] == "Oil Exploration & Production"
    assert row["basic_industry"] == "Oil Exploration & Production"
    assert row["classification_as_of"].tzinfo is not None


def test_collector_current_indices():
    class Stub:
        def all_indices(self): return ALL_INDICES
        def parse_index_snapshots(self, payload, retrieved_at=None): return NSEIndexProvider.parse_index_snapshots(payload, retrieved_at=retrieved_at)
        def health(self): return {"ok": True}

    result = IndexContextCollector(nse=Stub()).current_indices()
    assert len(result.records) == 1
    assert result.records[0].index_symbol == "NIFTY 50"


def test_collector_constituents():
    class Stub:
        def index_constituents(self, index): return INDEX_CONSTITUENTS
        def parse_constituents(self, payload, instrument_ids_by_symbol=None, retrieved_at=None): return NSEIndexProvider.parse_constituents(payload, instrument_ids_by_symbol=instrument_ids_by_symbol, retrieved_at=retrieved_at)

    class I:
        symbol = "RELIANCE"
        instrument_id = "INE002A01018"

    result = IndexContextCollector(nse=Stub()).constituents("NIFTY 50", instruments=[I()])
    assert len(result.records) == 2
    assert result.records[0].instrument_id == "INE002A01018"


def test_historical_index_uses_archive_data():
    class StubArchives:
        def index_daily_close(self, trading_date):
            return pd.DataFrame([
                {"INDEX_NAME": "NIFTY 50", "HistoricalDate": "02-Oct-2026", "OPEN": "25000", "HIGH": "25150", "LOW": "24950", "CLOSE": "25123.45"}
            ])

    class StubNSE: pass
    result = IndexContextCollector(archives=StubArchives()).historical_index("NIFTY 50", date(2026, 10, 2))
    assert len(result.records) == 1
    assert result.records[0].close == Decimal("25123.45")


def test_index_valuation_uses_archive_data():
    class StubArchives:
        def index_valuation(self, trading_date):
            return pd.DataFrame([
                {"INDEX_NAME": "NIFTY 50", "P/E": "21.4", "P/B": "3.8", "Div Yield": "1.2"}
            ])

    result = IndexContextCollector(archives=StubArchives()).valuation("NIFTY 50", date(2026, 10, 2))
    assert len(result.records) == 1
    assert result.records[0].pe == Decimal("21.4")
    assert result.records[0].dividend_yield == Decimal("1.2")
