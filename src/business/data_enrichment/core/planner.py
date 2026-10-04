from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable, Mapping, Any

from ..models import EnrichmentIssue, EnrichmentResult
from .._version import __version__

if TYPE_CHECKING:
    from ..profiles.defaults import EnrichmentProfile
from .registry import EnricherSpec, EnrichmentRegistry


@dataclass(frozen=True)
class EnrichmentPlan:
    """Resolved deterministic execution plan for an enrichment request."""

    requested_enrichers: tuple[str, ...]
    steps: tuple[EnricherSpec, ...]
    available_capabilities: frozenset[str]
    produced_capabilities: frozenset[str]
    missing_capabilities: frozenset[str]
    reused_capabilities: frozenset[str]
    profile: str | None = None
    profile_version: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def is_executable(self) -> bool:
        return not self.missing_capabilities

    @property
    def step_names(self) -> tuple[str, ...]:
        return tuple(step.name for step in self.steps)


class DependencyPlanner:
    """Resolve transitive enricher dependencies into a deterministic plan.

    A capability may be supplied externally (for example by data_foundation) or
    produced by another enricher. When multiple enrichers can provide a required
    capability, the caller may provide an explicit provider preference; otherwise
    an ambiguity is reported rather than silently choosing one.
    """

    def __init__(
        self,
        registry: EnrichmentRegistry,
        *,
        provider_preferences: Mapping[str, str] | None = None,
    ) -> None:
        self.registry = registry
        self.provider_preferences = dict(provider_preferences or {})

    def providers_for(self, capability: str) -> tuple[EnricherSpec, ...]:
        return self.registry.providers_for(capability)

    def plan(
        self,
        names: Iterable[str],
        *,
        available: Iterable[str] = (),
        profile: "EnrichmentProfile | None = None",
    ) -> EnrichmentPlan:
        requested = tuple(names)
        input_available_caps = set(available)
        available_caps = set(input_available_caps)
        planned: list[EnricherSpec] = []
        planned_names: set[str] = set()
        resolving: list[str] = []
        produced_caps: set[str] = set()
        reused_caps = set(available_caps)
        missing_caps: set[str] = set()
        provider_choices: dict[str, str] = {}

        # Profiles can declare capabilities already guaranteed by the caller's
        # upstream context without forcing those capabilities into every call.
        if profile is not None:
            available_caps.update(profile.available_capabilities)
            reused_caps.update(profile.available_capabilities)

        def add_spec(spec: EnricherSpec) -> bool:
            if spec.name in planned_names:
                return True
            if spec.name in resolving:
                cycle = " -> ".join(resolving + [spec.name])
                raise ValueError(f"Cyclic enrichment dependency: {cycle}")
            resolving.append(spec.name)
            success = True
            try:
                for capability in sorted(spec.requires):
                    if capability in available_caps:
                        continue
                    providers = self.providers_for(capability)
                    provider = self._choose_provider(capability, providers)
                    if provider is None:
                        missing_caps.add(capability)
                        success = False
                        continue
                    provider_choices[capability] = provider.name
                    if not add_spec(provider):
                        success = False
                        continue
                    if capability in available_caps:
                        continue
                    if capability in provider.provides:
                        available_caps.add(capability)
                        produced_caps.add(capability)
                    else:
                        missing_caps.add(capability)
                        success = False
                if success and spec.name not in planned_names:
                    planned.append(spec)
                    planned_names.add(spec.name)
                    newly_provided = set(spec.provides) - available_caps
                    available_caps.update(spec.provides)
                    produced_caps.update(newly_provided)
                return success
            finally:
                resolving.pop()

        for name in requested:
            add_spec(self.registry.get(name))

        # A requested profile is declarative: if it includes explicit enricher names,
        # those names are part of the requested set; profile requirements are treated
        # as preconditions and reported as missing when the caller does not provide them.
        if profile is not None:
            for capability in profile.required_capabilities:
                if capability not in available_caps and capability not in produced_caps:
                    missing_caps.add(capability)

        return EnrichmentPlan(
            requested_enrichers=requested,
            steps=tuple(planned),
            available_capabilities=frozenset(available_caps),
            produced_capabilities=frozenset(produced_caps),
            missing_capabilities=frozenset(missing_caps),
            reused_capabilities=frozenset(reused_caps),
            profile=profile.name if profile else None,
            profile_version=profile.version if profile else None,
            metadata={
                "requested_count": len(requested),
                "planned_count": len(planned),
                "missing_count": len(missing_caps),
                "provider_choices": dict(sorted(provider_choices.items())),
                "input_available_capabilities": sorted(input_available_caps),
                "effective_available_capabilities": sorted(available_caps),
            },
        )

    def plan_profile(
        self,
        profile: "EnrichmentProfile",
        *,
        available: Iterable[str] = (),
    ) -> EnrichmentPlan:
        return self.plan(profile.enrichers, available=available, profile=profile)

    def _choose_provider(self, capability: str, providers: tuple[EnricherSpec, ...]) -> EnricherSpec | None:
        if not providers:
            return None
        preferences = self.provider_preferences
        preferred_name = preferences.get(capability)
        if preferred_name:
            for provider in providers:
                if provider.name == preferred_name:
                    return provider
            raise ValueError(
                f"Provider preference {preferred_name!r} does not provide capability {capability!r}"
            )
        if len(providers) == 1:
            return providers[0]
        raise ValueError(
            f"Ambiguous provider for capability {capability!r}: "
            f"{[provider.name for provider in providers]}. "
            "Provide an explicit provider preference."
        )


def execute_plan(
    context,
    plan: EnrichmentPlan,
    *,
    stop_on_error: bool = False,
) -> EnrichmentResult:
    """Execute a previously resolved plan, retaining planner metadata."""

    combined = EnrichmentResult(enricher="planner", enricher_version=__version__)
    capabilities = set(plan.available_capabilities)
    for spec in plan.steps:
        missing = spec.requires - capabilities
        if missing:
            combined.issues.append(
                EnrichmentIssue(
                    code="missing_capability",
                    severity="error",
                    message=f"Missing capabilities for {spec.name}: {sorted(missing)}",
                    metadata={"enricher": spec.name},
                )
            )
            if stop_on_error:
                break
            continue
        result = spec.enricher.enrich(context)
        combined.extend(result)
        capabilities.update(spec.provides)
        if stop_on_error and any(issue.severity == "error" for issue in result.issues):
            break
    combined.metadata.update(
        {
            "planned_enrichers": list(plan.step_names),
            "requested_enrichers": list(plan.requested_enrichers),
            "final_capabilities": sorted(capabilities),
            "missing_capabilities": sorted(plan.missing_capabilities),
            "profile": plan.profile,
            "profile_version": plan.profile_version,
        }
    )
    return combined
