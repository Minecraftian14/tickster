from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Iterable

from pydantic import BaseModel

from .models import CanonicalRecord, RawArtifact, SourceObservation
from .reconciliation import observations_from_record
from .storage import (
    read_jsonl,
    write_canonical_indexes,
    write_canonical_records,
    write_raw_artifact,
    write_raw_manifest,
    write_source_observations,
    write_manifest,
)


# Canonical identity is deliberately type-aware. A single ``instrument_id`` is
# not sufficient for time-series observations: two PriceBars for the same
# instrument must remain distinct records. The same principle applies to
# periodic statements, index observations, and other repeated facts.
_NATURAL_KEY_FIELDS: dict[str, tuple[str, ...]] = {
    "Instrument": ("instrument_id",),
    "PriceBar": ("instrument_id", "timeframe", "timestamp"),
    "MarketQuote": ("instrument_id", "timestamp"),
    "CorporateAction": (
        "instrument_id",
        "action_type",
        "announcement_date",
        "ex_date",
        "record_date",
        "ratio",
        "amount",
    ),
    "FundamentalSnapshot": (
        "instrument_id",
        "period_end",
        "period_type",
        "statement_type",
        "statement_name",
        "fiscal_year",
    ),
    "CompanyPeer": ("instrument_id", "peer_instrument_key", "peer_isin", "peer_name"),
    "ShareholdingSnapshot": ("instrument_id", "period_end"),
    "CompanyDocument": ("document_id",),
    "NewsItem": ("news_id",),
    "MacroObservation": ("series_id", "observation_date"),
    "CompanyEvent": ("event_id",),
    "Filing": ("filing_id",),
    "DocumentAsset": ("asset_id",),
    "XBRLFact": (
        "filing_id",
        "instrument_id",
        "concept",
        "context_ref",
        "unit_ref",
        "period_start",
        "period_end",
        "instant",
        "dimensions",
    ),
    "IndexSnapshot": ("index_id", "timestamp"),
    "IndexPriceBar": ("index_id", "timestamp"),
    "IndexValuationSnapshot": ("index_id", "observation_date"),
    "IndexConstituent": ("index_id", "symbol", "effective_date"),
    "SectorClassification": ("instrument_id", "classification_as_of"),
    "InsiderTransaction": ("event_id",),
    "LargeDeal": ("event_id",),
    "RegulatoryItem": ("regulatory_id",),
    "RegulatoryDocument": ("document_id",),
    "MacroSeries": ("series_id",),
    "MacroRelease": ("release_id",),
}


def _record_natural_key(record: Any) -> str:
    record_type = record.__class__.__name__
    if record_type in _NATURAL_KEY_FIELDS:
        parts: list[str] = []
        for key in _NATURAL_KEY_FIELDS[record_type]:
            value = getattr(record, key, None)
            if value is None and isinstance(record, BaseModel):
                value = record.model_dump(mode="python").get(key)
            if value is not None:
                serialized = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
                parts.append(f"{key}={serialized}")
        if parts:
            return f"typed:{record_type}|" + "|".join(parts)

    # Generic fallback for record types that have no explicit identity rule.
    # Exclude collection-only provenance/metadata from the fallback so source
    # retrieval details do not accidentally change canonical identity.
    payload = record.model_dump(mode="json") if isinstance(record, BaseModel) else record
    if isinstance(payload, dict):
        payload = {key: value for key, value in payload.items() if key not in {"provenance", "metadata"}}
    digest = sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()
    return "payload:" + digest


def canonical_record_id(record: Any, *, domain: str) -> str:
    body = f"{domain}|{record.__class__.__name__}|{_record_natural_key(record)}"
    return sha256(body.encode("utf-8")).hexdigest()


def canonicalize_record(record: Any, *, domain: str, source_observation_ids: Iterable[str] = ()) -> CanonicalRecord:
    payload = record.model_dump(mode="json") if isinstance(record, BaseModel) else {"value": record}
    return CanonicalRecord(
        record_id=canonical_record_id(record, domain=domain),
        domain=domain,
        record_type=record.__class__.__name__,
        payload=payload,
        source_observation_ids=list(source_observation_ids),
    )


def persist_canonical_records(
    records: Iterable[Any],
    root: str,
    *,
    domain: str,
    source_observations: Iterable[SourceObservation] = (),
) -> list[CanonicalRecord]:
    """Persist canonical records plus their observation indexes."""
    records = list(records)
    observations = list(source_observations)
    grouped: dict[str, list[str]] = {}
    for observation in observations:
        grouped.setdefault(observation.canonical_record_id or "", []).append(observation.observation_id)

    canonical_records = [
        canonicalize_record(record, domain=domain, source_observation_ids=grouped.get(canonical_record_id(record, domain=domain), []))
        for record in records
    ]
    write_canonical_records(canonical_records, root, domain=domain)
    write_source_observations(observations, root)
    write_canonical_indexes(canonical_records, observations, root)
    return canonical_records


