from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from ._version import __version__
from .models import CanonicalRecord, RawArtifact, SourceObservation
from .storage import read_jsonl

PACKAGE_NAME = "indian-equity-data-foundation"
CONTRACT_VERSION = "1.0"
PACKAGE_VERSION = __version__
COLLECTION_PACKAGE = "indian-equity-data-platform"
MIN_COLLECTION_VERSION = "1.1.0"
STORAGE_FORMAT_VERSION = "1"

STABLE_CLASSES = (
    "IdentityAmbiguityError",
    "Resolution",
    "IdentityRegistry",
    "TemporalIndex",
    "RelationshipIndex",
    "FoundationStore",
    "ContractManifest",
    "ContractViolation",
)

STABLE_MODELS = (
    "IdentityAlias",
    "InstrumentIdentity",
    "TemporalEnvelope",
    "RawArtifact",
    "SourceObservation",
    "CanonicalRecord",
    "ReconciliationFinding",
    "ReconciliationDecision",
    "ReconciliationResult",
    "GraphNode",
    "Relationship",
    "RelationshipGraph",
    "DataQuality",
    "QualityFinding",
    "QualityReport",
    "TimelineEntry",
    "CompanyTimeline",
    "CanonicalBundle",
)

STABLE_FUNCTIONS = (
    "build_identity",
    "merge_identities",
    "resolve_instrument_id",
    "ingest_collection_results",
    "canonical_record_id",
    "canonicalize_record",
    "persist_canonical_records",
    "persist_raw_payloads",
    "observation_set_for_records",
    "build_quality_report",
    "choose_canonical_observation",
    "observations_from_record",
    "reconcile_numeric",
    "reconcile_numeric_with_decisions",
    "build_relationship_graph",
    "make_relationship",
    "index_relationships",
    "build_company_timeline",
    "build_temporal_index",
    "records_visible_at",
    "what_was_known_at",
    "events_between",
    "documents_available_at",
    "point_in_time_filter",
    "temporal_envelope",
    "is_visible_at",
    "load_raw_artifact",
    "read_jsonl",
    "write_raw_artifact",
    "write_raw_manifest",
    "write_canonical_records",
    "write_source_observations",
    "write_canonical_indexes",
    "write_canonical_jsonl",
    "write_manifest",
    "check_duplicates",
    "check_identity_ambiguities",
    "check_invalid_numeric_values",
    "check_missing_fields",
    "check_reconciliation_findings",
    "check_schema_drift",
    "check_stale_sources",
    "check_timestamp_anomalies",
    "schema_signature",
)

STABLE_STORE_METHODS = (
    "persist_raw_payloads",
    "persist_records",
    "persist_collection_result",
    "persist_collection_results",
    "load_canonical_records",
    "load_source_observations",
    "load_raw_artifacts",
    "load_raw_artifact",
    "load_bundle",
)

@dataclass(frozen=True)
class ContractManifest:
    package_name: str = PACKAGE_NAME
    contract_version: str = CONTRACT_VERSION
    package_version: str = PACKAGE_VERSION
    collection_package: str = COLLECTION_PACKAGE
    min_collection_version: str = MIN_COLLECTION_VERSION
    storage_format_version: str = STORAGE_FORMAT_VERSION
    stable_classes: tuple[str, ...] = STABLE_CLASSES
    stable_models: tuple[str, ...] = STABLE_MODELS
    stable_functions: tuple[str, ...] = STABLE_FUNCTIONS
    stable_store_methods: tuple[str, ...] = STABLE_STORE_METHODS

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ContractViolation(ValueError):
    """Raised when persisted foundation evidence violates the stable contract."""


def contract_manifest() -> ContractManifest:
    return ContractManifest()


def validate_evidence_chain(
    canonical_records: Iterable[CanonicalRecord],
    source_observations: Iterable[SourceObservation],
    raw_artifacts: Iterable[RawArtifact],
) -> list[str]:
    """Validate canonical → observation → raw-artifact references.

    The validator reports all violations so callers can present a useful integrity
    report. It does not inspect or modify the raw bytes themselves.
    """
    canonical = list(canonical_records)
    observations = {item.observation_id: item for item in source_observations}
    artifacts = {item.artifact_id: item for item in raw_artifacts}
    violations: list[str] = []

    for record in canonical:
        for observation_id in record.source_observation_ids:
            observation = observations.get(observation_id)
            if observation is None:
                violations.append(
                    f"canonical record {record.record_id} references missing observation {observation_id}"
                )
                continue
            if observation.canonical_record_id != record.record_id:
                violations.append(
                    f"observation {observation_id} points to {observation.canonical_record_id!r}, "
                    f"expected {record.record_id!r}"
                )

    for observation in observations.values():
        if observation.raw_ref and observation.raw_ref not in artifacts:
            violations.append(
                f"observation {observation.observation_id} references missing raw artifact {observation.raw_ref}"
            )

    return violations


def assert_evidence_chain(
    canonical_records: Iterable[CanonicalRecord],
    source_observations: Iterable[SourceObservation],
    raw_artifacts: Iterable[RawArtifact],
) -> None:
    violations = validate_evidence_chain(canonical_records, source_observations, raw_artifacts)
    if violations:
        raise ContractViolation("; ".join(violations))


def validate_store_layout(root: str | Path) -> list[str]:
    """Validate the metadata/index portion of a persisted foundation store."""
    root = Path(root)
    violations: list[str] = []
    manifest_path = root / "indexes" / "foundation_manifest.json"
    if not manifest_path.exists():
        violations.append("missing foundation manifest")
    else:
        try:
            import json
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("contract_version") != CONTRACT_VERSION:
                violations.append(
                    f"store contract_version={manifest.get('contract_version')!r}; expected {CONTRACT_VERSION!r}"
                )
            if manifest.get("storage_format_version") != STORAGE_FORMAT_VERSION:
                violations.append(
                    f"store storage_format_version={manifest.get('storage_format_version')!r}; expected {STORAGE_FORMAT_VERSION!r}"
                )
        except Exception as exc:
            violations.append(f"invalid foundation manifest: {exc}")

    raw_rows = read_jsonl(root / "indexes" / "raw_artifacts.jsonl")
    raw_artifacts = [RawArtifact.model_validate(row) for row in raw_rows]
    obs_rows = read_jsonl(root / "canonical" / "_source_observations" / "records.jsonl")
    observations = [SourceObservation.model_validate(row) for row in obs_rows]
    canonical_records: list[CanonicalRecord] = []
    canonical_root = root / "canonical"
    if canonical_root.exists():
        for path in canonical_root.glob("*/records.jsonl"):
            if path.parent.name == "_source_observations":
                continue
            canonical_records.extend(CanonicalRecord.model_validate(row) for row in read_jsonl(path))
    violations.extend(validate_evidence_chain(canonical_records, observations, raw_artifacts))
    return violations
