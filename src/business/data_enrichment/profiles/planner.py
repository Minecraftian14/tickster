from __future__ import annotations

from typing import Iterable

from ..core.planner import DependencyPlanner, EnrichmentPlan
from ..core.registry import EnrichmentRegistry
from .defaults import EnrichmentProfile


class ProfilePlanner:
    """Resolve named profiles into executable enrichment plans."""

    def __init__(
        self,
        enricher_registry: EnrichmentRegistry,
        profile_registry,
        *,
        provider_preferences: dict[str, str] | None = None,
    ) -> None:
        self.profile_registry = profile_registry
        self.planner = DependencyPlanner(
            enricher_registry,
            provider_preferences=provider_preferences,
        )

    def plan(
        self,
        profile: str | EnrichmentProfile,
        *,
        available: Iterable[str] = (),
    ) -> EnrichmentPlan:
        resolved = self.profile_registry.get(profile) if isinstance(profile, str) else profile
        return self.planner.plan_profile(resolved, available=available)
