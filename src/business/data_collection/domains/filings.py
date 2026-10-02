from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from data_collection.domains.models import Provenance


class Filing(BaseModel):
    """Canonical filing/catalog record.

    A Filing describes an information-disclosure event and may point to one or
    more machine-readable or human-readable assets (XBRL, PDF, ZIP, etc.).
    """

    model_config = ConfigDict(extra="allow")

    filing_id: str
    instrument_id: str | None = None
    symbol: str | None = None
    company_name: str | None = None
    filing_type: str
    category: str | None = None
    subcategory: str | None = None
    period_end: date | None = None
    period_start: date | None = None
    financial_year: str | None = None
    statement_type: str | None = None
    submission_type: str | None = None
    audited: bool | None = None
    published_at: datetime | None = None
    received_at: datetime | None = None
    revised_at: datetime | None = None
    revision_remarks: str | None = None
    details_url: str | None = None
    assets: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance


class DocumentAsset(BaseModel):
    """A retrievable artifact attached to or representing a filing."""

    model_config = ConfigDict(extra="allow")

    asset_id: str
    filing_id: str | None = None
    instrument_id: str | None = None
    document_type: Literal["pdf", "xbrl_xml", "xlsx", "csv", "zip", "html", "text", "unknown"] = "unknown"
    title: str | None = None
    url: str
    mime_type: str | None = None
    byte_size: int | None = None
    sha256: str | None = None
    local_path: str | None = None
    text_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance


class XBRLFact(BaseModel):
    """A loss-minimizing representation of one XBRL fact.

    We deliberately retain the concept name, context/unit references, raw value,
    and period metadata instead of mapping everything immediately to a fixed
    financial schema.
    """

    model_config = ConfigDict(extra="allow")

    filing_id: str | None = None
    instrument_id: str | None = None
    concept: str
    label: str | None = None
    value: Any = None
    context_ref: str | None = None
    unit_ref: str | None = None
    decimals: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    instant: date | None = None
    dimensions: dict[str, str] = Field(default_factory=dict)
    raw_xml: str | None = None
    provenance: Provenance
