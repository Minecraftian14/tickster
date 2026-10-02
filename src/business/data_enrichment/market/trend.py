from __future__ import annotations

from datetime import datetime, timezone

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedObservation, DerivedSeries, DerivedSeriesPoint, DerivedSummary, EnrichmentIssue, EnrichmentResult
from .common import prepare_price_records


def _sma(values: list[float]) -> float:
    return sum(values) / len(values)


class MovingAverageEnricher:
    name = "market.moving_averages"
    version = "0.2.0"
    requires = frozenset({"price.close"})
    provides = frozenset({"market.moving_average"})

    def __init__(self, windows: tuple[int, ...] = (20, 50, 200)) -> None:
        self.windows = tuple(sorted(set(windows)))

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        prepared = prepare_price_records(context)
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if not prepared:
            result.issues.append(EnrichmentIssue(code="no_observations", severity="warning", message="No valid close observations are available."))
            return result
        for window in self.windows:
            points: list[DerivedSeriesPoint] = []
            closes = [x[2] for x in prepared]
            for idx in range(window - 1, len(closes)):
                points.append(DerivedSeriesPoint(timestamp=prepared[idx][0], value=_sma(closes[idx + 1 - window:idx + 1]), source_record_ids=[x for x in (context.record_id(prepared[idx][1]),) if x]))
            result.series.append(DerivedSeries(
                derived_id=stable_id(self.name, context.instrument_id, window, [(p.timestamp.isoformat(), p.value) for p in points]),
                instrument_id=context.instrument_id,
                metric=f"sma_{window}",
                unit="price",
                points=points,
                lineage=context.lineage_for_records([x[1] for x in prepared], algorithm=self.name, algorithm_version=self.version, parameters={"window": window}, calculated_at=datetime.now(timezone.utc)),
                metadata={"window": window, "method": "simple_moving_average"},
            ))
        latest = prepared[-1]
        current = latest[2]
        values = {f"distance_from_sma_{window}": None for window in self.windows}
        for window in self.windows:
            if len(prepared) >= window:
                avg = _sma([x[2] for x in prepared[-window:]])
                values[f"distance_from_sma_{window}"] = current / avg - 1.0 if avg else None
        result.summaries.append(DerivedSummary(
            derived_id=stable_id(self.name, context.instrument_id, values),
            instrument_id=context.instrument_id,
            summary_type="moving_average_position",
            values={"current_close": current, **values},
            lineage=context.lineage_for_records([x[1] for x in prepared], algorithm=self.name, algorithm_version=self.version, parameters={"windows": self.windows}),
        ))
        return result
