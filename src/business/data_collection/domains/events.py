from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from data_collection.domains.models import Provenance


class CompanyEvent(BaseModel):
    """Canonical company-level event/disclosure representation."""

    model_config = ConfigDict(extra="allow")

    event_id: str
    instrument_id: str | None = None
    event_type: str
    subject: str | None = None
    event_date: date | datetime | None = None
    announcement_date: date | datetime | None = None
    description: str | None = None
    url: str | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance
