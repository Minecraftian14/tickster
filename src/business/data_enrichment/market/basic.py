from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSeries, DerivedSeriesPoint, DerivedSummary, DerivationLineage, EnrichmentIssue, EnrichmentResult


def _as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _timestamp(record: Any, fallback: datetime) -> datetime:
    payload = EnrichmentContext.payload(record)
    value = payload.get("timestamp") or payload.get("observation_date") or payload.get("trade_date")
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    envelope = EnrichmentContext.temporal(record)
    candidate = envelope.event_time or envelope.observed_at
    if isinstance(candidate, datetime):
        return candidate if candidate.tzinfo else candidate.replace(tzinfo=timezone.utc)
    return fallback


def _close(record: Any) -> float | None:
    payload = EnrichmentContext.payload(record)
    for key in ("close", "Close", "last_price", "ltp"):
        value = _as_float(payload.get(key))
        if value is not None:
            return value
    return None


class SimpleReturnEnricher:
    """Provider-neutral close-to-close return calculation."""

    name = "market.simple_return"
    version = "0.1.0"
    requires = frozenset({"price.close"})
    provides = frozenset({"market.return"})

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        records = context.records_for_instrument()
        prepared = []
        for record in records:
            close = _close(record)
            if close is None:
                continue
            prepared.append(( _timestamp(record, context.as_of or datetime.now(timezone.utc)), close, record))
        prepared.sort(key=lambda item: item[0])
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if len(prepared) < 2:
            result.issues.append(EnrichmentIssue(
                code="insufficient_observations",
                severity="warning",
                message="At least two close observations are required for a return series.",
                metric="return_1p",
            ))
            return result
        now = datetime.now(timezone.utc)
        points: list[DerivedSeriesPoint] = []
        for previous, current in zip(prepared, prepared[1:]):
            previous_ts, previous_close, previous_record = previous
            current_ts, current_close, current_record = current
            if previous_close == 0:
                result.issues.append(EnrichmentIssue(
                    code="zero_denominator",
                    severity="error",
                    message="Cannot compute return from a zero previous close.",
                    metric="return_1p",
                    record_ids=[rid for r in (previous_record, current_record) if (rid := EnrichmentContext.record_id(r))],
                ))
                continue
            value = current_close / previous_close - 1.0
            current_id = EnrichmentContext.record_id(current_record)
            points.append(DerivedSeriesPoint(timestamp=current_ts, value=value, source_record_ids=[x for x in (EnrichmentContext.record_id(previous_record), current_id) if x]))
        result.series.append(DerivedSeries(
            derived_id=stable_id(self.name, context.instrument_id, [(p.timestamp.isoformat(), p.value) for p in points]),
            instrument_id=context.instrument_id,
            metric="return_1p",
            unit="fraction",
            points=points,
            lineage=context.lineage_for_records([x[2] for x in prepared], algorithm=self.name, algorithm_version=self.version, parameters={}, calculated_at=now),
            metadata={"frequency": "input-observation-frequency"},
        ))
        return result


class ReturnSummaryEnricher:
    """Summarize a supplied close history into long-horizon descriptive statistics."""

    name = "market.return_summary"
    version = "0.1.0"
    requires = frozenset({"price.close"})
    provides = frozenset({"market.return_summary"})

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        records = context.records_for_instrument()
        prepared = sorted(
            (( _timestamp(r, context.as_of or datetime.now(timezone.utc)), _close(r), r) for r in records),
            key=lambda x: x[0],
        )
        prepared = [x for x in prepared if x[1] is not None]
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if len(prepared) < 2:
            result.issues.append(EnrichmentIssue(code="insufficient_observations", severity="warning", message="At least two closes required for return summary."))
            return result
        returns = []
        for prev, curr in zip(prepared, prepared[1:]):
            if prev[1] == 0:
                continue
            returns.append(curr[1] / prev[1] - 1.0)
        if not returns:
            result.issues.append(EnrichmentIssue(code="no_valid_returns", severity="warning", message="No valid returns could be calculated."))
            return result
        now = datetime.now(timezone.utc)
        values = {
            "observations": len(prepared),
            "return_observations": len(returns),
            "cumulative_return": prepared[-1][1] / prepared[0][1] - 1.0,
            "mean_period_return": mean(returns),
            "best_period_return": max(returns),
            "worst_period_return": min(returns),
        }
        result.summaries.append(DerivedSummary(
            derived_id=stable_id(self.name, context.instrument_id, values),
            instrument_id=context.instrument_id,
            summary_type="return_summary",
            values=values,
            lineage=context.lineage_for_records([x[2] for x in prepared], algorithm=self.name, algorithm_version=self.version, parameters={}, calculated_at=now),
        ))
        return result
