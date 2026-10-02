from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .context import EnrichmentContext
from .protocols import Enricher
from ..models import EnrichmentIssue, EnrichmentResult
from .._version import __version__


@dataclass(frozen=True)
class EnricherSpec:
    name: str
    version: str
    requires: frozenset[str]
    provides: frozenset[str]
    enricher: Any


class EnrichmentRegistry:
    def __init__(self) -> None:
        self._items: dict[str, EnricherSpec] = {}

    def register(self, enricher: Enricher) -> None:
        if enricher.name in self._items:
            raise ValueError(f"Enricher already registered: {enricher.name}")
        self._items[enricher.name] = EnricherSpec(
            name=enricher.name,
            version=enricher.version,
            requires=frozenset(enricher.requires),
            provides=frozenset(enricher.provides),
            enricher=enricher,
        )

    def get(self, name: str) -> EnricherSpec:
        try:
            return self._items[name]
        except KeyError as exc:
            raise KeyError(f"Unknown enricher: {name}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))

    def providers_for(self, capability: str) -> tuple[EnricherSpec, ...]:
        """Return enrichers that can provide a capability, in stable order."""
        return tuple(
            self._items[name]
            for name in sorted(self._items)
            if capability in self._items[name].provides
        )


class EnrichmentPipeline:
    """Dependency-aware deterministic pipeline with stable capability semantics."""

    def __init__(self, registry: EnrichmentRegistry) -> None:
        self.registry = registry

    def plan(self, names: list[str], *, available: set[str] | None = None) -> list[EnricherSpec]:
        available_caps = set(available or set())
        selected = [self.registry.get(name) for name in names]
        planned: list[EnricherSpec] = []
        remaining = selected[:]
        while remaining:
            progress = False
            for spec in list(remaining):
                missing = spec.requires - available_caps
                if not missing:
                    planned.append(spec)
                    available_caps.update(spec.provides)
                    remaining.remove(spec)
                    progress = True
            if not progress:
                missing = sorted(set().union(*(set(s.requires) - available_caps for s in remaining)))
                raise ValueError(f"Unable to plan enrichment; missing capabilities: {missing}")
        return planned

    def run(self, context: EnrichmentContext, names: list[str], *, available: set[str] | None = None) -> EnrichmentResult:
        specs = self.plan(names, available=available)
        combined = EnrichmentResult(enricher="pipeline", enricher_version=__version__)
        caps = set(available or set())
        for spec in specs:
            missing = spec.requires - caps
            if missing:
                combined.issues.append(EnrichmentIssue(
                    code="missing_capability",
                    severity="error",
                    message=f"Missing capabilities for {spec.name}: {sorted(missing)}",
                    metadata={"enricher": spec.name},
                ))
                continue
            result = spec.enricher.enrich(context)
            combined.extend(result)
            caps.update(spec.provides)
        combined.metadata["planned_enrichers"] = [spec.name for spec in specs]
        combined.metadata["final_capabilities"] = sorted(caps)
        return combined

    def dependency_plan(
        self,
        names: list[str],
        *,
        available: set[str] | None = None,
        provider_preferences: dict[str, str] | None = None,
    ):
        from .planner import DependencyPlanner
        return DependencyPlanner(self.registry, provider_preferences=provider_preferences).plan(
            names, available=available or set()
        )



def _register_core_market(registry: EnrichmentRegistry) -> None:
    from ..market import (
        DrawdownEnricher,
        LiquidityEnricher,
        MovingAverageEnricher,
        MultiResolutionSummaryEnricher,
        ReturnHorizonSummaryEnricher,
        ReturnSeriesEnricher,
        RollingVolatilityEnricher,
        VolatilitySummaryEnricher,
    )
    for enricher in (
        ReturnSeriesEnricher(),
        ReturnHorizonSummaryEnricher(),
        RollingVolatilityEnricher(),
        VolatilitySummaryEnricher(),
        DrawdownEnricher(),
        MovingAverageEnricher(),
        LiquidityEnricher(),
        MultiResolutionSummaryEnricher(),
    ):
        registry.register(enricher)


def _register_core_fundamental(registry: EnrichmentRegistry) -> None:
    from ..fundamental import (
        FundamentalCashFlowEnricher,
        FundamentalGrowthEnricher,
        FundamentalProfitabilityEnricher,
        FundamentalSolvencyEnricher,
        FundamentalTTMEnricher,
    )
    for enricher in (
        FundamentalGrowthEnricher(),
        FundamentalTTMEnricher(),
        FundamentalProfitabilityEnricher(),
        FundamentalSolvencyEnricher(),
        FundamentalCashFlowEnricher(),
    ):
        registry.register(enricher)


def default_registry() -> EnrichmentRegistry:
    """Return a registry containing the built-in deterministic market and fundamental enrichers."""
    registry = EnrichmentRegistry()
    _register_core_market(registry)
    from ..market import RelativePerformanceEnricher
    registry.register(RelativePerformanceEnricher())
    from ..comparative import BenchmarkComparisonEnricher, PeerReturnComparisonEnricher
    registry.register(BenchmarkComparisonEnricher())
    registry.register(PeerReturnComparisonEnricher())
    from ..ownership import ShareholdingChangeEnricher, InsiderActivityEnricher, LargeDealActivityEnricher
    from ..events import CompanyEventSummaryEnricher, EventReactionEnricher
    for enricher in (ShareholdingChangeEnricher(), InsiderActivityEnricher(), LargeDealActivityEnricher(), CompanyEventSummaryEnricher(), EventReactionEnricher()):
        registry.register(enricher)
    _register_core_fundamental(registry)
    from ..regimes import HistoricalStateSummaryEnricher, TrendRegimeEnricher, VolatilityRegimeEnricher, ExtremesRegimeEnricher, PersistenceRegimeEnricher
    for enricher in (HistoricalStateSummaryEnricher(), TrendRegimeEnricher(), VolatilityRegimeEnricher(), ExtremesRegimeEnricher(), PersistenceRegimeEnricher()):
        registry.register(enricher)
    return registry
