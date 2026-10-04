from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any

from .models import TemporalEnvelope


def _end_of_day(value: date) -> datetime:
    return datetime.combine(value, time.max, tzinfo=timezone.utc)


def _as_datetime(value: datetime | date | None, *, date_is_conservative: bool = True) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return _end_of_day(value) if date_is_conservative else datetime.combine(value, time.min, tzinfo=timezone.utc)


def _precision(value: datetime | date | None) -> str:
    if value is None:
        return "unknown"
    return "instant" if isinstance(value, datetime) else "date"


def temporal_envelope(record: Any, *, conservative_date_availability: bool = True) -> TemporalEnvelope:
    """Read temporal semantics from typed records or CanonicalRecord wrappers."""
    payload = getattr(record, "payload", None)
    payload = payload if isinstance(payload, dict) else {}
    payload_provenance = payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    provenance = getattr(record, "provenance", None)

    def value(name: str) -> Any:
        direct = getattr(record, name, None)
        if direct is not None:
            return direct
        return payload.get(name)

    def provenance_value(name: str) -> Any:
        direct = getattr(provenance, name, None) if provenance is not None else None
        if direct is not None:
            return direct
        return payload_provenance.get(name)

    published = provenance_value("published_at") or value("published_at")
    observed = provenance_value("observed_at") or value("observed_at")
    retrieved = provenance_value("retrieved_at") or value("retrieved_at")

    event_time = (
        value("event_date")
        or value("announcement_date")
        or value("trade_date")
        or value("timestamp")
        or value("observation_date")
        or published
        or observed
    )
    effective_time = value("ex_date") or value("effective_date")
    received = value("received_at") or provenance_value("received_at")

    if published is not None:
        available_at, basis = _as_datetime(published, date_is_conservative=conservative_date_availability), "published"
        availability_precision = _precision(published)
    elif received is not None:
        available_at, basis = _as_datetime(received, date_is_conservative=conservative_date_availability), "received"
        availability_precision = _precision(received)
    elif observed is not None:
        available_at, basis = _as_datetime(observed, date_is_conservative=conservative_date_availability), "observed"
        availability_precision = _precision(observed)
    elif retrieved is not None:
        available_at, basis = _as_datetime(retrieved, date_is_conservative=conservative_date_availability), "retrieved"
        availability_precision = _precision(retrieved)
    else:
        available_at, basis = None, "unknown"
        availability_precision = "unknown"

    return TemporalEnvelope(
        event_time=event_time,
        effective_time=effective_time,
        published_at=published,
        observed_at=observed,
        retrieved_at=retrieved,
        period_start=value("period_start"),
        period_end=value("period_end"),
        available_at=available_at,
        availability_basis=basis,
        availability_precision=availability_precision,
    )


def is_visible_at(record: Any, as_of: datetime, *, strict: bool = True, conservative_date_availability: bool = True) -> bool:
    envelope = temporal_envelope(record, conservative_date_availability=conservative_date_availability)
    if envelope.available_at is None:
        return not strict
    # Retrieval time proves when our collector obtained the record, not when the
    # information became knowable to the market. Conservative point-in-time
    # queries therefore exclude retrieval-only availability in strict mode.
    if strict and envelope.availability_basis == "retrieved":
        return False
    return envelope.available_at <= as_of


def point_in_time_filter(
    records: list[Any],
    as_of: datetime,
    *,
    strict: bool = True,
    conservative_date_availability: bool = True,
) -> list[Any]:
    return [
        record
        for record in records
        if is_visible_at(record, as_of, strict=strict, conservative_date_availability=conservative_date_availability)
    ]
