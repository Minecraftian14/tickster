from __future__ import annotations

from .base import OptionalBackend
from .financetoolkit import FinanceToolkitBackend
from .pandas_ta import PandasTABackend
from .quantstats import QuantStatsBackend


class BackendRegistry:
    """Registry for optional computation backends."""

    def __init__(self) -> None:
        self._items: dict[str, OptionalBackend] = {}

    def register(self, backend: OptionalBackend) -> None:
        if backend.name in self._items:
            raise ValueError(f"Backend already registered: {backend.name}")
        self._items[backend.name] = backend

    def get(self, name: str) -> OptionalBackend:
        try:
            return self._items[name]
        except KeyError as exc:
            raise KeyError(f"Unknown backend: {name}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))

    def available(self) -> tuple[str, ...]:
        return tuple(name for name in self.names() if self._items[name].available())

    def for_capability(self, capability: str, *, preferred: str | None = None) -> OptionalBackend:
        if preferred is not None:
            backend = self.get(preferred)
            if not backend.supports(capability):
                raise ValueError(f"Backend {preferred!r} does not support capability {capability!r}.")
            return backend
        candidates = [self._items[name] for name in self.names() if self._items[name].supports(capability)]
        available = [backend for backend in candidates if backend.available()]
        if not available:
            raise LookupError(f"No available backend supports capability {capability!r}.")
        return available[0]


def default_backend_registry() -> BackendRegistry:
    registry = BackendRegistry()
    registry.register(FinanceToolkitBackend())
    registry.register(QuantStatsBackend())
    registry.register(PandasTABackend())
    return registry
