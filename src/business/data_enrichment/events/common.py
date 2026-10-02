from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from data_foundation.temporal import is_visible_at

from ..core.context import EnrichmentContext
from ..market.common import close, timestamp


def event_time(record: Any) -> datetime | None:
    payload = EnrichmentContext.payload(record)
    for key in ("event_date", "announcement_date", "trade_date", "intimation_date", "broadcast_at", "acquisition_from", "timestamp", "date"):
        value = payload.get(key)
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if value is not None:
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    envelope = EnrichmentContext.temporal(record)
    for value in (envelope.event_time, envelope.observed_at, envelope.published_at):
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if value is not None:
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def visible_events(context: EnrichmentContext, records: Iterable[Any]) -> list[Any]:
    items = [record for record in records if event_time(record) is not None]
    if context.as_of is None:
        return items
    return [record for record in items if is_visible_at(record, context.as_of, strict=True)]


def event_type(record: Any) -> str:
    payload = EnrichmentContext.payload(record)
    value = payload.get("event_type") or payload.get("deal_type") or payload.get("action_type") or payload.get("record_type") or type(record).__name__
    return str(value)


def event_label(record: Any) -> str:
    payload = EnrichmentContext.payload(record)
    return str(payload.get("subject") or payload.get("title") or payload.get("description") or payload.get("event_type") or type(record).__name__)


def prepare_prices(records: Iterable[Any]) -> list[tuple[datetime, Any, float]]:
    prepared: list[tuple[datetime, Any, float]] = []
    for record in records:
        ts = timestamp(record)
        price = close(record)
        if ts is not None and price is not None and price > 0:
            prepared.append((ts, record, price))
    prepared.sort(key=lambda item: item[0])
    return prepared


def forward_return(prepared: list[tuple[datetime, Any, float]], start: datetime, offset: int) -> tuple[float | None, list[Any]]:
    candidates = [(ts, record, price) for ts, record, price in prepared if ts > start]
    if len(candidates) <= offset:
        return None, []
    base = candidates[0]
    target = candidates[offset]
    return target[2] / base[2] - 1.0, [base[1], target[1]]
