from datetime import date, datetime, timezone
from decimal import Decimal

from data_collection.collection.ownership import OwnershipCollector, MarketEventsCollector, parse_insider_transactions, parse_large_deals, parse_shareholding
from data_collection.domains.models import Instrument, Provenance
from data_collection.domains.ownership import InsiderTransaction

NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)


def instrument():
    return Instrument(
        instrument_id="INE002A01018", isin="INE002A01018", symbol="RELIANCE", exchange="NSE",
        instrument_key="NSE_EQ|INE002A01018", provenance=Provenance(source="test", source_type="fixture", retrieved_at=NOW)
    )


def test_shareholding_parser_keeps_quarter_and_raw_fields():
    payload = {"data": [
        {"symbol": "RELIANCE", "date": "30-JUN-2026", "pr_and_prgrp": 49.12, "public_val": 50.88, "employeeTrusts": 0.0, "recordId": "123"}
    ]}
    records = parse_shareholding(payload, instrument=instrument(), symbol="RELIANCE", retrieved_at=NOW)
    assert len(records) == 1
    assert records[0].period_end == date(2026, 6, 30)
    assert records[0].holders["promoter_and_promoter_group"] == Decimal("49.12")
    assert records[0].holders["raw"]["recordId"] == "123"


def test_insider_parser_normalizes_core_pit_fields():
    payload = {"data": [{
        "symbol": "RELIANCE", "company": "Reliance Industries Limited", "anex": "Regulation 7 (2)",
        "acqName": "Example Promoter", "personCategory": "Promoter", "befAcqSharesNo": "1000",
        "befAcqSharesPer": "50.0", "secAcq": "100", "secVal": "100000", "tdpTransactionType": "Market Purchase",
        "afterAcqSharesNo": "1100", "afterAcqSharesPer": "55.0", "acqfromDt": "01-Sep-2026",
        "acqtoDt": "01-Sep-2026", "intimDt": "02-Sep-2026 16:10:00", "acqMode": "Market Purchase", "xbrl": "https://example/x.xml",
    }]}
    records = parse_insider_transactions(payload, instrument=instrument(), symbol="RELIANCE", retrieved_at=NOW)
    assert len(records) == 1
    assert records[0].person_name == "Example Promoter"
    assert records[0].securities_acquired == Decimal("100")
    assert records[0].acquisition_to == date(2026, 9, 1)


def test_large_deal_parser_supports_bulk_shape():
    payload = {"as_on_date": "02-10-2026", "BULK_DEALS_DATA": [{
        "date": "02-Oct-2026", "symbol": "RELIANCE", "name": "Reliance Industries Limited",
        "clientName": "Example Fund", "buySell": "BUY", "qty": 100000, "watp": 1420.5,
    }]}
    records = parse_large_deals(payload, mode="bulk_deals", symbol="RELIANCE", retrieved_at=NOW)
    assert len(records) == 1
    assert records[0].quantity == Decimal("100000")
    assert records[0].weighted_average_price == Decimal("1420.5")


def test_collectors_preserve_raw_payload_and_provider_errors():
    class Stub:
        def shareholding(self, symbol):
            return {"data": [{"symbol": symbol, "date": "30-JUN-2026", "pr_and_prgrp": 49, "public_val": 51}]}
        def insider_trading(self, start, end, symbol=None):
            return {"data": []}
        def large_deals(self, mode):
            return {"BULK_DEALS_DATA": []}
    provider = Stub()
    own = OwnershipCollector(nse=provider)
    result = own.shareholding("RELIANCE", instrument=instrument())
    assert not result.errors
    assert len(result.raw_payloads) == 1
    assert result.records[0].instrument_id == "INE002A01018"

    deals = MarketEventsCollector(nse=provider).large_deals("bulk_deals", symbol="RELIANCE")
    assert not deals.errors
