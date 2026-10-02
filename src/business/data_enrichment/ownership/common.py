from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Iterable

from ..core.context import EnrichmentContext


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if value == value and abs(value) != float("inf") else None


def as_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def first(payload: dict[str, Any], *names: str) -> Any:
    normalized = {str(k).strip().lower().replace(" ", "").replace("_", ""): k for k in payload}
    for name in names:
        key = normalized.get(name.lower().replace(" ", "").replace("_", ""))
        if key is not None:
            return payload[key]
    return None


def holder_value(record: Any, aliases: tuple[str, ...]) -> float | None:
    payload = EnrichmentContext.payload(record)
    holders = payload.get("holders") if isinstance(payload.get("holders"), dict) else getattr(record, "holders", {})
    if not isinstance(holders, dict):
        holders = {}
    candidates = dict(holders)
    raw = holders.get("raw")
    if isinstance(raw, dict):
        candidates.update(raw)
    return as_float(first(candidates, *aliases))


def record_date(record: Any) -> date | None:
    payload = EnrichmentContext.payload(record)
    for value in (
        payload.get("period_end"),
        payload.get("trade_date"),
        payload.get("event_date"),
        payload.get("announcement_date"),
        payload.get("date"),
    ):
        parsed = as_datetime(value)
        if parsed is not None:
            return parsed.date()
    envelope = EnrichmentContext.temporal(record)
    candidate = envelope.event_time or envelope.period_end
    parsed = as_datetime(candidate)
    return parsed.date() if parsed is not None else None


def event_time(record: Any) -> datetime | None:
    payload = EnrichmentContext.payload(record)
    for key in (
        "event_date", "announcement_date", "trade_date", "intimation_date",
        "broadcast_at", "acquisition_from", "timestamp", "date",
    ):
        parsed = as_datetime(payload.get(key))
        if parsed is not None:
            return parsed
    envelope = EnrichmentContext.temporal(record)
    for candidate in (envelope.event_time, envelope.observed_at, envelope.published_at):
        parsed = as_datetime(candidate)
        if parsed is not None:
            return parsed
    return None


def availability(record: Any) -> datetime | None:
    return EnrichmentContext.temporal(record).available_at


def latest_available(records: Iterable[Any]) -> datetime | None:
    values = [availability(record) for record in records]
    values = [value for value in values if value is not None]
    return max(values) if values else None


def signed_transaction(record: Any) -> tuple[float, float, float]:
    """Return signed quantity, signed value, and absolute quantity-like value."""
    payload = EnrichmentContext.payload(record)
    acquired = as_float(first(payload, "securities_acquired", "buy_quantity", "quantity", "qty")) or 0.0
    buy_qty = as_float(first(payload, "buy_quantity", "buyQuantity")) or 0.0
    sell_qty = as_float(first(payload, "sell_quantity", "sellquantity", "sellQuantity")) or 0.0
    acquired_value = as_float(first(payload, "transaction_value", "buy_value", "sell_value", "value")) or 0.0
    buy_value = as_float(first(payload, "buy_value", "buyValue")) or 0.0
    sell_value = as_float(first(payload, "sell_value", "sellValue")) or 0.0
    transaction_type = str(first(payload, "transaction_type", "tdpTransactionType", "side", "action") or "").lower()
    mode = str(first(payload, "mode") or "").lower()

    explicit_signed = False
    if buy_qty or sell_qty or buy_value or sell_value:
        explicit_signed = True
    if explicit_signed:
        quantity = buy_qty - sell_qty
        value = buy_value - sell_value
        gross_qty = buy_qty + sell_qty
        gross_value = buy_value + sell_value
        if not value:
            value = acquired_value if quantity >= 0 else -abs(acquired_value)
        return quantity, value, gross_qty or abs(quantity)

    negative_words = ("sell", "dispos", "sale", "transfer out")
    positive_words = ("buy", "acqui", "purchase", "subscribe", "allot")
    if any(word in transaction_type for word in negative_words) or any(word in mode for word in negative_words):
        return -abs(acquired), -abs(acquired_value), abs(acquired)
    if any(word in transaction_type for word in positive_words) or any(word in mode for word in positive_words):
        return abs(acquired), abs(acquired_value), abs(acquired)
    return 0.0, 0.0, abs(acquired)
