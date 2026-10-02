from __future__ import annotations

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSeries, DerivedSeriesPoint, EnrichmentIssue, EnrichmentResult
from .common import available_at_for_metric, extract_financial_points, group_statement_points, merge_financial_periods, records_for_metric, ratio


class FundamentalCashFlowEnricher:
    """Derive cash-flow quality and reinvestment measures."""

    name = "fundamental.cashflow"
    version = "0.3.0"
    requires = frozenset({"fundamental.statement"})
    provides = frozenset({"fundamental.cashflow"})

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        groups = group_statement_points(merge_financial_periods(extract_financial_points(context)))
        for (statement_name, statement_type), points in groups.items():
            formulas = {
                "free_cash_flow": lambda p: p.values.get("free_cash_flow") if p.values.get("free_cash_flow") is not None else (p.values.get("operating_cash_flow") - abs(p.values.get("capital_expenditure"))) if p.values.get("operating_cash_flow") is not None and p.values.get("capital_expenditure") is not None else None,
                "operating_cashflow_margin": lambda p: ratio(p.values.get("operating_cash_flow"), p.values.get("revenue")),
                "free_cashflow_margin": lambda p: ratio((p.values.get("free_cash_flow") if p.values.get("free_cash_flow") is not None else (p.values.get("operating_cash_flow") - abs(p.values.get("capital_expenditure"))) if p.values.get("operating_cash_flow") is not None and p.values.get("capital_expenditure") is not None else None), p.values.get("revenue")),
                "cashflow_to_net_income": lambda p: ratio(p.values.get("operating_cash_flow"), p.values.get("net_income")),
                "capex_to_revenue": lambda p: ratio(abs(p.values.get("capital_expenditure")) if p.values.get("capital_expenditure") is not None else None, p.values.get("revenue")),
            }
            for metric, formula in formulas.items():
                out: list[DerivedSeriesPoint] = []
                source_records = []
                for point in points:
                    value = formula(point)
                    if value is None:
                        continue
                    dependencies = {
                        "free_cash_flow": {"free_cash_flow", "operating_cash_flow", "capital_expenditure"},
                        "operating_cashflow_margin": {"operating_cash_flow", "revenue"},
                        "free_cashflow_margin": {"free_cash_flow", "operating_cash_flow", "capital_expenditure", "revenue"},
                        "cashflow_to_net_income": {"operating_cash_flow", "net_income"},
                        "capex_to_revenue": {"capital_expenditure", "revenue"},
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
                    unit = "source-units" if metric == "free_cash_flow" else "fraction"
                    result.series.append(DerivedSeries(
                        derived_id=stable_id(algorithm, context.instrument_id, [(p.timestamp.isoformat(), p.value) for p in out]),
                        instrument_id=context.instrument_id,
                        metric=metric,
                        unit=unit,
                        points=out,
                        lineage=context.lineage_for_records(source_records, algorithm=algorithm, algorithm_version=self.version, parameters={"capex_convention": "absolute_cash_outflow", "statement_name": statement_name, "statement_type": statement_type}),
                        metadata={"source_statement": statement_name, "statement_type": statement_type},
                    ))
        if not result.series:
            result.issues.append(EnrichmentIssue(code="no_cashflow_metrics", severity="warning", message="No supported cash-flow measures could be calculated from the supplied statements."))
        return result
