from __future__ import annotations

from .defaults import EnrichmentProfile


class ProfileRegistry:
    """Registry for named enrichment profiles."""

    def __init__(self) -> None:
        self._items: dict[str, EnrichmentProfile] = {}

    def register(self, profile: EnrichmentProfile) -> None:
        if profile.name in self._items:
            raise ValueError(f"Profile already registered: {profile.name}")
        self._items[profile.name] = profile

    def get(self, name: str) -> EnrichmentProfile:
        try:
            return self._items[name]
        except KeyError as exc:
            raise KeyError(f"Unknown enrichment profile: {name}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))


def default_profile_registry() -> ProfileRegistry:
    from .defaults import (
        BENCHMARK_COMPARATIVE_PROFILE,
        CORE_FUNDAMENTAL_PROFILE,
        CORE_MARKET_PROFILE,
        EVENT_PROFILE,
        OWNERSHIP_PROFILE,
        PEER_COMPARATIVE_PROFILE,
        REGIME_PROFILE,
        RELATIVE_MARKET_PROFILE,
        RESEARCH_CORE_PROFILE,
    )

    registry = ProfileRegistry()
    for profile in (
        CORE_MARKET_PROFILE,
        CORE_FUNDAMENTAL_PROFILE,
        RELATIVE_MARKET_PROFILE,
        BENCHMARK_COMPARATIVE_PROFILE,
        PEER_COMPARATIVE_PROFILE,
        OWNERSHIP_PROFILE,
        EVENT_PROFILE,
        REGIME_PROFILE,
        RESEARCH_CORE_PROFILE,
    ):
        registry.register(profile)
    return registry
