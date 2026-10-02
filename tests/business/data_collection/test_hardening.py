from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd

from data_collection.collection.fundamentals import statement_snapshots_from_payload
from data_collection.collection.market import MarketCollector
from data_collection.collection.results import RawPayload, CollectionResult
from data_collection.domains.filings import DocumentAsset, Filing
from data_collection.domains.models import Instrument, MarketQuote, PriceBar, Provenance
from data_collection.processing.market import collapse_price_sources, deduplicate_price_bars
from data_collection.providers.nse_archives import NSEArchivesProvider
from data_collection.providers.upstox import UpstoxProvider
from data_collection.storage.raw import load_raw_payload, raw_payload_id, write_raw_payloads


NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)


def prov(source: str) -> Provenance:
    return Provenance(source=source, source_type="fixture", retrieved_at=NOW)


def instrument():
    return Instrument(
        instrument_id="INE002A01018", isin="INE002A01018", symbol="RELIANCE", exchange="NSE",
        instrument_key="NSE_EQ|INE002A01018", provenance=prov("test")
    )


def test_source_aware_price_dedup_preserves_independent_observations():
    ts = datetime(2026, 1, 2, tzinfo=timezone.utc)
    a = PriceBar(instrument_id="INE1", timestamp=ts, timeframe="1d", close=Decimal("100"), provenance=prov("nse"))
    b = a.model_copy(update={"close": Decimal("100.1"), "provenance": prov("yfinance")})
    assert len(deduplicate_price_bars([a, b])) == 2
    assert len(collapse_price_sources([a, b])) == 1


def test_upstox_full_quote_promotes_v3_fields():
    payload = {"data": {"NSE_EQ:RELIANCE": {
        "timestamp": "2026-10-02T15:22:31.099+05:30",
        "last_price": 100.5,
        "prev_close_price": 99.5,
        "net_change": 1.0,
        "average_price": 100.1,
        "volume": 12345,
        "total_buy_quantity": 500,
        "total_sell_quantity": 400,
        "upper_circuit_limit": 110,
        "lower_circuit_limit": 90,
        "last_trade_time": "1790934751099",
        "previous_oi": 0,
        "indicative_equilibrium_price": 100.2,
        "indicative_equilibrium_quantity": 1000,
        "indicative_imbalance_quantity_total": 100,
        "indicative_imbalance_quantity_market": 50,
        "reference_price": 99.5,
        "cas_eligible": True,
        "ohlc": {"open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 12345, "ts": 1790934700000},
        "depth": {"buy": [{"quantity": 10, "price": 100.4, "orders": 2}], "sell": [{"quantity": 12, "price": 100.6, "orders": 3}]},
    }}}
    records = UpstoxProvider.parse_full_quotes(payload, {"NSE_EQ:RELIANCE": "INE002A01018"}, retrieved_at=NOW)
    q = records[0]
    assert q.timestamp.isoformat() == "2026-10-02T09:52:31.099000+00:00"
    assert q.indicative_equilibrium_price == Decimal("100.2")
    assert q.cas_eligible is True
    assert q.bid_depth[0]["orders"] == 2
    assert q.number_of_orders == 5
    assert q.ohlc_timestamp is not None


def test_upstox_daily_history_chunks_long_ranges():
    class StubUpstox:
        def __init__(self): self.calls = []
        def historical_candles_v3(self, key, unit, interval, to_date, from_date):
            self.calls.append((to_date, from_date))
            return {"data": {"candles": [[to_date.isoformat() + "T00:00:00+05:30", 1, 2, 1, 2, 10]]}}
        def parse_candles(self, payload, instrument_id, *, timeframe, retrieved_at=None, issues=None):
            return UpstoxProvider.parse_candles(payload, instrument_id, timeframe=timeframe, retrieved_at=retrieved_at, issues=issues)
    stub = StubUpstox()
    result = MarketCollector(upstox=stub).daily_history(instrument=instrument(), start=date(2000, 1, 1), end=date(2026, 1, 1), sources=("upstox",))
    assert not result.errors
    assert len(stub.calls) == 3
    assert stub.calls[0][1] == date(2000, 1, 1)
    assert stub.calls[-1][0] == date(2026, 1, 1)


def test_raw_payloads_are_content_addressed_and_reloadable(tmp_path):
    item = RawPayload(source="nse", domain="market", retrieved_at=NOW, payload={"b": 2, "a": 1}, request={"date": "2026-10-01"})
    digest = raw_payload_id(item)
    paths = write_raw_payloads([item], tmp_path)
    assert paths and digest in paths[0].name
    loaded = load_raw_payload(paths[0])
    assert loaded["raw_id"] == digest
    assert loaded["payload"] == {"b": 2, "a": 1}


def test_filing_assets_are_linked_to_filing_id():
    class StubNSE:
        def corporate_announcements(self, **kwargs):
            return [{"symbol": "RELIANCE", "desc": "Press Release", "attchmntFile": "https://example.com/a.pdf", "an_dt": "02-Oct-2026 10:00:00"}]
    from data_collection.collection.filings import FilingCollector
    result = FilingCollector(nse=StubNSE()).corporate_announcements(symbol="RELIANCE", from_date=date(2026,10,2), to_date=date(2026,10,2), instrument=instrument())
    assert result.records[0].assets
    assert result.related_records
    asset = result.related_records[0]
    assert asset.asset_id == result.records[0].assets[0]
    assert asset.filing_id == result.records[0].filing_id


def test_fundamental_statement_history_is_period_aware():
    payload = {"data": {"type": "consolidated", "time_period": "yearly", "units_in": "crore", "income_statement": [{"category": "revenue", "history": [{"period": "Mar 2026", "value": 1234, "change": "+10%"}]}]}}
    rows = statement_snapshots_from_payload(payload, instrument_id="INE1", statement_name="income_statement", retrieved_at=NOW)
    assert len(rows) == 1
    assert rows[0].period_end == date(2026, 3, 31)
    assert rows[0].statement_name == "income_statement"
    assert rows[0].metrics["summary"]["revenue"]["value"] == 1234

def test_nse_universe_prefers_isin_identity():
    frame = pd.DataFrame([{"SYMBOL": "RELIANCE", "ISIN": "INE002A01018", "CLOSE_PRICE": 102}])
    rows = NSEArchivesProvider.normalize_equity_universe_daily(frame, trading_date=date(2026, 10, 1))
    assert rows[0].instrument_id == "INE002A01018"

def test_collection_result_can_persist_raw(tmp_path):
    result = CollectionResult(domain="market")
    result.raw_payloads.append(RawPayload(source="nse", domain="market", retrieved_at=NOW, payload={"x": 1}))
    paths = result.persist_raw(tmp_path)
    assert len(paths) == 1
    assert paths[0].exists()
