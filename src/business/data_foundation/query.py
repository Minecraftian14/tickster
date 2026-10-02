from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from .identity import IdentityRegistry
from .temporal import point_in_time_filter
from .temporal_index import TemporalIndex


def records_visible_at(
    records: list[Any],
    as_of: datetime,
    *,
    instrument_id: str | None = None,
    strict: bool = True,
) -> list[Any]:
    candidates = records
    if instrument_id is not None:
        candidates = [
            record
            for record in candidates
            if getattr(record, "instrument_id", None) == instrument_id
            or instrument_id in getattr(record, "instrument_ids", [])
        ]
    return point_in_time_filter(candidates, as_of, strict=strict)


def build_temporal_index(records: Iterable[Any], *, identity_registry: IdentityRegistry | None = None) -> TemporalIndex:
    return TemporalIndex(records, identity_registry=identity_registry)


def what_was_known_at(index: TemporalIndex, company_or_instrument: str, as_of: datetime, *, strict: bool = True) -> list[Any]:
    return index.what_was_known_at(company_or_instrument, as_of, strict=strict)


def events_between(index: TemporalIndex, company_or_instrument: str, start: datetime, end: datetime, *, event_types: set[str] | None = None, require_available_by_end: bool = False) -> list[Any]:
    return index.events_between(company_or_instrument, start, end, event_types=event_types, require_available_by_end=require_available_by_end)


def documents_available_at(index: TemporalIndex, company_or_instrument: str, as_of: datetime, *, strict: bool = True) -> list[Any]:
    return index.documents_available_at(company_or_instrument, as_of, strict=strict)
