from __future__ import annotations

from typing import Any, Protocol

from .context import EnrichmentContext
from ..models import EnrichmentResult


class Enricher(Protocol):
    """Protocol implemented by every enrichment component."""

    name: str
    version: str
    requires: frozenset[str]
    provides: frozenset[str]

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        ...


class ComputationBackend(Protocol):
    """Optional calculation engine adapter used behind enrichment components."""

    name: str
    version: str
    capabilities: frozenset[str]

    def supports(self, capability: str) -> bool:
        ...

    def available(self) -> bool:
        ...

    def compute(self, capability: str, data: Any, **kwargs: Any) -> Any:
        ...
