from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from data_foundation import CanonicalRecord
from data_enrichment import EnrichmentContext, InsiderActivityEnricher, LargeDealActivityEnricher, ShareholdingChangeEnricher

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def canon(rid, instrument, payload):
    payload = {"instrument_id": instrument, **payload}
    return CanonicalRecord(record_id=rid, domain="test", record_type="X", payload=payload)


def sh(rid, period_end, promoter, public, fii=None, dii=None):
    return canon(rid, "TARGET", {
        "period_end": period_end,
        "holders": {
            "promoter_and_promoter_group": promoter,
            "public": public,
            "fii": fii,
            "dii": dii,
        },
        "published_at": BASE + timedelta(days=period_end.day),
    })


def test_shareholding_changes_latest_period():
    result = ShareholdingChangeEnricher().enrich(EnrichmentContext([
        sh("s1", datetime(2025, 12, 31, tzinfo=timezone.utc), 50.0, 30.0, 10.0, 10.0),
        sh("s2", datetime(2026, 3, 31, tzinfo=timezone.utc), 51.5, 28.5, 11.0, 9.0),
    ], instrument_id="TARGET"))
    values = result.summaries[0].values
    assert values["promoter_current"] == pytest.approx(51.5)
    assert values["promoter_change"] == pytest.approx(1.5)
    assert values["public_change"] == pytest.approx(-1.5)
    obs = {x.metric: x.value for x in result.observations}
    assert obs["shareholding_change_fii"] == pytest.approx(1.0)
    assert obs["shareholding_change_dii"] == pytest.approx(-1.0)


def test_shareholding_uses_nearest_previous_available_field():
    records = [
        sh("s1", datetime(2025, 9, 30, tzinfo=timezone.utc), 50.0, 30.0),
        sh("s2", datetime(2025, 12, 31, tzinfo=timezone.utc), None, 31.0),
        sh("s3", datetime(2026, 3, 31, tzinfo=timezone.utc), 52.0, 29.0),
    ]
    result = ShareholdingChangeEnricher().enrich(EnrichmentContext(records, instrument_id="TARGET"))
    promoter = next(o for o in result.observations if o.metric == "shareholding_change_promoter")
    assert promoter.value == pytest.approx(2.0)
    assert promoter.lineage.source_record_ids == ["s3", "s1"]


def test_insider_activity_aggregates_buy_sell_and_people():
    def insider(rid, day, person, buy_qty=0, sell_qty=0, buy_value=0, sell_value=0):
        return canon(rid, "TARGET", {
            "intimation_date": BASE + timedelta(days=day),
            "person_name": person,
            "buy_quantity": buy_qty,
            "sell_quantity": sell_qty,
            "buy_value": buy_value,
            "sell_value": sell_value,
            "published_at": BASE + timedelta(days=day),
        })
    records = [
        insider("i1", 1, "Alice", buy_qty=100, buy_value=1000),
        insider("i2", 5, "Bob", sell_qty=40, sell_value=600),
        insider("i3", 80, "Alice", buy_qty=50, buy_value=400),
    ]
    result = InsiderActivityEnricher(windows_days=(30, 90)).enrich(EnrichmentContext(records, instrument_id="TARGET"))
    short = result.summaries[0].values
    assert short["transaction_count"] == 1  # the anchor-day transaction is included
    long = result.summaries[1].values
    assert long["transaction_count"] == 3
    assert long["buy_quantity"] == pytest.approx(150)
    assert long["sell_quantity"] == pytest.approx(40)
    assert long["net_value"] == pytest.approx(800)
    assert long["distinct_people"] == 2


def test_insider_point_in_time_excludes_future_disclosures():
    def rec(rid, day, person, value):
        return canon(rid, "TARGET", {
            "intimation_date": BASE + timedelta(days=day),
            "person_name": person,
            "buy_quantity": 10,
            "buy_value": value,
            "published_at": BASE + timedelta(days=day),
        })
    as_of = BASE + timedelta(days=10)
    result = InsiderActivityEnricher(windows_days=(365,)).enrich(EnrichmentContext(
        [rec("i1", 1, "Alice", 100), rec("i2", 20, "Bob", 200)], instrument_id="TARGET", as_of=as_of,
    ))
    assert result.summaries[0].values["transaction_count"] == 1


def test_large_deal_activity_aggregates_notional_and_sides():
    def deal(rid, day, side, qty, price, client, deal_type):
        return canon(rid, "TARGET", {
            "trade_date": BASE + timedelta(days=day),
            "side": side,
            "quantity": qty,
            "weighted_average_price": price,
            "client_name": client,
            "deal_type": deal_type,
            "published_at": BASE + timedelta(days=day),
        })
    result = LargeDealActivityEnricher(windows_days=(30,)).enrich(EnrichmentContext([
        deal("d1", 1, "BUY", 100, 10, "Fund A", "bulk_deals"),
        deal("d2", 5, "SELL", 50, 12, "Fund B", "block_deals"),
    ], instrument_id="TARGET"))
    values = result.summaries[0].values
    assert values["deal_count"] == 2
    assert values["gross_quantity"] == pytest.approx(150)
    assert values["buy_value"] == pytest.approx(1000)
    assert values["sell_value"] == pytest.approx(600)
    assert values["net_value"] == pytest.approx(400)
    assert values["distinct_clients"] == 2
    assert values["deal_type_counts"] == {"bulk_deals": 1, "block_deals": 1}
