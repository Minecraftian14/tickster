from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from data_foundation import CanonicalRecord
from data_enrichment import (
    CORE_FUNDAMENTAL_PROFILE,
    EnrichmentContext,
    EnrichmentPipeline,
    default_registry,
    FundamentalCashFlowEnricher,
    FundamentalGrowthEnricher,
    FundamentalProfitabilityEnricher,
    FundamentalSolvencyEnricher,
    FundamentalTTMEnricher,
)

BASE = datetime(2026, 3, 31, tzinfo=timezone.utc)


def fundamental(record_id: str, period_end: date, metrics: dict, *, period_type: str = "quarterly", name: str = "income_statement", statement_type: str = "consolidated", available_offset_days: int = 10):
    available = datetime.combine(period_end, datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=available_offset_days)
    return CanonicalRecord(
        record_id=record_id,
        domain="fundamentals",
        record_type="FundamentalSnapshot",
        payload={
            "instrument_id": "REL",
            "period_end": period_end,
            "period_type": period_type,
            "statement_name": name,
            "statement_type": statement_type,
            "metrics": metrics,
            "published_at": available,
        },
    )


def context(records):
    return EnrichmentContext(records, instrument_id="REL")


def test_growth_qoq_and_yoy_are_distinct():
    records = []
    for idx, (year, month, day, revenue) in enumerate([(2025, 3, 31, 100), (2025, 6, 30, 120), (2025, 9, 30, 130), (2025, 12, 31, 140), (2026, 3, 31, 150)]):
        records.append(fundamental(f"r{idx}", date(year, month, day), {"revenue": revenue, "eps": revenue / 10}))
    result = FundamentalGrowthEnricher().enrich(context(records))
    metrics = {series.metric: series for series in result.series}
    assert "revenue_qoq_growth" in metrics
    assert "revenue_yoy_growth" in metrics
    assert metrics["revenue_qoq_growth"].points[-1].value == pytest.approx(150 / 140 - 1)
    assert metrics["revenue_yoy_growth"].points[-1].value == pytest.approx(150 / 100 - 1)
    assert metrics["revenue_qoq_growth"].points[-1].available_at is not None


def test_ttm_requires_consecutive_quarters():
    dates = [date(2025, 3, 31), date(2025, 6, 30), date(2025, 9, 30), date(2025, 12, 31), date(2026, 3, 31)]
    records = [fundamental(f"r{i}", d, {"revenue": 100 + i * 10}) for i, d in enumerate(dates)]
    result = FundamentalTTMEnricher().enrich(context(records))
    series = next(s for s in result.series if s.metric == "revenue_ttm")
    assert len(series.points) == 2
    assert series.points[-1].value == pytest.approx(110 + 120 + 130 + 140)


def test_ttm_skips_gap():
    dates = [date(2025, 3, 31), date(2025, 6, 30), date(2025, 12, 31), date(2026, 3, 31)]
    records = [fundamental(f"r{i}", d, {"revenue": 100 + i * 10}) for i, d in enumerate(dates)]
    result = FundamentalTTMEnricher().enrich(context(records))
    assert not [s for s in result.series if s.metric == "revenue_ttm"]
    assert any(issue.code == "non_consecutive_quarters" for issue in result.issues)


def test_profitability_merges_income_and_balance_statements():
    records = [
        fundamental("i0", date(2025, 3, 31), {"revenue": 1000, "gross profit": 400, "ebitda": 300, "ebit": 200, "net income": 100}, period_type="yearly", name="income_statement"),
        fundamental("b0", date(2025, 3, 31), {"total equity": 500, "total assets": 1200}, period_type="yearly", name="balance_sheet"),
        fundamental("i1", date(2026, 3, 31), {"revenue": 1200, "gross profit": 480, "ebitda": 360, "ebit": 240, "net income": 144}, period_type="yearly", name="income_statement"),
        fundamental("b1", date(2026, 3, 31), {"total equity": 600, "total assets": 1400}, period_type="yearly", name="balance_sheet"),
    ]
    result = FundamentalProfitabilityEnricher().enrich(context(records))
    series = {s.metric: s for s in result.series}
    assert series["net_margin"].points[-1].value == pytest.approx(0.12)
    assert series["roe"].points[-1].value == pytest.approx(144 / 550)
    assert series["roa"].points[-1].value == pytest.approx(144 / 1300)
    assert set(series["roe"].points[-1].source_record_ids) == {"i1", "b1", "b0"}


def test_solvency_and_liquidity_merges_statement_families():
    records = [
        fundamental("bs", date(2026, 3, 31), {"total debt": 200, "cash": 50, "total equity": 500, "current assets": 300, "inventory": 50, "current liabilities": 150}, name="balance_sheet"),
        fundamental("is", date(2026, 3, 31), {"ebitda": 150, "ebit": 100, "interest expense": 20}, name="income_statement"),
    ]
    result = FundamentalSolvencyEnricher().enrich(context(records))
    values = {s.metric: s.points[-1].value for s in result.series}
    assert values["debt_to_equity"] == pytest.approx(0.4)
    assert values["net_debt_to_ebitda"] == pytest.approx(1.0)
    assert values["current_ratio"] == pytest.approx(2.0)
    assert values["quick_ratio"] == pytest.approx(5 / 3)
    assert values["interest_coverage"] == pytest.approx(5.0)


def test_cashflow_derives_free_cash_flow_and_quality_ratios():
    records = [fundamental("c0", date(2026, 3, 31), {
        "revenue": 1000, "operating cash flow": 220, "capital expenditure": -70, "net income": 180,
    }, name="cash_flow")]
    result = FundamentalCashFlowEnricher().enrich(context(records))
    values = {s.metric: s.points[-1].value for s in result.series}
    assert values["free_cash_flow"] == pytest.approx(150)
    assert values["operating_cashflow_margin"] == pytest.approx(0.22)
    assert values["free_cashflow_margin"] == pytest.approx(0.15)
    assert values["cashflow_to_net_income"] == pytest.approx(220 / 180)
    assert values["capex_to_revenue"] == pytest.approx(0.07)


def test_pipeline_can_plan_fundamental_pack():
    registry = default_registry()
    assert all(name in registry.names() for name in CORE_FUNDAMENTAL_PROFILE.enrichers)
    records = [fundamental("a", date(2025, 3, 31), {"revenue": 100, "net income": 10, "total equity": 50, "total assets": 100})]
    result = EnrichmentPipeline(registry).run(context(records), list(CORE_FUNDAMENTAL_PROFILE.enrichers), available={"fundamental.statement"})
    assert result.metadata["planned_enrichers"] == list(CORE_FUNDAMENTAL_PROFILE.enrichers)
    assert not [issue for issue in result.issues if issue.severity == "error"]


def test_ttm_lineage_contains_all_statement_records():
    dates = [date(2025, 6, 30), date(2025, 9, 30), date(2025, 12, 31), date(2026, 3, 31)]
    records = []
    for idx, d in enumerate(dates):
        records.append(fundamental(f"i{idx}", d, {"revenue": 100 + idx * 10}, name="income_statement"))
        records.append(fundamental(f"c{idx}", d, {"operating cash flow": 20 + idx}, name="cash_flow"))
    result = FundamentalTTMEnricher().enrich(context(records))
    series = next(s for s in result.series if s.metric == "revenue_ttm")
    assert set(series.points[-1].source_record_ids) == {"i0", "i1", "i2", "i3"}
    assert len(series.lineage.source_record_ids) >= 4
