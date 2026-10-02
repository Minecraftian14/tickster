from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd

from data_collection.collection.macro import MacroCollector, observations_from_rows
from data_collection.domains.models import MacroObservation
from data_collection.providers.mospi import MOSPIProvider
from data_collection.providers.rbi import RBIProvider
from data_collection.processing.macro import deduplicate_macro, group_macro_by_series


NOW = datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc)


def test_observations_from_rows_preserves_raw_and_parses_dates():
    rows = [{"date": "2026-07-01", "value": "5.2", "unit": "%", "state": "All India"}]
    out = observations_from_rows(rows, source="mospi", source_dataset="cpi", series_id="cpi_all_india", value_fields=("value",))
    assert len(out) == 1
    assert out[0].observation_date == date(2026, 7, 1)
    assert out[0].value == "5.2"
    assert out[0].metadata["raw"]["state"] == "All India"


def test_rbi_provider_reads_csv_bytes():
    provider = RBIProvider()
    frame = provider.read_table(b"Date,Value\n2026-01-01,6.5\n", format_hint="csv")
    assert list(frame.columns) == ["Date", "Value"]
    assert frame.iloc[0]["Value"] == 6.5


def test_mospi_provider_builds_cpi_request():
    provider = MOSPIProvider(token="abc", base_url="https://example.test")
    class Stub:
        def __call__(self, **params):
            assert params["Year"] == "2026"
            return {"data": [{"date": "2026-07-01", "value": "104.2"}]}
    provider.cpi_index = Stub()
    result = MacroCollector(mospi=provider).mospi_cpi(Year="2026")
    assert len(result.records) == 1
    assert result.records[0].series_id == "getCPIIndex"


def test_collector_rbi_table():
    class StubRBI:
        def read_table(self, source, format_hint="csv"):
            return pd.DataFrame([{"date": "2026-06-01", "value": "6.25"}])
    result = MacroCollector(rbi=StubRBI()).rbi_table("x", source_dataset="policy_rate", series_id="repo_rate")
    assert len(result.records) == 1
    assert result.records[0].series_id == "repo_rate"
    assert result.records[0].value == "6.25"


def test_deduplicate_and_group_macro():
    p = MacroObservation(
        series_id="x", observation_date=date(2026, 1, 1), value=Decimal("1"),
        provenance={"source": "rbi", "source_type": "test", "retrieved_at": NOW}
    )
    q = p.model_copy(update={"value": Decimal("2")})
    out = deduplicate_macro([p, q])
    assert len(out) == 1
    assert out[0].value == Decimal("2")
    assert list(group_macro_by_series(out)) == ["x"]
