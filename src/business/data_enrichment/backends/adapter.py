from __future__ import annotations

from typing import Any

from .base import BackendComputation, BackendUnavailableError


class BackendAdapter:
    """Small facade that turns third-party backend results into backend computations."""

    def __init__(self, backend: Any) -> None:
        self.backend = backend

    @property
    def name(self) -> str:
        return self.backend.name

    def compute(self, capability: str, data: Any, **kwargs: Any) -> BackendComputation:
        return self.backend.compute(capability, data, **kwargs)

    def available(self) -> bool:
        try:
            return bool(self.backend.available())
        except (BackendUnavailableError, RuntimeError):
            return False
