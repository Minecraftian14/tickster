from __future__ import annotations

from datetime import date, datetime, time, timezone
from hashlib import sha256
from typing import Any, Iterable

from .models import CompanyTimeline, TimelineEntry
from .temporal import _as_datetime, temporal_envelope


def _payload(record: Any) -> dict[str, Any]:
    payload = getattr(record, "payload", None)
    return payload if isinstance(payload, dict) else {}


def _record_id(record: Any) -> str | None:
    direct = getattr(record, "record_id", None)
    if direct:
        return str(direct)
    for key in (
        "event_id", "filing_id", "document_id", "asset_id", "news_id", "instrument_id",
        "series_id", "index_id", "observation_id", "relationship_id",
    ):
        value = getattr(record, key, None)
        if value:
            return str(value)
        value = _payload(record).get(key)
        if value:
            return str(value)
    canonical_payload = getattr(record, "payload", None)
    if canonical_payload is not None:
        body = repr(canonical_payload).encode("utf-8")
    elif hasattr(record, "model_dump"):
        try:
            body = repr(record.model_dump(mode="json")).encode("utf-8")
        except Exception:
            body = repr(record).encode("utf-8")
    else:
        body = repr(record).encode("utf-8")
    return "synthetic:" + sha256(body).hexdigest()


def _instrument_ids(record: Any) -> list[str]:
    payload = _payload(record)
    values: list[str] = []
    direct = getattr(record, "instrument_id", None) or payload.get("instrument_id")
    if direct:
        values.append(str(direct))
    for value in (getattr(record, "instrument_ids", None) or payload.get("instrument_ids") or []):
        if value:
            values.append(str(value))
    return list(dict.fromkeys(values))


def _instrument_id(record: Any) -> str | None:
    ids = _instrument_ids(record)
    return ids[0] if ids else None


def _title(record: Any) -> str:
    payload = _payload(record)
    return str(
        getattr(record, "title", None)
        or getattr(record, "subject", None)
        or getattr(record, "name", None)
        or getattr(record, "statement_name", None)
        or getattr(record, "event_type", None)
        or getattr(record, "document_type", None)
        or payload.get("title")
        or payload.get("subject")
        or payload.get("event_type")
        or payload.get("document_type")
        or getattr(record, "record_type", None)
        or record.__class__.__name__
    )


def _record_evidence(record: Any) -> list[str]:
    evidence: list[str] = []
    provenance = getattr(record, "provenance", None)
    raw_ref = getattr(provenance, "raw_ref", None) or getattr(record, "raw_ref", None)
    if raw_ref:
        evidence.append(str(raw_ref))
    evidence.extend(str(value) for value in getattr(record, "source_observation_ids", None) or [])
    return sorted(set(evidence))


def _sort_datetime(value: datetime | date | None) -> tuple[bool, datetime | None]:
    if value is None:
        return True, None
    if isinstance(value, datetime):
        return False, value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return False, datetime.combine(value, time.min, tzinfo=timezone.utc)


def build_company_timeline(instrument_id: str, records: Iterable[Any]) -> CompanyTimeline:
    entries: list[TimelineEntry] = []
    for record in records:
        if instrument_id not in _instrument_ids(record):
            continue
        record_id = _record_id(record)
        if not record_id:
            continue
        envelope = temporal_envelope(record)
        entry_key = sha256(f"{instrument_id}|{getattr(record, 'record_type', record.__class__.__name__)}|{record_id}".encode()).hexdigest()
        entries.append(
            TimelineEntry(
                entry_id=entry_key,
                instrument_id=instrument_id,
                entry_type=str(getattr(record, "record_type", record.__class__.__name__)),
                title=_title(record),
                event_time=envelope.event_time,
                available_at=envelope.available_at,
                source_record_id=record_id,
                evidence_ids=_record_evidence(record),
                metadata={
                    "availability_basis": envelope.availability_basis,
                    "availability_precision": envelope.availability_precision,
                    "effective_time": envelope.effective_time,
                },
            )
        )

    entries.sort(
        key=lambda x: (
            *_sort_datetime(x.event_time),
            x.available_at is None,
            x.available_at,
            x.entry_type,
            x.entry_id,
        )
    )
    return CompanyTimeline(
        instrument_id=instrument_id,
        entries=entries,
        metadata={"entry_count": len(entries)},
    )
