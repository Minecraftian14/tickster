from __future__ import annotations

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSeries, DerivedSeriesPoint, EnrichmentIssue, EnrichmentResult
from .common import average, available_at_for_metric, extract_financial_points, group_statement_points, merge_financial_periods, ratio, records_for_metric


class FundamentalProfitabilityEnricher:
    """Calculate descriptive margins and return-on-capital ratios from statements."""

    name = "fundamental.profitability"
    version = "0.3.0"
    requires = frozenset({"fundamental.statement"})
    provides = frozenset({"fundamental.profitability"})

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        groups = group_statement_points(merge_financial_periods(extract_financial_points(context)))
        for (statement_name, statement_type), points in groups.items():
            if not any(p.values for p in points):
                continue
            metrics = {
                "gross_margin": lambda c, prev: ratio(c.values.get("gross_profit"), c.values.get("revenue")),
                "ebitda_margin": lambda c, prev: ratio(c.values.get("ebitda"), c.values.get("revenue")),
                "ebit_margin": lambda c, prev: ratio(c.values.get("ebit"), c.values.get("revenue")),
                "net_margin": lambda c, prev: ratio(c.values.get("net_income"), c.values.get("revenue")),
                "roe": lambda c, prev: ratio(c.values.get("net_income"), average(prev.values.get("total_equity") if prev else None, c.values.get("total_equity"))),
                "roa": lambda c, prev: ratio(c.values.get("net_income"), average(prev.values.get("total_assets") if prev else None, c.values.get("total_assets"))),
            }
            for metric, formula in metrics.items():
                out: list[DerivedSeriesPoint] = []
                source_records = []
                for idx, current in enumerate(points):
                    value = formula(current, points[idx - 1] if idx else None)
                    if value is None:
                        continue
                    prev = points[idx - 1] if idx else None
                    if metric in {"gross_margin", "ebitda_margin", "ebit_margin", "net_margin"}:
                        dependencies = {"gross_margin": ("gross_profit", "revenue"), "ebitda_margin": ("ebitda", "revenue"), "ebit_margin": ("ebit", "revenue"), "net_margin": ("net_income", "revenue")}[metric]
                    elif metric == "roe":
                        dependencies = ("net_income", "total_equity")
                    else:
                        dependencies = ("net_income", "total_assets")
                    source_items = []
                    for dependency in dependencies:
                        source_items.extend(records_for_metric(current, dependency))
                        if prev is not None and metric in {"roe", "roa"} and dependency in {"total_equity", "total_assets"}:
                            source_items.extend(records_for_metric(prev, dependency))
                    ids = [rid for item in source_items if (rid := EnrichmentContext.record_id(item))]
                    availability_values = [EnrichmentContext.temporal(item).available_at for item in source_items if EnrichmentContext.temporal(item).available_at is not None]
                    out.append(DerivedSeriesPoint(timestamp=current.timestamp, value=value, source_record_ids=ids, available_at=max(availability_values) if availability_values else None))
                    source_records.extend(source_items)
                if out:
                    algorithm = f"{self.name}.{metric}"
                    result.series.append(DerivedSeries(
                        derived_id=stable_id(algorithm, context.instrument_id, [(p.timestamp.isoformat(), p.value) for p in out]),
                        instrument_id=context.instrument_id,
                        metric=metric,
                        unit="fraction",
                        points=out,
                        lineage=context.lineage_for_records(source_records, algorithm=algorithm, algorithm_version=self.version, parameters={"denominator_basis": "average_prior_period" if metric in {"roe", "roa"} else "same_period", "statement_name": statement_name, "statement_type": statement_type}),
                        metadata={"source_statement": statement_name, "statement_type": statement_type},
                    ))
        if not result.series:
            result.issues.append(EnrichmentIssue(code="no_profitability_metrics", severity="warning", message="No supported profitability ratios could be calculated from the supplied statements."))
        return result
