from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class BackendUnavailableError(RuntimeError):
    """Raised when an optional calculation backend is not installed."""


@dataclass(frozen=True)
class BackendComputation:
    """Provider-neutral wrapper around a third-party calculation result."""

    backend: str
    capability: str
    value: Any
    backend_version: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class OptionalBackend(ABC):
    """Lazy optional backend contract. Importing data_enrichment never imports the dependency."""

    name: str
    version: str  # adapter/package version exposed by this integration
    dependency_name: str
    dependency_version: str
    capabilities: frozenset[str]

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "adapter_version": self.version,
            "dependency_name": self.dependency_name,
            "dependency_version": self.dependency_version,
            "capabilities": sorted(self.capabilities),
            "available": self.available(),
        }

    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def compute(self, capability: str, data: Any, **kwargs: Any) -> BackendComputation:
        raise NotImplementedError
