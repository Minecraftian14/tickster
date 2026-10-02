from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any, Iterable

from .identity import IdentityRegistry
from .models import CanonicalBundle, CompanyTimeline, RelationshipGraph
from .relationships import build_relationship_graph
from .temporal import is_visible_at, temporal_envelope
from .timeline import build_company_timeline


def _instrument_ids(record: Any) -> set[str]:
    direct = getattr(record, "instrument_id", None)
    values = set()
    if direct:
        values.add(str(direct))
    for value in getattr(record, "instrument_ids", None) or []:
        if value:
            values.add(str(value))
    return values


def _event_time(record: Any) -> Any:
    return temporal_envelope(record).event_time


def _event_datetime(record: Any) -> datetime | None:
    value = _event_time(record)
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _record_type(record: Any) -> str:
    return record.__class__.__name__


def _resolve_entity(registry: IdentityRegistry, entity: str, *, as_of: datetime | None = None) -> str | None:
    identity = registry.identity(entity)
    if identity is not None:
        return identity.instrument_id
    resolved = registry.company.resolve(entity, as_of=as_of)
    return resolved.instrument_id if resolved else None


class TemporalIndex:
    """In-memory point-in-time query index over typed canonical records."""

    def __init__(self, records: Iterable[Any] = (), *, identity_registry: IdentityRegistry | None = None) -> None:
        self.records = list(records)
        self.identity_registry = identity_registry or IdentityRegistry()
        self._by_instrument: dict[str, list[Any]] = {}
        self._index()

    @classmethod
    def from_bundle(cls, bundle: CanonicalBundle) -> "TemporalIndex":
        identities = bundle.identities
        return cls(bundle.records, identity_registry=IdentityRegistry.from_identities(identities))

    def _index(self) -> None:
        self._by_instrument = {}
        for record in self.records:
            for instrument_id in _instrument_ids(record):
                self._by_instrument.setdefault(instrument_id, []).append(record)
        for records in self._by_instrument.values():
            records.sort(key=lambda item: (_event_datetime(item) is None, _event_datetime(item), _record_type(item)))

    def add(self, record: Any) -> None:
        self.records.append(record)
        for instrument_id in _instrument_ids(record):
            self._by_instrument.setdefault(instrument_id, []).append(record)

    def resolve_entity(self, company_or_instrument: str, *, as_of: datetime | None = None) -> str | None:
        return _resolve_entity(self.identity_registry, company_or_instrument, as_of=as_of)

    def records_visible_at(self, company_or_instrument: str, as_of: datetime, *, strict: bool = True) -> list[Any]:
        instrument_id = self.resolve_entity(company_or_instrument, as_of=as_of) or company_or_instrument
        candidates = self._by_instrument.get(instrument_id, [])
        return [record for record in candidates if is_visible_at(record, as_of, strict=strict)]

    def what_was_known_at(self, company_or_instrument: str, as_of: datetime, *, strict: bool = True) -> list[Any]:
        """Return all records for the resolved instrument visible by ``as_of``.

        This is intentionally a factual snapshot: it does not rank, summarize,
        predict, or infer consequences. Ordering is by event time then availability.
        """
        records = self.records_visible_at(company_or_instrument, as_of, strict=strict)
        return sorted(
            records,
            key=lambda item: (
                _event_datetime(item) is None,
                _event_datetime(item),
                temporal_envelope(item).available_at is None,
                temporal_envelope(item).available_at,
                _record_type(item),
            ),
        )

    def events_between(
        self,
        company_or_instrument: str,
        start: datetime,
        end: datetime,
        *,
        event_types: set[str] | None = None,
        require_available_by_end: bool = False,
    ) -> list[Any]:
        instrument_id = self.resolve_entity(company_or_instrument, as_of=start) or company_or_instrument
        results: list[Any] = []
        for record in self._by_instrument.get(instrument_id, []):
            event_time = _event_datetime(record)
            if event_time is None or not (start <= event_time <= end):
                continue
            if event_types and _record_type(record) not in event_types:
                continue
            if require_available_by_end and not is_visible_at(record, end, strict=True):
                continue
            results.append(record)
        return sorted(results, key=lambda item: (_event_datetime(item) is None, _event_datetime(item), _record_type(item)))

    def documents_available_at(self, company_or_instrument: str, as_of: datetime, *, strict: bool = True) -> list[Any]:
        records = self.records_visible_at(company_or_instrument, as_of, strict=strict)
        return [
            record
            for record in records
            if _record_type(record) in {"CompanyDocument", "DocumentAsset", "RegulatoryDocument", "Filing"}
        ]

    def company_timeline(self, company_or_instrument: str) -> CompanyTimeline:
        instrument_id = self.resolve_entity(company_or_instrument) or company_or_instrument
        return build_company_timeline(instrument_id, self._by_instrument.get(instrument_id, []))

    def relationship_graph(self, *, include_data_records: bool = True) -> RelationshipGraph:
        """Build a deterministic factual relationship graph over indexed records."""
        return build_relationship_graph(self.records, include_data_records=include_data_records)
