from __future__ import annotations

from datetime import datetime, timezone
import math

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedObservation, DerivedSeries, DerivedSeriesPoint, DerivedSummary, EnrichmentIssue, EnrichmentResult
from .common import annualized_volatility, prepare_price_records


class RollingVolatilityEnricher:
    name = "market.rolling_volatility"
    version = "0.2.0"
    requires = frozenset({"price.close"})
    provides = frozenset({"market.realized_volatility"})

    def __init__(self, windows: tuple[int, ...] = (20, 60, 252), *, periods_per_year: int = 252) -> None:
        self.windows = tuple(sorted(set(windows)))
        self.periods_per_year = periods_per_year

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        prepared = prepare_price_records(context)
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if len(prepared) < 2:
            result.issues.append(EnrichmentIssue(code="insufficient_observations", severity="warning", message="At least two closes are required."))
            return result
        returns = []
        return_records = []
        for prev, cur in zip(prepared, prepared[1:]):
            if prev[2] <= 0 or cur[2] <= 0:
                continue
            returns.append(cur[2] / prev[2] - 1.0)
            return_records.append(cur[1])
        for window in self.windows:
            points: list[DerivedSeriesPoint] = []
            for idx, ret in enumerate(returns):
                if idx + 1 < window:
                    continue
                window_returns = returns[idx + 1 - window:idx + 1]
                vol = annualized_volatility(window_returns, self.periods_per_year)
                if vol is not None:
                    points.append(DerivedSeriesPoint(timestamp=prepared[idx + 1][0], value=vol, source_record_ids=[x for x in (context.record_id(return_records[idx]),) if x]))
            result.series.append(DerivedSeries(
                derived_id=stable_id(self.name, context.instrument_id, window, [(p.timestamp.isoformat(), p.value) for p in points]),
                instrument_id=context.instrument_id,
                metric=f"realized_volatility_{window}p",
                unit="annualized-fraction",
                points=points,
                lineage=context.lineage_for_records([x[1] for x in prepared], algorithm=self.name, algorithm_version=self.version, parameters={"window": window, "periods_per_year": self.periods_per_year}, calculated_at=datetime.now(timezone.utc)),
                metadata={"window": window, "periods_per_year": self.periods_per_year},
            ))
        return result


class VolatilitySummaryEnricher:
    name = "market.volatility_summary"
    version = "0.2.0"
    requires = frozenset({"price.close"})
    provides = frozenset({"market.volatility_summary"})

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        prepared = prepare_price_records(context)
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if len(prepared) < 2:
            result.issues.append(EnrichmentIssue(code="insufficient_observations", severity="warning", message="At least two closes are required."))
            return result
        returns = [cur[2] / prev[2] - 1.0 for prev, cur in zip(prepared, prepared[1:]) if prev[2] > 0 and cur[2] > 0]
        if len(returns) < 2:
            result.issues.append(EnrichmentIssue(code="insufficient_returns", severity="warning", message="Not enough positive-price returns are available."))
            return result
        avg = sum(returns) / len(returns)
        variance = sum((x - avg) ** 2 for x in returns) / (len(returns) - 1)
        sorted_returns = sorted(returns)
        q05 = sorted_returns[max(0, int(len(sorted_returns) * 0.05) - 1)]
        q95 = sorted_returns[min(len(sorted_returns) - 1, int(len(sorted_returns) * 0.95))]
        values = {
            "observations": len(prepared),
            "return_observations": len(returns),
            "annualized_volatility": math.sqrt(variance) * math.sqrt(252),
            "mean_return": avg,
            "return_p05": q05,
            "return_p95": q95,
        }
        result.summaries.append(DerivedSummary(
            derived_id=stable_id(self.name, context.instrument_id, values),
            instrument_id=context.instrument_id,
            summary_type="volatility_summary",
            values=values,
            lineage=context.lineage_for_records([x[1] for x in prepared], algorithm=self.name, algorithm_version=self.version, parameters={"periods_per_year": 252}),
        ))
        return result
