from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class CapabilityResult:
    source: str
    capability: str
    status: str
    details: dict[str, Any]


def run_health_checks(providers: dict[str, Any]) -> list[CapabilityResult]:
    results: list[CapabilityResult] = []
    for name, provider in providers.items():
        try:
            results.append(CapabilityResult(name, "health", "ok", provider.health()))
        except Exception as exc:
            results.append(CapabilityResult(name, "health", "error", {"error": str(exc)}))
    return results


def as_dicts(results: list[CapabilityResult]) -> list[dict[str, Any]]:
    return [asdict(x) for x in results]
