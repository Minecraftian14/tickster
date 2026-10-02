from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from data_foundation import CanonicalRecord
from data_enrichment import (
    BENCHMARK_COMPARATIVE_PROFILE,
    PEER_COMPARATIVE_PROFILE,
    BenchmarkComparisonEnricher,
    EnrichmentContext,
    EnrichmentPipeline,
    PeerReturnComparisonEnricher,
    default_registry,
)

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def bar(record_id: str, instrument_id: str, close: float, day: int):
    ts = BASE + timedelta(days=day)
    return CanonicalRecord(
        record_id=record_id,
        domain="market",
        record_type="PriceBar",
        payload={
            "instrument_id": instrument_id,
            "timestamp": ts,
            "close": close,
            "published_at": ts,
        },
    )


def ctx(records, *, metadata=None):
    return EnrichmentContext(records, instrument_id="TARGET", metadata=metadata or {})


def test_benchmark_comparison_calculates_excess_return_and_beta():
    target = [bar("t0", "TARGET", 100, 0), bar("t1", "TARGET", 106, 1), bar("t2", "TARGET", 101.76, 2), bar("t3", "TARGET", 112.9536, 3)]
    benchmark = [bar("b0", "NIFTY", 100, 0), bar("b1", "NIFTY", 105, 1), bar("b2", "NIFTY", 99.75, 2), bar("b3", "NIFTY", 109.725, 3)]
    result = BenchmarkComparisonEnricher(horizons=(1, 2)).enrich(ctx(target, metadata={"benchmark_records": benchmark, "benchmark_id": "NIFTY"}))
    assert result.series[0].metric == "excess_return_1p"
    assert result.series[0].points[0].value == pytest.approx(0.06 - 0.05)
    values = result.summaries[0].values
    assert values["aligned_observations"] == 3
    assert values["correlation"] is not None
    assert values["beta"] == pytest.approx(1.0, rel=1e-6)
    assert set(result.series[0].lineage.source_record_ids) == {"t0", "t1", "t2", "t3", "b0", "b1", "b2", "b3"}


def test_benchmark_reports_no_alignment_when_dates_do_not_overlap():
    target = [bar("t0", "TARGET", 100, 0), bar("t1", "TARGET", 110, 1)]
    benchmark = [bar("b0", "NIFTY", 100, 10), bar("b1", "NIFTY", 105, 11)]
    result = BenchmarkComparisonEnricher().enrich(ctx(target, metadata={"benchmark_records": benchmark, "benchmark_id": "NIFTY"}))
    assert any(issue.code == "no_aligned_benchmark_history" for issue in result.issues)


def test_peer_comparison_reports_distribution_and_percentile():
    target = [bar("t0", "TARGET", 100, 0), bar("t1", "TARGET", 130, 1)]
    peer_a = [bar("a0", "A", 100, 0), bar("a1", "A", 110, 1)]
    peer_b = [bar("b0", "B", 100, 0), bar("b1", "B", 115, 1)]
    peer_c = [bar("c0", "C", 100, 0), bar("c1", "C", 125, 1)]
    result = PeerReturnComparisonEnricher(horizons=(1,)).enrich(ctx(target, metadata={"peer_records": {"A": peer_a, "B": peer_b, "C": peer_c}}))
    values = result.summaries[0].values
    assert values["peer_count"] == 3
    assert values["peer_median_1p"] == pytest.approx(0.15)
    assert values["target_return_1p"] == pytest.approx(0.30)
    assert values["excess_vs_peer_median_1p"] == pytest.approx(0.15)
    assert values["target_percentile_1p"] == pytest.approx(1.0)
    assert values["peer_zscore_1p"] is not None
    assert set(result.summaries[0].lineage.source_record_ids) == {"t0", "t1", "a0", "a1", "b0", "b1", "c0", "c1"}


def test_peer_comparison_accepts_tuple_form_and_skips_insufficient_peers():
    target = [bar("t0", "TARGET", 100, 0), bar("t1", "TARGET", 120, 1)]
    good = [bar("p0", "P", 100, 0), bar("p1", "P", 105, 1)]
    short = [bar("s0", "S", 100, 0)]
    result = PeerReturnComparisonEnricher(horizons=(1,)).enrich(ctx(target, metadata={"peer_records": [("P", good), ("S", short)]}))
    assert result.summaries[0].values["peer_count"] == 1
    assert "P" in result.summaries[0].metadata["peer_ids"]


def test_comparative_profiles_and_registry_are_available():
    registry = default_registry()
    assert registry.get(BENCHMARK_COMPARATIVE_PROFILE.enrichers[0]).version == "0.4.0"
    assert registry.get(PEER_COMPARATIVE_PROFILE.enrichers[0]).version == "0.4.0"


def test_benchmark_and_peer_can_run_as_selected_pipeline_with_declared_capabilities():
    target = [bar(f"t{i}", "TARGET", 100 + i, i) for i in range(3)]
    benchmark = [bar(f"b{i}", "NIFTY", 100 + 0.5 * i, i) for i in range(3)]
    peers = {"A": [bar("a0", "A", 100, 0), bar("a1", "A", 101, 1), bar("a2", "A", 102, 2)]}
    registry = default_registry()
    pipeline = EnrichmentPipeline(registry)
    result = pipeline.run(
        ctx(target, metadata={"benchmark_records": benchmark, "benchmark_id": "NIFTY", "peer_records": peers}),
        [*BENCHMARK_COMPARATIVE_PROFILE.enrichers, *PEER_COMPARATIVE_PROFILE.enrichers],
        available={"price.close", "benchmark.close", "peer.close"},
    )
    assert not [issue for issue in result.issues if issue.severity == "error"]
    assert {summary.summary_type for summary in result.summaries} == {"benchmark_comparison", "peer_return_comparison"}
    from data_enrichment import __version__
    assert result.enricher_version == __version__
