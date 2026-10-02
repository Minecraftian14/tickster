from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from data_collection.domains.models import Provenance


class RegulatoryItem(BaseModel):
    """Canonical SEBI/regulatory publication or enforcement record.

    This model is intentionally generic. SEBI publishes several families of
    records—regulations, circulars, master circulars, orders, informal guidance,
    press releases, reports and related notices. We preserve the publisher's
    category/subcategory and raw metadata instead of forcing all of them into a
    single semantic schema during collection.
    """

    model_config = ConfigDict(extra="allow")

    regulatory_id: str
    category: str
    subcategory: str | None = None
    title: str
    published_at: datetime | None = None
    detail_url: str | None = None
    document_urls: list[str] = Field(default_factory=list)
    entity_names: list[str] = Field(default_factory=list)
    instrument_ids: list[str] = Field(default_factory=list)
    department: str | None = None
    section: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance


class RegulatoryDocument(BaseModel):
    """A retrievable document attached to a regulatory item."""

    model_config = ConfigDict(extra="allow")

    document_id: str
    regulatory_id: str | None = None
    title: str | None = None
    url: str
    mime_type: str | None = None
    content_hash: str | None = None
    byte_size: int | None = None
    local_path: str | None = None
    text_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance
