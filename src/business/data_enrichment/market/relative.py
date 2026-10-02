from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSeries, DerivedSeriesPoint, DerivedSummary, EnrichmentIssue, EnrichmentResult
from .common import prepare_price_records, timestamp, close


class RelativePerformanceEnricher:
    name = "market.relative_performance"
    version = "0.2.0"
    requires = frozenset({"price.close", "benchmark.close"})
    provides = frozenset({"market.excess_return", "market.relative_performance"})

    def _benchmark_records(self, context: EnrichmentContext) -> list[Any]:
        value = context.metadata.get("benchmark_records")
        return list(value) if value is not None else []

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        security = prepare_price_records(context)
        benchmarks = [(timestamp(r), r, close(r)) for r in self._benchmark_records(context)]
        benchmarks = [x for x in benchmarks if x[0] is not None and x[2] is not None]
        benchmarks.sort(key=lambda x: x[0])
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if len(security) < 2 or len(benchmarks) < 2:
            result.issues.append(EnrichmentIssue(code="insufficient_benchmark_data", severity="warning", message="Security and benchmark each require at least two close observations."))
            return result
        benchmark_by_day = {ts.date(): price for ts, _, price in benchmarks}
        points: list[DerivedSeriesPoint] = []
        for prev, cur in zip(security, security[1:]):
            prev_b = benchmark_by_day.get(prev[0].date())
            cur_b = benchmark_by_day.get(cur[0].date())
            if prev_b is None or cur_b is None or prev_b <= 0 or cur_b <= 0 or prev[2] <= 0:
                continue
            stock_ret = cur[2] / prev[2] - 1.0
            benchmark_ret = cur_b / prev_b - 1.0
            points.append(DerivedSeriesPoint(timestamp=cur[0], value=stock_ret - benchmark_ret, source_record_ids=[x for x in (context.record_id(prev[1]), context.record_id(cur[1])) if x]))
        if not points:
            result.issues.append(EnrichmentIssue(code="no_aligned_observations", severity="warning", message="No security/benchmark dates could be aligned."))
            return result
        security_records = [x[1] for x in security]
        benchmark_records = [x[1] for x in benchmarks]
        lineage_records = security_records + benchmark_records
        result.series.append(DerivedSeries(
            derived_id=stable_id(self.name, context.instrument_id, [(p.timestamp.isoformat(), p.value) for p in points]),
            instrument_id=context.instrument_id,
            metric="excess_return_1p",
            unit="fraction",
            points=points,
            lineage=context.lineage_for_records(lineage_records, algorithm=self.name, algorithm_version=self.version, parameters={"benchmark": context.metadata.get("benchmark_id")}),
            metadata={"benchmark_id": context.metadata.get("benchmark_id")},
        ))
        result.summaries.append(DerivedSummary(
            derived_id=stable_id(self.name, context.instrument_id, len(points), points[-1].value),
            instrument_id=context.instrument_id,
            summary_type="relative_performance",
            values={
                "aligned_observations": len(points),
                "mean_excess_return": sum(p.value for p in points) / len(points),
                "cumulative_excess_return_approx": sum(p.value for p in points),
                "latest_excess_return": points[-1].value,
            },
            lineage=context.lineage_for_records(lineage_records, algorithm=self.name, algorithm_version=self.version, parameters={"benchmark": context.metadata.get("benchmark_id")}),
            metadata={"benchmark_id": context.metadata.get("benchmark_id")},
        ))
        return result
