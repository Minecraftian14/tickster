from __future__ import annotations

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSeries, DerivedSeriesPoint, DerivedSummary, EnrichmentIssue, EnrichmentResult
from .common import available_at_for_metric, extract_financial_points, group_statement_points, merge_financial_periods, period_gap_is_valid, records_for_metric


class FundamentalGrowthEnricher:
    """Derive period-over-period and year-over-year growth from statement history."""

    name = "fundamental.growth"
    version = "0.3.0"
    requires = frozenset({"fundamental.statement"})
    provides = frozenset({"fundamental.growth"})

    def __init__(self, *, metrics: tuple[str, ...] = ("revenue", "ebitda", "ebit", "net_income", "eps", "operating_cash_flow", "free_cash_flow")):
        self.metrics = metrics

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        groups = group_statement_points(merge_financial_periods(extract_financial_points(context)))
        for (statement_name, statement_type), points in groups.items():
            for metric in self.metrics:
                usable = [p for p in points if metric in p.values and p.values[metric] is not None]
                if len(usable) < 2:
                    continue
                periods = [p.period_end for p in usable]
                period_type = (usable[-1].period_type or "").lower()
                lags = (1, 4) if "quarter" in period_type else (1,)
                for lag in lags:
                    label = "qoq" if lag == 1 and "quarter" in period_type else "yoy"
                    if lag == 1 and "year" in period_type:
                        label = "yoy"
                    points_out: list[DerivedSeriesPoint] = []
                    source_records = []
                    for idx in range(lag, len(usable)):
                        prev = usable[idx - lag]
                        curr = usable[idx]
                        if curr.period_end is None or prev.values[metric] == 0:
                            continue
                        value = curr.values[metric] / prev.values[metric] - 1.0
                        source_items = list(records_for_metric(prev, metric)) + list(records_for_metric(curr, metric))
                        ids = [rid for item in source_items if (rid := EnrichmentContext.record_id(item))]
                        if not period_gap_is_valid(prev.period_end, curr.period_end, period_type=period_type, lag=lag):
                            result.issues.append(EnrichmentIssue(code="period_gap", severity="warning", message=f"Skipped {label} growth for {metric} because the comparison periods are not adjacent.", metric=f"{metric}_{label}_growth", record_ids=[rid for item in list(records_for_metric(prev, metric)) + list(records_for_metric(curr, metric)) if (rid := EnrichmentContext.record_id(item))]))
                            continue
                        points_out.append(DerivedSeriesPoint(timestamp=curr.timestamp, value=value, source_record_ids=ids, available_at=available_at_for_metric(curr, metric)))
                        source_records.extend(records_for_metric(prev, metric))
                        source_records.extend(records_for_metric(curr, metric))
                    if not points_out:
                        continue
                    algorithm = f"{self.name}.{label}"
                    lineage = context.lineage_for_records(source_records or [p.source_record for p in usable], algorithm=algorithm, algorithm_version=self.version, parameters={"metric": metric, "lag": lag, "statement_name": statement_name, "statement_type": statement_type})
                    result.series.append(DerivedSeries(
                        derived_id=stable_id(algorithm, context.instrument_id, metric, [(p.timestamp.isoformat(), p.value) for p in points_out]),
                        instrument_id=context.instrument_id,
                        metric=f"{metric}_{label}_growth",
                        unit="fraction",
                        points=points_out,
                        lineage=lineage,
                        metadata={"source_statement": statement_name, "statement_type": statement_type, "lag_periods": lag},
                    ))
        if not result.series:
            result.issues.append(EnrichmentIssue(code="no_growth_metrics", severity="warning", message="No supported fundamental metric had enough history to calculate growth."))
        return result
