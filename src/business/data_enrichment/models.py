from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DerivationLineage(BaseModel):
    """Evidence and calculation metadata for derived outputs."""

    model_config = ConfigDict(extra="allow")

    source_record_ids: list[str] = Field(default_factory=list)
    source_observation_ids: list[str] = Field(default_factory=list)
    raw_artifact_ids: list[str] = Field(default_factory=list)
    algorithm: str
    algorithm_version: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    calculated_at: datetime


class DerivedObservation(BaseModel):
    """One derived value at one point in time."""

    model_config = ConfigDict(extra="allow")

    derived_id: str
    instrument_id: str | None = None
    metric: str
    value: Any = None
    unit: str | None = None
    observed_at: datetime | None = None
    available_at: datetime | None = None
    calculation_basis: Literal["deterministic"] = "deterministic"
    lineage: DerivationLineage
    metadata: dict[str, Any] = Field(default_factory=dict)


class DerivedSeriesPoint(BaseModel):
    timestamp: datetime
    value: Any = None
    source_record_ids: list[str] = Field(default_factory=list)
    available_at: datetime | None = None


class DerivedSeries(BaseModel):
    """A derived time series retaining point-level lineage."""

    model_config = ConfigDict(extra="allow")

    derived_id: str
    instrument_id: str | None = None
    metric: str
    unit: str | None = None
    points: list[DerivedSeriesPoint] = Field(default_factory=list)
    calculation_basis: Literal["deterministic"] = "deterministic"
    lineage: DerivationLineage
    metadata: dict[str, Any] = Field(default_factory=dict)


class DerivedSummary(BaseModel):
    """A compact descriptive summary derived from canonical records."""

    model_config = ConfigDict(extra="allow")

    derived_id: str
    instrument_id: str | None = None
    summary_type: str
    values: dict[str, Any] = Field(default_factory=dict)
    calculation_basis: Literal["deterministic"] = "deterministic"
    lineage: DerivationLineage
    metadata: dict[str, Any] = Field(default_factory=dict)


class EnrichmentIssue(BaseModel):
    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    metric: str | None = None
    record_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EnrichmentResult(BaseModel):
    """Outputs of one enrichment run."""

    enricher: str
    enricher_version: str
    observations: list[DerivedObservation] = Field(default_factory=list)
    series: list[DerivedSeries] = Field(default_factory=list)
    summaries: list[DerivedSummary] = Field(default_factory=list)
    issues: list[EnrichmentIssue] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def extend(self, other: "EnrichmentResult") -> None:
        self.observations.extend(other.observations)
        self.series.extend(other.series)
        self.summaries.extend(other.summaries)
        self.issues.extend(other.issues)
