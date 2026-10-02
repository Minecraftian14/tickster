from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSummary, EnrichmentIssue, EnrichmentResult
from data_foundation.temporal import is_visible_at
from .common import event_time, first, signed_transaction


class InsiderActivityEnricher:
    """Aggregate disclosed insider/PIT activity over configurable lookback windows."""

    name = "ownership.insider_activity"
    version = "0.5.0"
    requires = frozenset({"insider.transaction"})
    provides = frozenset({"ownership.insider_activity"})

    def __init__(self, *, windows_days: tuple[int, ...] = (30, 90, 365)) -> None:
        self.windows_days = tuple(sorted(set(windows_days)))

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        records = [r for r in context.metadata.get("insider_records", context.records_for_instrument()) if event_time(r) is not None]
        records = [r for r in records if context.as_of is None or not EnrichmentContext.temporal(r).available_at or EnrichmentContext.temporal(r).available_at <= context.as_of]
        records.sort(key=lambda r: event_time(r) or datetime.min.replace(tzinfo=timezone.utc))
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if not records:
            result.issues.append(EnrichmentIssue(code="no_insider_activity", severity="warning", message="No dated insider transactions were supplied."))
            return result
        anchor = context.as_of or max(event_time(r) for r in records)
        summaries: list[DerivedSummary] = []
        for window in self.windows_days:
            start = anchor - timedelta(days=window)
            selected = [r for r in records if start <= (event_time(r) or start) <= anchor]
            signed = [signed_transaction(r) for r in selected]
            net_qty = sum(item[0] for item in signed)
            net_value = sum(item[1] for item in signed)
            buy_qty = sum(max(item[0], 0.0) for item in signed)
            sell_qty = sum(max(-item[0], 0.0) for item in signed)
            buy_value = sum(max(item[1], 0.0) for item in signed)
            sell_value = sum(max(-item[1], 0.0) for item in signed)
            people = {str(first(EnrichmentContext.payload(r), "person_name", "personName", "name") or "").strip() for r in selected}
            people.discard("")
            values: dict[str, Any] = {
                "window_days": window,
                "anchor": anchor,
                "transaction_count": len(selected),
                "distinct_people": len(people),
                "buy_quantity": buy_qty,
                "sell_quantity": sell_qty,
                "net_quantity": net_qty,
                "buy_value": buy_value,
                "sell_value": sell_value,
                "net_value": net_value,
                "buy_to_sell_quantity_ratio": buy_qty / sell_qty if sell_qty > 0 else None,
                "buy_to_sell_value_ratio": buy_value / sell_value if sell_value > 0 else None,
            }
            summaries.append(DerivedSummary(
                derived_id=stable_id(self.name, context.instrument_id, values),
                instrument_id=context.instrument_id,
                summary_type="insider_activity",
                values=values,
                lineage=context.lineage_for_records(selected, algorithm=self.name, algorithm_version=self.version, parameters={"window_days": window, "anchor": anchor}, calculated_at=datetime.now(timezone.utc)),
                metadata={"period_start": start, "period_end": anchor},
            ))
        result.summaries.extend(summaries)
        return result
