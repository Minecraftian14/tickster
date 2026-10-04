from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class RawPayload:
    source: str
    domain: str
    retrieved_at: datetime
    payload: Any
    request: dict[str, Any] = field(default_factory=dict)
    source_url: str | None = None
    content_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def stable_id(self) -> str:
        from data_collection.storage.raw import raw_payload_id
        return raw_payload_id(self)


@dataclass
class CollectionResult(Generic[T]):
    """A domain collection result containing canonical records, raw evidence and diagnostic issues."""

    domain: str
    records: list[T] = field(default_factory=list)
    raw_payloads: list[RawPayload] = field(default_factory=list)
    related_records: list[Any] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_error(self, *, source: str, operation: str, exc: Exception, **context: Any) -> None:
        self.errors.append({
            "source": source,
            "operation": operation,
            "error": str(exc),
            "error_type": type(exc).__name__,
            **context,
        })

    def add_issue(self, *, source: str, operation: str, message: str, **context: Any) -> None:
        self.issues.append({
            "source": source,
            "operation": operation,
            "message": message,
            **context,
        })

    def persist_raw(self, root: str) -> list:
        """Persist this result's raw evidence and return written artifact paths."""
        from data_collection.storage.raw import write_raw_payloads
        return write_raw_payloads(self.raw_payloads, root)

    def extend(self, other: "CollectionResult[T]") -> None:
        self.records.extend(other.records)
        self.raw_payloads.extend(other.raw_payloads)
        self.related_records.extend(other.related_records)
        self.errors.extend(other.errors)
        self.issues.extend(other.issues)

    def export_to_raw(self, export_field, *args: str):
        return {
            "domain": self.domain,
            "records": export_field(self.records),
            # "raw_payloads": export_field(self.raw_payloads),
            "related_records": export_field(self.related_records),
        }
