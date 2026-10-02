from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSummary, EnrichmentIssue, EnrichmentResult
from .common import event_time, event_type, visible_events


class CompanyEventSummaryEnricher:
    """Describe the company's recent event/disclosure activity without interpretation."""

    name = "events.company_summary"
    version = "0.5.0"
    requires = frozenset({"company.event"})
    provides = frozenset({"events.company_summary"})

    def __init__(self, *, windows_days: tuple[int, ...] = (30, 90, 365)) -> None:
        self.windows_days = tuple(sorted(set(windows_days)))

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        records = visible_events(context, context.metadata.get("event_records", ()))
        if not records:
            records = visible_events(context, context.records_for_instrument())
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if not records:
            result.issues.append(EnrichmentIssue(code="no_company_events", severity="warning", message="No dated company events were supplied."))
            return result
        anchor = context.as_of or max(event_time(r) for r in records)
        for window in self.windows_days:
            start = anchor - timedelta(days=window)
            selected = [r for r in records if start <= (event_time(r) or start) <= anchor]
            counts = Counter(event_type(r) for r in selected)
            last_record = max(selected, key=lambda r: event_time(r) or datetime.min.replace(tzinfo=timezone.utc), default=None)
            last_time = event_time(last_record) if last_record is not None else None
            values: dict[str, Any] = {
                "window_days": window,
                "anchor": anchor,
                "event_count": len(selected),
                "event_type_counts": dict(counts),
                "distinct_event_types": len(counts),
                "last_event_at": last_time,
                "days_since_last_event": (anchor - last_time).days if last_time else None,
            }
            result.summaries.append(DerivedSummary(
                derived_id=stable_id(self.name, context.instrument_id, values),
                instrument_id=context.instrument_id,
                summary_type="company_event_summary",
                values=values,
                lineage=context.lineage_for_records(selected, algorithm=self.name, algorithm_version=self.version, parameters={"window_days": window, "anchor": anchor}, calculated_at=datetime.now(timezone.utc)),
                metadata={"period_start": start, "period_end": anchor},
            ))
        return result
