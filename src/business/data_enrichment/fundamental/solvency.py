from __future__ import annotations

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSeries, DerivedSeriesPoint, EnrichmentIssue, EnrichmentResult
from .common import available_at_for_metric, extract_financial_points, group_statement_points, merge_financial_periods, records_for_metric, ratio


class FundamentalSolvencyEnricher:
    """Calculate liquidity and leverage measures from balance-sheet history."""

    name = "fundamental.solvency"
    version = "0.3.0"
    requires = frozenset({"fundamental.statement"})
    provides = frozenset({"fundamental.solvency"})

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        groups = group_statement_points(merge_financial_periods(extract_financial_points(context)))
        for (statement_name, statement_type), points in groups.items():
            formulas = {
                "debt_to_equity": lambda p: ratio(p.values.get("total_debt"), p.values.get("total_equity")),
                "net_debt_to_ebitda": lambda p: ratio((p.values.get("total_debt") - p.values.get("cash")) if p.values.get("total_debt") is not None and p.values.get("cash") is not None else None, p.values.get("ebitda")),
                "current_ratio": lambda p: ratio(p.values.get("current_assets"), p.values.get("current_liabilities")),
                "quick_ratio": lambda p: ratio((p.values.get("current_assets") - p.values.get("inventory")) if p.values.get("current_assets") is not None and p.values.get("inventory") is not None else None, p.values.get("current_liabilities")),
                "interest_coverage": lambda p: ratio(p.values.get("ebit"), abs(p.values.get("interest_expense"))) if p.values.get("interest_expense") is not None else None,
            }
            for metric, formula in formulas.items():
                out: list[DerivedSeriesPoint] = []
                source_records = []
                for point in points:
                    value = formula(point)
                    if value is None:
                        continue
                    dependencies = {
                        "debt_to_equity": {"total_debt", "total_equity"},
                        "net_debt_to_ebitda": {"total_debt", "cash", "ebitda"},
                        "current_ratio": {"current_assets", "current_liabilities"},
                        "quick_ratio": {"current_assets", "inventory", "current_liabilities"},
                        "interest_coverage": {"ebit", "interest_expense"},
                    }[metric]
                    source_items = []
                    for dependency in dependencies:
                        source_items.extend(records_for_metric(point, dependency))
                    ids = [rid for item in source_items if (rid := EnrichmentContext.record_id(item))]
                    availability_values = [EnrichmentContext.temporal(item).available_at for item in source_items if EnrichmentContext.temporal(item).available_at is not None]
                    out.append(DerivedSeriesPoint(timestamp=point.timestamp, value=value, source_record_ids=ids, available_at=max(availability_values) if availability_values else None))
                    source_records.extend(source_items)
                if out:
                    algorithm = f"{self.name}.{metric}"
                    result.series.append(DerivedSeries(
                        derived_id=stable_id(algorithm, context.instrument_id, [(p.timestamp.isoformat(), p.value) for p in out]),
                        instrument_id=context.instrument_id,
                        metric=metric,
                        unit="ratio",
                        points=out,
                        lineage=context.lineage_for_records(source_records, algorithm=algorithm, algorithm_version=self.version, parameters={"statement_name": statement_name, "statement_type": statement_type}),
                        metadata={"source_statement": statement_name, "statement_type": statement_type},
                    ))
        if not result.series:
            result.issues.append(EnrichmentIssue(code="no_solvency_metrics", severity="warning", message="No supported solvency/liquidity ratios could be calculated from the supplied statements."))
        return result
