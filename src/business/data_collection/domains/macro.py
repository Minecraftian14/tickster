from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from data_collection.domains.models import Provenance


class MacroSeries(BaseModel):
    """Describes a macroeconomic series without prescribing a provider taxonomy."""

    model_config = ConfigDict(extra="allow")

    series_id: str
    name: str
    description: str | None = None
    frequency: str | None = None
    unit: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MacroRelease(BaseModel):
    """A release/event associated with a macro series or dataset."""

    model_config = ConfigDict(extra="allow")

    release_id: str
    title: str
    published_at: date | None = None
    reference_period: str | None = None
    source: str | None = None
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance
