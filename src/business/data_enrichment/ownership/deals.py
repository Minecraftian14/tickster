from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSummary, EnrichmentIssue, EnrichmentResult
from data_foundation.temporal import is_visible_at
from .common import as_float, event_time, first


class LargeDealActivityEnricher:
    """Aggregate bulk/block/short-sale disclosures over configurable windows."""

    name = "ownership.large_deal_activity"
    version = "0.5.0"
    requires = frozenset({"large.deal"})
    provides = frozenset({"ownership.large_deal_activity"})

    def __init__(self, *, windows_days: tuple[int, ...] = (30, 90, 365)) -> None:
        self.windows_days = tuple(sorted(set(windows_days)))

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        records = [r for r in context.metadata.get("large_deal_records", context.records_for_instrument()) if event_time(r) is not None]
        if not records:
            result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
            result.issues.append(EnrichmentIssue(code="no_large_deals", severity="warning", message="No dated bulk/block/short-sale deals were supplied."))
            return result
        if context.as_of is not None:
            records = [r for r in records if is_visible_at(r, context.as_of, strict=True)]
        records.sort(key=lambda r: event_time(r) or datetime.min.replace(tzinfo=timezone.utc))
        anchor = context.as_of or max(event_time(r) for r in records)
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        for window in self.windows_days:
            start = anchor - timedelta(days=window)
            selected = [r for r in records if start <= (event_time(r) or start) <= anchor]
            buys = sells = 0.0
            gross_qty = gross_value = 0.0
            distinct_clients: set[str] = set()
            type_counts: dict[str, int] = {}
            for record in selected:
                payload = EnrichmentContext.payload(record)
                qty = as_float(first(payload, "quantity", "qty")) or 0.0
                price = as_float(first(payload, "weighted_average_price", "watp")) or 0.0
                side = str(first(payload, "side", "buySell", "buy_sell") or "").strip().lower()
                deal_type = str(first(payload, "deal_type", "dealType") or getattr(record, "deal_type", "unknown") or "unknown").lower()
                notional = qty * price if qty and price else as_float(first(payload, "value", "transaction_value")) or 0.0
                gross_qty += abs(qty)
                gross_value += abs(notional)
                if "buy" in side:
                    buys += abs(notional)
                elif "sell" in side:
                    sells += abs(notional)
                client = str(first(payload, "client_name", "clientName", "client") or "").strip()
                if client:
                    distinct_clients.add(client)
                type_counts[deal_type] = type_counts.get(deal_type, 0) + 1
            values: dict[str, Any] = {
                "window_days": window,
                "anchor": anchor,
                "deal_count": len(selected),
                "distinct_clients": len(distinct_clients),
                "gross_quantity": gross_qty,
                "gross_value": gross_value,
                "buy_value": buys,
                "sell_value": sells,
                "net_value": buys - sells,
                "buy_to_sell_value_ratio": buys / sells if sells > 0 else None,
                "deal_type_counts": type_counts,
            }
            result.summaries.append(DerivedSummary(
                derived_id=stable_id(self.name, context.instrument_id, values),
                instrument_id=context.instrument_id,
                summary_type="large_deal_activity",
                values=values,
                lineage=context.lineage_for_records(selected, algorithm=self.name, algorithm_version=self.version, parameters={"window_days": window, "anchor": anchor}, calculated_at=datetime.now(timezone.utc)),
                metadata={"period_start": start, "period_end": anchor},
            ))
        return result
