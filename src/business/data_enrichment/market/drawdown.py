from __future__ import annotations

from datetime import datetime, timezone

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSeries, DerivedSeriesPoint, DerivedSummary, EnrichmentIssue, EnrichmentResult
from .common import prepare_price_records


class DrawdownEnricher:
    name = "market.drawdown"
    version = "0.2.0"
    requires = frozenset({"price.close"})
    provides = frozenset({"market.drawdown", "market.max_drawdown"})

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        prepared = prepare_price_records(context)
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if len(prepared) < 2:
            result.issues.append(EnrichmentIssue(code="insufficient_observations", severity="warning", message="At least two closes are required."))
            return result
        peak = prepared[0][2]
        points: list[DerivedSeriesPoint] = []
        min_dd = 0.0
        trough_ts = prepared[0][0]
        peak_ts = prepared[0][0]
        current_peak_ts = prepared[0][0]
        for ts, record, price in prepared:
            if price > peak:
                peak = price
                current_peak_ts = ts
            dd = price / peak - 1.0 if peak > 0 else 0.0
            points.append(DerivedSeriesPoint(timestamp=ts, value=dd, source_record_ids=[x for x in (context.record_id(record),) if x]))
            if dd < min_dd:
                min_dd = dd
                trough_ts = ts
                peak_ts = current_peak_ts
        values = {
            "current_drawdown": points[-1].value,
            "maximum_drawdown": min_dd,
            "peak_timestamp": peak_ts,
            "trough_timestamp": trough_ts,
            "time_since_peak_days": max((prepared[-1][0] - peak_ts).days, 0),
        }
        lineage = context.lineage_for_records([x[1] for x in prepared], algorithm=self.name, algorithm_version=self.version, parameters={}, calculated_at=datetime.now(timezone.utc))
        result.series.append(DerivedSeries(
            derived_id=stable_id(self.name, context.instrument_id, [(p.timestamp.isoformat(), p.value) for p in points]),
            instrument_id=context.instrument_id,
            metric="drawdown",
            unit="fraction",
            points=points,
            lineage=lineage,
            metadata={"definition": "price / running_peak - 1"},
        ))
        result.summaries.append(DerivedSummary(
            derived_id=stable_id(self.name, context.instrument_id, values),
            instrument_id=context.instrument_id,
            summary_type="drawdown_summary",
            values=values,
            lineage=lineage,
        ))
        return result
