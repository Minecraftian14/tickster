from datetime import date, datetime, timezone
from decimal import Decimal
import pandas as pd

from data_collection.collection.corporate import CorporateActionCollector, CompanyEventCollector
from data_collection.domains.models import Instrument, Provenance
from data_collection.domains.events import CompanyEvent
from data_collection.providers.upstox import UpstoxProvider
from data_collection.processing.corporate import deduplicate_corporate_actions, deduplicate_company_events


NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)


def instrument():
    return Instrument(
        instrument_id="INE002A01018", isin="INE002A01018", symbol="RELIANCE", exchange="NSE",
        instrument_key="NSE_EQ|INE002A01018", provenance=Provenance(
            source="test", source_type="fixture", retrieved_at=NOW
        )
    )


def test_upstox_corporate_actions_parser():
    payload = {
        "status": "success",
        "data": [{
            "name": "Dividend", "expiry_date": "14 Aug 2025", "amount": 5.5, "ratio": None,
            "event_details": [
                {"name": "Announcement date", "value": "25 Apr 2025"},
                {"name": "Ex dividend date", "value": "14 Aug 2025"},
                {"name": "Record date", "value": "14 Aug 2025"},
            ],
        }],
    }
    records = UpstoxProvider.parse_corporate_actions(payload, instrument().instrument_id, retrieved_at=NOW)
    assert len(records) == 1
    assert records[0].action_type == "dividend"
    assert records[0].announcement_date == date(2025, 4, 25)
    assert records[0].ex_date == date(2025, 8, 14)
    assert records[0].record_date == date(2025, 8, 14)
    assert records[0].amount == Decimal("5.5")


def test_nse_corporate_action_normalization_and_filter():
    frame = pd.DataFrame([
        {"SYMBOL": "RELIANCE", "COMPANY NAME": "Reliance Industries Limited", "SERIES": "EQ", "PURPOSE": "Dividend - Rs 5", "EX-DATE": "14-Aug-2026", "RECORD DATE": "14-Aug-2026", "FACE VALUE": 10},
        {"SYMBOL": "TCS", "COMPANY NAME": "Tata Consultancy Services", "SERIES": "EQ", "PURPOSE": "Dividend - Rs 10", "EX-DATE": "15-Aug-2026", "RECORD DATE": "15-Aug-2026", "FACE VALUE": 1},
    ])
    class StubNSE:
        def corporate_actions(self, trading_date):
            return frame
    result = CorporateActionCollector(nse=StubNSE()).for_dates(date(2026, 8, 14), symbol="RELIANCE", instrument=instrument())
    assert not result.errors
    assert len(result.records) == 1
    assert result.records[0].instrument_id == instrument().instrument_id
    assert result.records[0].ex_date == date(2026, 8, 14)


def test_event_collection_normalizes_and_dedupes():
    frame = pd.DataFrame([{ "SYMBOL": "RELIANCE", "SUBJECT": "General Updates", "DESCRIPTION": "Project update", "COMPANY NAME": "Reliance Industries" }])
    class StubNSE:
        def announcements(self, trading_date): return frame
        def board_meetings(self, trading_date): return frame
    collector = CompanyEventCollector(nse=StubNSE())
    result = collector.announcements(date(2026, 9, 30), symbol="RELIANCE", instrument=instrument())
    assert len(result.records) == 1
    assert result.records[0].event_type == "announcement"
    assert result.records[0].subject == "General Updates"
    assert result.records[0].instrument_id == instrument().instrument_id
    assert len(deduplicate_company_events(result.records * 2)) == 1


def test_corporate_action_dedupe():
    action = UpstoxProvider.parse_corporate_actions({"data": [{"name": "Dividend", "amount": 1.0, "ratio": None, "event_details": []}]}, instrument().instrument_id, retrieved_at=NOW)[0]
    assert len(deduplicate_corporate_actions([action, action])) == 1
