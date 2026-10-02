from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from data_collection.collection.results import CollectionResult, RawPayload
from data_collection.domains.models import Instrument, Provenance
from data_collection.domains.regulatory import RegulatoryDocument, RegulatoryItem
from data_collection.providers.sebi import SEBIProvider


def _norm_name(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = " ".join(str(value).split())
    return text or None


def _stable_id(category: str, title: str, published_at: Any, detail_url: str | None) -> str:
    material = f"sebi|{category}|{title}|{published_at}|{detail_url}"
    return f"sebi:{sha256(material.encode('utf-8')).hexdigest()[:32]}"


def normalize_regulatory_item(
    row: dict[str, Any],
    *,
    source_category: str,
    retrieved_at: datetime,
    instrument: Instrument | None = None,
    detail: dict[str, Any] | None = None,
) -> tuple[RegulatoryItem, list[RegulatoryDocument]]:
    detail = detail or {}
    regulatory_id = _stable_id(source_category, str(row.get("title", "")), row.get("published_at"), row.get("detail_url"))
    document_urls = [x["url"] for x in detail.get("document_links", []) if x.get("url")]
    links = list(dict.fromkeys([*row.get("links", []), *document_urls]))

    item = RegulatoryItem(
        regulatory_id=regulatory_id,
        category=source_category,
        subcategory=None,
        title=str(row.get("title") or detail.get("title") or "").strip(),
        published_at=row.get("published_at"),
        detail_url=row.get("detail_url"),
        document_urls=document_urls,
        entity_names=[] if instrument is None else ([instrument.name] if instrument.name else []),
        instrument_ids=[] if instrument is None else [instrument.instrument_id],
        metadata={
            "date_text": row.get("date_text"),
            "reference_number": row.get("reference_number"),
            "listing_cells": row.get("cells", []),
            "listing_links": links,
            "detail_text": detail.get("text"),
        },
        provenance=Provenance(
            source="sebi",
            source_type="regulator",
            source_dataset=source_category,
            source_url=row.get("detail_url"),
            retrieved_at=retrieved_at,
            published_at=row.get("published_at"),
        ),
    )

    docs: list[RegulatoryDocument] = []
    for link in document_urls:
        did = f"sebi:{sha256(link.encode('utf-8')).hexdigest()[:32]}"
        docs.append(RegulatoryDocument(
            document_id=did,
            regulatory_id=regulatory_id,
            title=item.title,
            url=link,
            metadata={"source_category": source_category},
            provenance=Provenance(
                source="sebi",
                source_type="regulator",
                source_dataset=f"{source_category}:document",
                source_url=link,
                retrieved_at=retrieved_at,
            ),
        ))
    return item, docs


class RegulatoryCollector:
    """High-level SEBI regulatory collection.

    Collection defaults to listing metadata. Detail-page crawling is explicit,
    because it can multiply requests substantially. Downloads remain separate.
    """

    domain = "regulatory"

    def __init__(self, *, sebi: SEBIProvider | None = None):
        self.sebi = sebi

    def listing(
        self,
        category: str,
        *,
        max_pages: int = 1,
        instrument: Instrument | None = None,
        fetch_details: bool = False,
    ) -> CollectionResult[RegulatoryItem]:
        result: CollectionResult[RegulatoryItem] = CollectionResult(domain=self.domain)
        if self.sebi is None:
            result.errors.append({"source": "sebi", "error": "provider is not configured"})
            return result
        now = datetime.now(timezone.utc)
        try:
            rows, requests = self.sebi.listing(category, max_pages=max_pages)
            for request in requests:
                result.raw_payloads.append(RawPayload(
                    source="sebi", domain=self.domain, retrieved_at=now,
                    payload={"request_meta": request, "category": category},
                    request={"category": category, "url": request.get("url")},
                ))
            for row in rows:
                detail = None
                if fetch_details and row.get("detail_url"):
                    try:
                        detail, detail_meta = self.sebi.detail(row["detail_url"])
                        result.raw_payloads.append(RawPayload(
                            source="sebi", domain=self.domain, retrieved_at=now,
                            payload=detail,
                            request={"category": category, "detail_url": row["detail_url"], "meta": detail_meta},
                        ))
                    except Exception as exc:
                        result.errors.append({"source": "sebi", "detail_url": row.get("detail_url"), "error": str(exc)})
                item, _docs = normalize_regulatory_item(row, source_category=category, retrieved_at=now, instrument=instrument, detail=detail)
                result.records.append(item)
        except Exception as exc:
            result.errors.append({"source": "sebi", "category": category, "error": str(exc)})
        return result

    def document_asset(self, url: str, *, regulatory_id: str | None = None) -> tuple[bytes, RegulatoryDocument] | None:
        if self.sebi is None:
            return None
        body, meta = self.sebi.download(url)
        now = datetime.now(timezone.utc)
        document = RegulatoryDocument(
            document_id=f"sebi:{meta['sha256']}",
            regulatory_id=regulatory_id,
            url=meta["url"],
            mime_type=meta.get("content_type"),
            content_hash=meta["sha256"],
            byte_size=meta["byte_size"],
            provenance=Provenance(
                source="sebi",
                source_type="regulator",
                source_dataset="regulatory_document",
                source_url=meta["url"],
                retrieved_at=now,
                raw_ref=meta["sha256"],
            ),
        )
        return body, document
