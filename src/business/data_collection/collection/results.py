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


@dataclass
class CollectionResult(Generic[T]):
    """A domain collection result containing canonical records and raw evidence."""

    domain: str
    records: list[T] = field(default_factory=list)
    raw_payloads: list[RawPayload] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def extend(self, other: "CollectionResult[T]") -> None:
        self.records.extend(other.records)
        self.raw_payloads.extend(other.raw_payloads)
        self.errors.extend(other.errors)
