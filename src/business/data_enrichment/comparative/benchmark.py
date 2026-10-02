from __future__ import annotations

from datetime import datetime, timezone
from math import sqrt
from typing import Any

from ..core.hashing import stable_id
from ..core.context import EnrichmentContext
from ..models import DerivedSeries, DerivedSeriesPoint, DerivedSummary, EnrichmentIssue, EnrichmentResult
from .common import align_daily_returns, beta, correlation, records_from_metadata, sample_std


class BenchmarkComparisonEnricher:
    """Compare an equity's realized returns and risk statistics with a benchmark."""

    name = "comparative.benchmark"
    version = "0.4.0"
    requires = frozenset({"price.close", "benchmark.close"})
    provides = frozenset({"comparative.benchmark_performance", "comparative.benchmark_risk"})

    def __init__(self, *, horizons: tuple[int, ...] = (21, 63, 126, 252), periods_per_year: int = 252) -> None:
        self.horizons = horizons
        self.periods_per_year = periods_per_year

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        benchmark_records = records_from_metadata(context, "benchmark_records")
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        aligned = align_daily_returns(context.records_for_instrument(), benchmark_records)
        if not aligned:
            result.issues.append(EnrichmentIssue(
                code="no_aligned_benchmark_history",
                severity="warning",
                message="No valid security/benchmark return observations could be aligned.",
                metric="benchmark_comparison",
            ))
            return result

        calculated_at = datetime.now(timezone.utc)
        all_record_ids = set()
        for point in aligned:
            all_record_ids.update(point.instrument_record_ids)
            all_record_ids.update(point.reference_record_ids)
        source_records = [*context.records_for_instrument(), *benchmark_records]
        lineage = context.lineage_for_records(
            source_records,
            algorithm=self.name,
            algorithm_version=self.version,
            parameters={"benchmark_id": context.metadata.get("benchmark_id"), "horizons": self.horizons},
            calculated_at=calculated_at,
        )

        excess_points = [
            DerivedSeriesPoint(
                timestamp=item.timestamp,
                value=item.excess_return,
                source_record_ids=list(item.instrument_record_ids + item.reference_record_ids),
            )
            for item in aligned
        ]
        result.series.append(DerivedSeries(
            derived_id=stable_id(self.name, context.instrument_id, "excess_return_1p", [(p.timestamp.isoformat(), p.value) for p in excess_points]),
            instrument_id=context.instrument_id,
            metric="excess_return_1p",
            unit="fraction",
            points=excess_points,
            lineage=lineage,
            metadata={"benchmark_id": context.metadata.get("benchmark_id")},
        ))

        values: dict[str, Any] = {
            "aligned_observations": len(aligned),
            "benchmark_id": context.metadata.get("benchmark_id"),
            "correlation": correlation([x.instrument_return for x in aligned], [x.reference_return for x in aligned]),
            "beta": beta([x.instrument_return for x in aligned], [x.reference_return for x in aligned]),
        }
        excess = [x.excess_return for x in aligned]
        te = sample_std(excess)
        values["tracking_error_annualized"] = te * sqrt(self.periods_per_year) if te is not None else None
        values["information_ratio"] = (sum(excess) / len(excess)) / te * sqrt(self.periods_per_year) if te not in (None, 0) else None
        for horizon in self.horizons:
            if len(aligned) < horizon:
                values[f"excess_return_{horizon}p"] = None
                values[f"instrument_return_{horizon}p"] = None
                values[f"benchmark_return_{horizon}p"] = None
                continue
            window = aligned[-horizon:]
            values[f"instrument_return_{horizon}p"] = _compound([x.instrument_return for x in window])
            values[f"benchmark_return_{horizon}p"] = _compound([x.reference_return for x in window])
            values[f"excess_return_{horizon}p"] = values[f"instrument_return_{horizon}p"] - values[f"benchmark_return_{horizon}p"]

        result.summaries.append(DerivedSummary(
            derived_id=stable_id(self.name, context.instrument_id, values),
            instrument_id=context.instrument_id,
            summary_type="benchmark_comparison",
            values=values,
            lineage=lineage,
            metadata={"periods_per_year": self.periods_per_year},
        ))
        return result


def _compound(returns: list[float]) -> float:
    value = 1.0
    for item in returns:
        value *= 1.0 + item
    return value - 1.0
