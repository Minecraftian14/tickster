from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSummary, EnrichmentIssue, EnrichmentResult
from .common import event_label, event_time, event_type, forward_return, prepare_prices, visible_events


class EventReactionEnricher:
    """Measure descriptive forward market reactions following supplied events."""

    name = "events.market_reaction"
    version = "0.5.0"
    requires = frozenset({"company.event", "price.close"})
    provides = frozenset({"events.market_reaction"})

    def __init__(self, *, horizons: tuple[int, ...] = (1, 5, 21)) -> None:
        self.horizons = tuple(sorted(set(horizons)))

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        events = visible_events(context, context.metadata.get("event_records", ()))
        prices = prepare_prices(context.records_for_instrument())
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if not events:
            result.issues.append(EnrichmentIssue(code="no_event_records", severity="warning", message="No dated event records were supplied."))
            return result
        if len(prices) < 2:
            result.issues.append(EnrichmentIssue(code="insufficient_price_history", severity="warning", message="At least two valid price observations are required for event reaction analysis."))
            return result
        for event in events:
            start = event_time(event)
            values: dict[str, Any] = {
                "event_type": event_type(event),
                "event_label": event_label(event),
                "event_time": start,
            }
            supporting_records = [event]
            for horizon in self.horizons:
                reaction, price_records = forward_return(prices, start, horizon)
                values[f"forward_return_{horizon}p"] = reaction
                supporting_records.extend(price_records)
            supporting_records = _unique_records(supporting_records, context)
            result.summaries.append(DerivedSummary(
                derived_id=stable_id(self.name, context.instrument_id, EnrichmentContext.record_id(event), values),
                instrument_id=context.instrument_id,
                summary_type="event_market_reaction",
                values=values,
                lineage=context.lineage_for_records(supporting_records, algorithm=self.name, algorithm_version=self.version, parameters={"horizons": self.horizons}, calculated_at=datetime.now(timezone.utc)),
                metadata={"event_record_id": context.record_id(event), "uses_future_outcome": True},
            ))
        return result


def _unique_records(records: list[Any], context: EnrichmentContext) -> list[Any]:
    out: list[Any] = []
    seen: set[str] = set()
    for record in records:
        rid = context.record_id(record) or f"anonymous:{id(record)}"
        if rid in seen:
            continue
        seen.add(rid)
        out.append(record)
    return out
