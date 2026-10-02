from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from data_foundation import CanonicalRecord
from data_enrichment import (
    CORE_MARKET_PROFILE,
    EnrichmentContext,
    LiquidityEnricher,
    MovingAverageEnricher,
    MultiResolutionSummaryEnricher,
    RelativePerformanceEnricher,
    ReturnHorizonSummaryEnricher,
    ReturnSeriesEnricher,
    RollingVolatilityEnricher,
    VolatilitySummaryEnricher,
    DrawdownEnricher,
    default_registry,
)

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def bar(record_id: str, instrument_id: str, close: float, day: int, **extra):
    ts = BASE + timedelta(days=day)
    return CanonicalRecord(
        record_id=record_id,
        domain="market",
        record_type="PriceBar",
        payload={
            "instrument_id": instrument_id,
            "timestamp": ts,
            "close": close,
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "volume": 1000 + day * 100,
            "traded_value": (1000 + day * 100) * close,
            "delivery_percent": 35 + day,
            "published_at": ts,
            **extra,
        },
    )


def ctx(records, *, metadata=None):
    return EnrichmentContext(records, instrument_id="REL", metadata=metadata or {})


def test_returns_include_simple_log_and_cumulative():
    result = ReturnSeriesEnricher().enrich(ctx([bar("a", "REL", 100, 0), bar("b", "REL", 110, 1), bar("c", "REL", 121, 2)]))
    assert {s.metric for s in result.series} == {"return_1p", "log_return_1p", "cumulative_return"}
    simple = next(s for s in result.series if s.metric == "return_1p")
    cumulative = next(s for s in result.series if s.metric == "cumulative_return")
    assert [round(p.value, 6) for p in simple.points] == [0.1, 0.1]
    assert cumulative.points[-1].value == pytest.approx(0.21)


def test_return_horizons_are_available_when_history_exists():
    result = ReturnHorizonSummaryEnricher().enrich(ctx([bar(f"r{i}", "REL", 100 + i, i) for i in range(520)]))
    values = result.summaries[0].values
    assert values["return_252p"] is not None
    assert values["annualized_return"] is not None


def test_rolling_volatility_is_annualized():
    records = [bar(f"r{i}", "REL", 100 * (1.001 ** i), i) for i in range(70)]
    result = RollingVolatilityEnricher(windows=(20,)).enrich(ctx(records))
    series = result.series[0]
    assert series.metric == "realized_volatility_20p"
    assert len(series.points) == 50
    assert series.points[-1].value > 0


def test_volatility_summary_is_descriptive():
    result = VolatilitySummaryEnricher().enrich(ctx([bar(f"r{i}", "REL", 100 + i * 0.5, i) for i in range(20)]))
    values = result.summaries[0].values
    assert values["return_observations"] == 19
    assert values["return_p95"] >= values["return_p05"]


def test_drawdown_finds_peak_to_trough():
    result = DrawdownEnricher().enrich(ctx([bar("a", "REL", 100, 0), bar("b", "REL", 120, 1), bar("c", "REL", 90, 2), bar("d", "REL", 110, 3)]))
    values = result.summaries[0].values
    assert values["maximum_drawdown"] == pytest.approx(-0.25)
    assert result.series[0].points[2].value == pytest.approx(-0.25)


def test_moving_average_and_distance():
    result = MovingAverageEnricher(windows=(3,)).enrich(ctx([bar("a", "REL", 100, 0), bar("b", "REL", 110, 1), bar("c", "REL", 120, 2), bar("d", "REL", 130, 3)]))
    series = result.series[0]
    assert series.metric == "sma_3"
    assert series.points[-1].value == pytest.approx(120)
    assert result.summaries[0].values["distance_from_sma_3"] == pytest.approx(130 / 120 - 1)


def test_liquidity_reports_coverage():
    result = LiquidityEnricher(windows=(3,)).enrich(ctx([bar("a", "REL", 100, 0), bar("b", "REL", 110, 1), bar("c", "REL", 120, 2)]))
    values = result.summaries[0].values
    assert values["avg_volume"] == pytest.approx(1100)
    assert values["volume_coverage"] == 1
    assert values["delivery_coverage"] == 1


def test_relative_performance_uses_benchmark_from_metadata():
    stock = [bar("s0", "REL", 100, 0), bar("s1", "REL", 110, 1), bar("s2", "REL", 121, 2)]
    bench = [bar("b0", "NIFTY", 100, 0), bar("b1", "NIFTY", 105, 1), bar("b2", "NIFTY", 110, 2)]
    result = RelativePerformanceEnricher().enrich(ctx(stock, metadata={"benchmark_records": bench, "benchmark_id": "NIFTY"}))
    assert result.series[0].metric == "excess_return_1p"
    assert result.series[0].points[0].value == pytest.approx(0.10 - 0.05)
    lineage_ids = set(result.series[0].lineage.source_record_ids)
    assert {"s0", "s1", "s2", "b0", "b1", "b2"}.issubset(lineage_ids)


def test_multi_resolution_creates_week_and_month_series():
    records = [bar(f"r{i}", "REL", 100 + i, i) for i in range(40)]
    result = MultiResolutionSummaryEnricher().enrich(ctx(records))
    assert {s.metric for s in result.series} == {"week_return", "month_return"}
    assert all(s.points for s in result.series)


def test_core_profile_registry_contains_v02_pack():
    registry = default_registry()
    for name in CORE_MARKET_PROFILE.enrichers:
        assert registry.get(name).version == "0.2.0"


def test_core_pipeline_runs_without_manual_ordering():
    records = [bar(f"r{i}", "REL", 100 + i, i) for i in range(260)]
    registry = default_registry()
    from data_enrichment import EnrichmentPipeline
    pipeline = EnrichmentPipeline(registry)
    result = pipeline.run(ctx(records), list(CORE_MARKET_PROFILE.enrichers), available={"price.close"})
    assert not [issue for issue in result.issues if issue.severity == "error"]
    assert len(result.series) >= 8
    assert len(result.summaries) >= 8
    assert result.metadata["planned_enrichers"] == list(CORE_MARKET_PROFILE.enrichers)
