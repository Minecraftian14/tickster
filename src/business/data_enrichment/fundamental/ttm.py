from __future__ import annotations

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSeries, DerivedSeriesPoint, EnrichmentIssue, EnrichmentResult
from .common import available_at_for_metric, extract_financial_points, group_statement_points, merge_financial_periods, records_for_metric, quarter_index


class FundamentalTTMEnricher:
    """Create trailing-four-quarter flow metrics from quarterly statements."""

    name = "fundamental.ttm"
    version = "0.3.0"
    requires = frozenset({"fundamental.statement"})
    provides = frozenset({"fundamental.ttm"})

    def __init__(self, *, metrics: tuple[str, ...] = ("revenue", "ebitda", "ebit", "net_income", "operating_cash_flow", "free_cash_flow")):
        self.metrics = metrics

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        groups = group_statement_points(merge_financial_periods(extract_financial_points(context)))
        for (statement_name, statement_type), points in groups.items():
            quarterly = [p for p in points if "quarter" in (p.period_type or "").lower()]
            quarterly.sort(key=lambda p: p.period_end or __import__("datetime").date.min)
            if len(quarterly) < 4:
                continue
            for metric in self.metrics:
                out: list[DerivedSeriesPoint] = []
                source_records = []
                for idx in range(3, len(quarterly)):
                    window = quarterly[idx - 3:idx + 1]
                    if any(metric not in p.values for p in window):
                        continue
                    ends = [p.period_end for p in window if p.period_end]
                    if len(ends) != 4 or any(quarter_index(b) - quarter_index(a) != 1 for a, b in zip(ends, ends[1:])):
                        result.issues.append(EnrichmentIssue(code="non_consecutive_quarters", severity="warning", message=f"Skipped TTM {metric} because the four-quarter window is not consecutive.", metric=f"{metric}_ttm", record_ids=[rid for point in window for item in records_for_metric(point, metric) if (rid := EnrichmentContext.record_id(item))]))
                        continue
                    value = sum(p.values[metric] for p in window)
                    current = window[-1]
                    metric_items = [item for point in window for item in records_for_metric(point, metric)]
                    out.append(DerivedSeriesPoint(timestamp=current.timestamp, value=value, source_record_ids=[rid for item in metric_items if (rid := EnrichmentContext.record_id(item))], available_at=available_at_for_metric(current, metric)))
                    source_records.extend(metric_items)
                if out:
                    algorithm = f"{self.name}.{metric}"
                    result.series.append(DerivedSeries(
                        derived_id=stable_id(algorithm, context.instrument_id, [(p.timestamp.isoformat(), p.value) for p in out]),
                        instrument_id=context.instrument_id,
                        metric=f"{metric}_ttm",
                        unit="source-units",
                        points=out,
                        lineage=context.lineage_for_records(source_records, algorithm=algorithm, algorithm_version=self.version, parameters={"window_quarters": 4, "statement_name": statement_name, "statement_type": statement_type}),
                        metadata={"frequency": "quarterly", "window": 4},
                    ))
        if not result.series:
            result.issues.append(EnrichmentIssue(code="no_ttm_metrics", severity="warning", message="No consecutive quarterly history was available for TTM calculations."))
        return result
