from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Generic, TypeVar

T = TypeVar("T")


class Collector(ABC, Generic[T]):
    """Provider-neutral collector contract for one domain."""

    name: str
    domain: str

    @abstractmethod
    def health(self) -> dict:
        """Return a cheap capability/connectivity check."""

    @abstractmethod
    def collect_sample(self, symbol: str, start: date | None = None, end: date | None = None) -> list[T]:
        """Return a small representative sample, safe for probes/tests."""
