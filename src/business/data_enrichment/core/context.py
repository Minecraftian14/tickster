from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from data_foundation.temporal import is_visible_at, temporal_envelope
from ..models import DerivationLineage


class EnrichmentContext:
    """Read-only working set for enrichers.

    The context contains canonical records and optional lookup metadata. It never
    mutates foundation records and delegates point-in-time semantics to
    data_foundation rather than inventing a second temporal model.
    """

    def __init__(
        self,
        records: Iterable[Any],
        *,
        as_of: datetime | None = None,
        instrument_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        source_observations: Iterable[Any] = (),
    ) -> None:
        self.records = tuple(records)
        self.as_of = as_of
        self.instrument_id = instrument_id
        self.metadata = dict(metadata or {})
        self.source_observations = tuple(source_observations)
        self._observations_by_id = {
            str(getattr(obs, "observation_id")): obs
            for obs in self.source_observations
            if getattr(obs, "observation_id", None)
        }

    def visible_records(self, *, strict: bool = True) -> list[Any]:
        if self.as_of is None:
            return list(self.records)
        return [record for record in self.records if is_visible_at(record, self.as_of, strict=strict)]

    def records_for_instrument(self, *, visible_only: bool = True, strict: bool = True) -> list[Any]:
        records = self.visible_records(strict=strict) if visible_only else list(self.records)
        if self.instrument_id is None:
            return records
        result: list[Any] = []
        for record in records:
            rid = getattr(record, "instrument_id", None)
            payload = getattr(record, "payload", None)
            if isinstance(payload, dict):
                rid = rid or payload.get("instrument_id")
            rids = getattr(record, "instrument_ids", None)
            if rids is None and isinstance(payload, dict):
                rids = payload.get("instrument_ids", [])
            if rid == self.instrument_id or self.instrument_id in (rids or []):
                result.append(record)
        return result

    @staticmethod
    def payload(record: Any) -> dict[str, Any]:
        payload = getattr(record, "payload", None)
        if isinstance(payload, dict):
            return payload
        if hasattr(record, "model_dump"):
            dumped = record.model_dump(mode="json")
            return dumped if isinstance(dumped, dict) else {}
        return {}

    @staticmethod
    def record_id(record: Any) -> str | None:
        value = getattr(record, "record_id", None)
        if value:
            return str(value)
        for key in ("event_id", "filing_id", "document_id", "news_id", "observation_id", "relationship_id"):
            value = getattr(record, key, None)
            if value:
                return str(value)
        return None

    @staticmethod
    def instrument_id(record: Any) -> str | None:
        value = getattr(record, "instrument_id", None)
        if value:
            return str(value)
        payload = EnrichmentContext.payload(record)
        value = payload.get("instrument_id")
        return str(value) if value else None

    @staticmethod
    def temporal(record: Any):
        return temporal_envelope(record)

    def lineage_for_records(
        self,
        records: Iterable[Any],
        *,
        algorithm: str,
        algorithm_version: str,
        parameters: dict[str, Any] | None = None,
        calculated_at: datetime | None = None,
    ) -> DerivationLineage:
        """Construct lineage from canonical records and supplied foundation observations."""
        records = list(records)
        record_ids = [rid for record in records if (rid := self.record_id(record))]
        observation_ids: list[str] = []
        raw_ids: list[str] = []
        for record in records:
            ids = getattr(record, "source_observation_ids", None)
            payload = getattr(record, "payload", None)
            if ids is None and isinstance(payload, dict):
                ids = payload.get("source_observation_ids", [])
            for observation_id in ids or []:
                oid = str(observation_id)
                if oid not in observation_ids:
                    observation_ids.append(oid)
                observation = self._observations_by_id.get(oid)
                raw_ref = getattr(observation, "raw_ref", None) if observation is not None else None
                if raw_ref and str(raw_ref) not in raw_ids:
                    raw_ids.append(str(raw_ref))
        return DerivationLineage(
            source_record_ids=record_ids,
            source_observation_ids=observation_ids,
            raw_artifact_ids=raw_ids,
            algorithm=algorithm,
            algorithm_version=algorithm_version,
            parameters=dict(parameters or {}),
            calculated_at=calculated_at or datetime.now(timezone.utc),
        )
