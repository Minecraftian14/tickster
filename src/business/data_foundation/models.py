from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class IdentityAlias(BaseModel):
    """A provider/source-specific identifier for one canonical instrument."""

    model_config = ConfigDict(extra="allow")

    alias_type: str
    value: str
    source: str | None = None
    instrument_id: str
    valid_from: date | datetime | None = None
    valid_to: date | datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class InstrumentIdentity(BaseModel):
    """Canonical identity and aliases assembled from collected Instrument records."""

    model_config = ConfigDict(extra="allow")

    instrument_id: str
    isin: str | None = None
    symbol: str | None = None
    exchange: str | None = None
    name: str | None = None
    active: bool | None = None
    aliases: list[IdentityAlias] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TemporalEnvelope(BaseModel):
    """The time semantics needed to reconstruct point-in-time knowledge."""

    model_config = ConfigDict(extra="allow")

    event_time: datetime | date | None = None
    effective_time: datetime | date | None = None
    published_at: datetime | date | None = None
    observed_at: datetime | date | None = None
    retrieved_at: datetime | None = None
    period_start: date | datetime | None = None
    period_end: date | datetime | None = None
    available_at: datetime | None = None
    availability_basis: Literal["published", "observed", "received", "effective", "retrieved", "unknown"] = "unknown"
    availability_precision: Literal["instant", "date", "unknown"] = "unknown"


class RawArtifact(BaseModel):
    """Immutable source artifact stored by content hash."""

    model_config = ConfigDict(extra="allow")

    contract_version: str = "1.0"
    artifact_id: str
    source: str
    domain: str
    media_type: str = "application/octet-stream"
    content_hash: str
    size_bytes: int
    storage_path: str
    retrieved_at: datetime
    source_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceObservation(BaseModel):
    """A source-specific observation preserved for reconciliation."""

    model_config = ConfigDict(extra="allow")

    contract_version: str = "1.0"
    observation_id: str
    entity_key: str
    field: str
    value: Any = None
    source: str
    source_type: str | None = None
    observed_at: datetime | date | None = None
    published_at: datetime | date | None = None
    retrieved_at: datetime | None = None
    raw_ref: str | None = None
    canonical_record_id: str | None = None
    unit: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalRecord(BaseModel):
    """Persistable canonical record with backward evidence references."""

    model_config = ConfigDict(extra="allow")

    contract_version: str = "1.0"
    record_id: str
    domain: str
    record_type: str
    payload: dict[str, Any]
    source_observation_ids: list[str] = Field(default_factory=list)
    quality_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


ReconciliationStatus = Literal[
    "agree",
    "minor_difference",
    "conflicting",
    "missing",
    "unresolvable",
]


class ReconciliationFinding(BaseModel):
    """Outcome of comparing observations for one entity/field."""

    model_config = ConfigDict(extra="allow")

    finding_id: str
    entity_key: str
    field: str
    status: ReconciliationStatus
    observations: list[str] = Field(default_factory=list)
    message: str
    spread: float | None = None
    relative_spread: float | None = None
    missing_sources: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReconciliationDecision(BaseModel):
    """Explicit, deterministic choice of a canonical observation when possible."""

    model_config = ConfigDict(extra="allow")

    decision_id: str
    finding_id: str
    selected_observation_id: str | None = None
    selected_value: Any = None
    status: ReconciliationStatus
    reason: str
    policy: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReconciliationResult(BaseModel):
    """A reconciliation finding together with its optional canonical decision."""

    model_config = ConfigDict(extra="allow")

    finding: ReconciliationFinding
    decision: ReconciliationDecision


class GraphNode(BaseModel):
    """Typed node used by the deterministic foundation relationship graph."""

    model_config = ConfigDict(extra="allow")

    node_id: str
    node_type: str
    label: str
    instrument_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RelationshipGraph(BaseModel):
    """Deterministic graph view over canonical entities and factual relationships."""

    model_config = ConfigDict(extra="allow")

    nodes: list[GraphNode] = Field(default_factory=list)
    relationships: list["Relationship"] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Relationship(BaseModel):
    """Directed, provenance-carrying relationship between canonical entities."""

    model_config = ConfigDict(extra="allow")

    relationship_id: str
    subject_id: str
    predicate: str
    object_id: str
    valid_from: datetime | date | None = None
    valid_to: datetime | date | None = None
    asserted_at: datetime | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataQuality(BaseModel):
    """Structured value-quality status; a null value is not itself an explanation."""

    status: Literal[
        "present",
        "missing",
        "unknown",
        "not_applicable",
        "not_provided",
        "parse_failed",
        "source_unavailable",
        "conflicting",
        "invalid",
    ]
    message: str | None = None
    source: str | None = None
    field: str | None = None
    raw_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


QualityCategory = Literal[
    "missing_field",
    "stale_source",
    "duplicate",
    "timestamp_anomaly",
    "schema_drift",
    "identity_ambiguity",
    "invalid_value",
    "conflict",
]

QualitySeverity = Literal["info", "warning", "error"]


class QualityFinding(BaseModel):
    """A machine-readable quality issue detected by the foundation quality engine."""

    model_config = ConfigDict(extra="allow")

    finding_id: str
    category: QualityCategory
    severity: QualitySeverity
    message: str
    entity_key: str | None = None
    field: str | None = None
    source: str | None = None
    record_ids: list[str] = Field(default_factory=list)
    observation_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class QualityReport(BaseModel):
    """Aggregate quality results for a batch of records/observations/artifacts."""

    model_config = ConfigDict(extra="allow")

    generated_at: datetime
    findings: list[QualityFinding] = Field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for finding in self.findings:
            out[finding.category] = out.get(finding.category, 0) + 1
        return out

    @property
    def severity_summary(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for finding in self.findings:
            out[finding.severity] = out.get(finding.severity, 0) + 1
        return out

    @property
    def passed(self) -> bool:
        return not any(item.severity == "error" for item in self.findings)


class TimelineEntry(BaseModel):
    """A normalized timeline entry pointing back to a collected record."""

    model_config = ConfigDict(extra="allow")

    entry_id: str
    instrument_id: str
    entry_type: str
    title: str
    event_time: datetime | date | None = None
    available_at: datetime | None = None
    source_record_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompanyTimeline(BaseModel):
    """Chronological information history for one canonical instrument."""

    model_config = ConfigDict(extra="allow")

    instrument_id: str
    entries: list[TimelineEntry] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalBundle(BaseModel):
    """A typed container for canonical records plus foundation indexes."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    contract_version: str = "1.0"
    instruments: list[Any] = Field(default_factory=list)
    records: list[Any] = Field(default_factory=list)
    canonical_records: list[CanonicalRecord] = Field(default_factory=list)
    source_observations: list[SourceObservation] = Field(default_factory=list)
    raw_artifacts: list[RawArtifact] = Field(default_factory=list)
    raw_refs: list[str] = Field(default_factory=list)
    identities: list[InstrumentIdentity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    quality: list[DataQuality] = Field(default_factory=list)
    quality_findings: list[QualityFinding] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
