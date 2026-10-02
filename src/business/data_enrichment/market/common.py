from __future__ import annotations

from datetime import date, datetime, timezone
import math
from typing import Any, Iterable

from ..core.context import EnrichmentContext


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def as_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def timestamp(record: Any) -> datetime | None:
    payload = EnrichmentContext.payload(record)
    for key in ("timestamp", "observation_date", "trade_date", "date"):
        parsed = as_datetime(payload.get(key))
        if parsed is not None:
            return parsed
    envelope = EnrichmentContext.temporal(record)
    for candidate in (envelope.event_time, envelope.observed_at, envelope.published_at):
        parsed = as_datetime(candidate)
        if parsed is not None:
            return parsed
    return None


def field(record: Any, *names: str) -> float | None:
    payload = EnrichmentContext.payload(record)
    for name in names:
        parsed = as_float(payload.get(name))
        if parsed is not None:
            return parsed
    return None


def close(record: Any) -> float | None:
    return field(record, "close", "Close", "last_price", "ltp")


def open_price(record: Any) -> float | None:
    return field(record, "open", "Open")


def high(record: Any) -> float | None:
    return field(record, "high", "High")


def low(record: Any) -> float | None:
    return field(record, "low", "Low")


def volume(record: Any) -> float | None:
    return field(record, "volume", "Volume", "total_traded_quantity")


def traded_value(record: Any) -> float | None:
    return field(record, "traded_value", "tradedValue", "total_traded_value", "turnover")


def delivery_quantity(record: Any) -> float | None:
    return field(record, "delivery_quantity", "delivery_qty", "DELIV_QTY", "deliverable_quantity")


def delivery_percent(record: Any) -> float | None:
    return field(record, "delivery_percent", "DELIV_PER", "delivery_percentage")


def instrument_id(record: Any, fallback: str | None) -> str | None:
    return EnrichmentContext.instrument_id(record) or fallback


def prepare_price_records(context: EnrichmentContext, *, require_close: bool = True) -> list[tuple[datetime, Any, float]]:
    prepared: list[tuple[datetime, Any, float]] = []
    for record in context.records_for_instrument():
        ts = timestamp(record)
        value = close(record)
        if ts is None or (require_close and value is None):
            continue
        if value is None:
            continue
        prepared.append((ts, record, value))
    prepared.sort(key=lambda item: item[0])
    return prepared


def window_values(values: list[float], window: int) -> list[list[float] | None]:
    if window <= 0:
        raise ValueError("window must be positive")
    result: list[list[float] | None] = []
    for index in range(len(values)):
        start = index - window + 1
        result.append(values[start:index + 1] if start >= 0 else None)
    return result


def mean_or_none(values: Iterable[float]) -> float | None:
    seq = list(values)
    return sum(seq) / len(seq) if seq else None


def stddev_population(values: Iterable[float]) -> float | None:
    seq = list(values)
    if not seq:
        return None
    avg = sum(seq) / len(seq)
    return math.sqrt(sum((x - avg) ** 2 for x in seq) / len(seq))


def annualized_volatility(returns: Iterable[float], periods_per_year: int = 252) -> float | None:
    seq = list(returns)
    if len(seq) < 2:
        return None
    avg = sum(seq) / len(seq)
    variance = sum((x - avg) ** 2 for x in seq) / (len(seq) - 1)
    return math.sqrt(variance) * math.sqrt(periods_per_year)