def persist_raw_payloads(raw_payloads: Iterable[Any], root: str) -> list[RawArtifact]:
    """Bridge data_collection.RawPayload objects into foundation raw artifacts."""
    artifacts: list[RawArtifact] = []
    for item in raw_payloads:
        artifact = write_raw_artifact(
            item.payload,
            root,
            source=item.source,
            domain=item.domain,
            retrieved_at=item.retrieved_at,
            media_type=item.content_type or "application/json",
            source_url=item.source_url,
            metadata={"request": item.request, **item.metadata},
            artifact_id=item.stable_id() if hasattr(item, "stable_id") else None,
        )
        artifacts.append(artifact)
    write_raw_manifest(artifacts, root)
    return artifacts


def observation_set_for_records(records: Iterable[Any], *, domain: str | None = None) -> list[SourceObservation]:
    """Build source observations with canonical IDs using one consistent domain."""
    records = list(records)
    observations: list[SourceObservation] = []
    for record in records:
        record_domain = domain or record.__class__.__name__.lower()
        rid = canonical_record_id(record, domain=record_domain)
        extracted = observations_from_record(record)
        for observation in extracted:
            observation.canonical_record_id = rid
        observations.extend(extracted)
    return observations

class FoundationStore:
    """Small file-backed persistence facade for the v0.2 evidence chain.

    The store deliberately uses append-only JSONL for metadata/indexes and
    immutable, content-addressed files for raw bytes. A later version can swap
    the physical storage engine without changing collection or canonical APIs.
    """

    def __init__(self, root: str) -> None:
        from pathlib import Path
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _write_manifest(self) -> None:
        from .contract import contract_manifest
        write_manifest(contract_manifest().as_dict(), self.root)

    def persist_raw_payloads(self, raw_payloads: Iterable[Any]) -> list[RawArtifact]:
        artifacts = persist_raw_payloads(raw_payloads, str(self.root))
        self._write_manifest()
        return artifacts

    def persist_records(self, records: Iterable[Any], *, domain: str) -> tuple[list[CanonicalRecord], list[SourceObservation]]:
        records = list(records)
        observations = observation_set_for_records(records, domain=domain)
        canonical = persist_canonical_records(records, str(self.root), domain=domain, source_observations=observations)
        self._write_manifest()
        return canonical, observations

    def persist_collection_result(self, result: Any) -> dict[str, Any]:
        """Persist a data_collection.CollectionResult without changing the collection package."""
        raw_artifacts = self.persist_raw_payloads(result.raw_payloads)
        records = list(result.records) + list(result.related_records)
        canonical, observations = self.persist_records(records, domain=result.domain)
        return {
            "raw_artifacts": raw_artifacts,
            "canonical_records": canonical,
            "source_observations": observations,
        }

    def persist_collection_results(self, results: Iterable[Any]) -> list[dict[str, Any]]:
        return [self.persist_collection_result(result) for result in results]

    def load_canonical_records(self, *, domain: str | None = None) -> list[CanonicalRecord]:
        """Load persisted canonical envelopes, optionally restricted to one domain."""
        canonical_root = self.root / "canonical"
        paths = [canonical_root / domain / "records.jsonl"] if domain else sorted(
            path for path in canonical_root.glob("*/records.jsonl") if path.parent.name != "_source_observations"
        )
        rows: list[CanonicalRecord] = []
        for path in paths:
            for item in read_jsonl(path):
                rows.append(CanonicalRecord.model_validate(item))
        return rows

    def load_source_observations(self) -> list[SourceObservation]:
        path = self.root / "canonical" / "_source_observations" / "records.jsonl"
        return [SourceObservation.model_validate(item) for item in read_jsonl(path)]

    def load_raw_artifacts(self) -> list[RawArtifact]:
        path = self.root / "indexes" / "raw_artifacts.jsonl"
        return [RawArtifact.model_validate(item) for item in read_jsonl(path)]

    def load_raw_artifact(self, artifact_id: str) -> bytes:
        from .storage import load_raw_artifact
        artifact = next((item for item in self.load_raw_artifacts() if item.artifact_id == artifact_id), None)
        if artifact is None:
            raise KeyError(f"Unknown raw artifact: {artifact_id}")
        return load_raw_artifact(self.root, artifact)

    def load_bundle(self) -> tuple[list[CanonicalRecord], list[SourceObservation], list[RawArtifact]]:
        """Load the persisted evidence layers in canonical → observation → raw order."""
        return self.load_canonical_records(), self.load_source_observations(), self.load_raw_artifacts()

