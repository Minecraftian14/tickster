"""Canonical foundation for the Indian equity information corpus."""

from ._version import __version__

from .contract import (
    COLLECTION_PACKAGE, CONTRACT_VERSION, MIN_COLLECTION_VERSION, PACKAGE_NAME, PACKAGE_VERSION, STORAGE_FORMAT_VERSION,
    ContractManifest, ContractViolation, assert_evidence_chain, contract_manifest, validate_evidence_chain, validate_store_layout,
)
from .identity import IdentityAmbiguityError, IdentityRegistry, Resolution, build_alias_index, build_identity, merge_identities, resolve_instrument_id
from .ingest import ingest_collection_results
from .models import (
    CanonicalBundle,
    CanonicalRecord,
    CompanyTimeline,
    DataQuality,
    IdentityAlias,
    InstrumentIdentity,
    QualityFinding,
    QualityReport,
    RawArtifact,
    ReconciliationDecision,
    ReconciliationFinding,
    GraphNode,
    RelationshipGraph,
    ReconciliationResult,
    Relationship,
    SourceObservation,
    TemporalEnvelope,
    TimelineEntry,
)
from .persistence import FoundationStore, canonical_record_id, canonicalize_record, observation_set_for_records, persist_canonical_records, persist_raw_payloads
from .query import build_temporal_index, documents_available_at, events_between, records_visible_at, what_was_known_at
from .quality import build_quality_report, check_duplicates, check_identity_ambiguities, check_invalid_numeric_values, check_missing_fields, check_reconciliation_findings, check_schema_drift, check_stale_sources, check_timestamp_anomalies, schema_signature
from .reconciliation import choose_canonical_observation, observations_from_record, reconcile_numeric, reconcile_numeric_with_decisions
from .relationships import RelationshipIndex, build_relationship_graph, index_relationships, make_relationship
from .storage import load_raw_artifact, read_jsonl, write_canonical_indexes, write_canonical_records, write_canonical_jsonl, write_manifest, write_raw_artifact, write_raw_manifest, write_source_observations
from .temporal import is_visible_at, point_in_time_filter, temporal_envelope
from .temporal_index import TemporalIndex
from .timeline import build_company_timeline

__all__ = [
    "__version__", "PACKAGE_NAME", "CONTRACT_VERSION", "PACKAGE_VERSION", "COLLECTION_PACKAGE", "MIN_COLLECTION_VERSION", "STORAGE_FORMAT_VERSION", "ContractManifest", "ContractViolation", "contract_manifest", "validate_evidence_chain", "assert_evidence_chain", "validate_store_layout", "IdentityAmbiguityError", "IdentityRegistry", "Resolution", "TemporalIndex",
    "CanonicalBundle", "CanonicalRecord", "CompanyTimeline", "DataQuality", "IdentityAlias",
    "InstrumentIdentity", "QualityFinding", "QualityReport", "RawArtifact", "ReconciliationDecision", "GraphNode", "RelationshipGraph",
    "ReconciliationFinding", "ReconciliationResult", "Relationship", "SourceObservation",
    "TemporalEnvelope", "TimelineEntry", "build_alias_index", "build_company_timeline", "build_identity",
    "FoundationStore", "canonical_record_id", "canonicalize_record", "observation_set_for_records", "index_relationships", "RelationshipIndex", "build_relationship_graph",
    "ingest_collection_results", "is_visible_at", "build_temporal_index", "documents_available_at", "events_between",
    "what_was_known_at", "load_raw_artifact", "make_relationship", "merge_identities", "observations_from_record",
    "persist_canonical_records", "persist_raw_payloads", "point_in_time_filter", "read_jsonl", "choose_canonical_observation",
    "reconcile_numeric", "reconcile_numeric_with_decisions", "records_visible_at", "resolve_instrument_id", "temporal_envelope",
    "write_canonical_indexes", "write_canonical_records", "write_canonical_jsonl", "write_manifest", "write_raw_artifact", "write_raw_manifest",
    "write_source_observations", "build_quality_report", "check_duplicates", "check_identity_ambiguities",
    "check_invalid_numeric_values", "check_missing_fields", "check_reconciliation_findings", "check_schema_drift", "check_stale_sources",
    "check_timestamp_anomalies", "schema_signature",
]
