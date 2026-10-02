from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Mapping

from ._version import __version__

CONTRACT_VERSION = "1.0"
FOUNDATION_CONTRACT = "1.x"


@dataclass(frozen=True)
class EnrichmentContract:
    """Machine-readable compatibility contract for data_enrichment 1.x."""

    package_version: str
    contract_version: str
    foundation_contract: str
    stable_exports: Mapping[str, tuple[str, ...]]
    guarantees: tuple[str, ...]


STABLE_EXPORTS: dict[str, tuple[str, ...]] = {
    "data_enrichment": (
        '__version__',
        'CONTRACT_VERSION',
        'FOUNDATION_CONTRACT',
        'EnrichmentContract',
        'public_contract',
        'validate_public_contract',
        'is_compatible_contract',
        'assert_compatible_contract',
        'ContextItemRef',
        'ContextPack',
        'ContextPackBuilder',
        'ContextPackProfile',
        'ContextSectionSpec',
        'DerivedObservation',
        'DerivedSeries',
        'DerivedSeriesPoint',
        'DerivedSummary',
        'DerivationLineage',
        'EnrichmentIssue',
        'EnrichmentResult',
        'EnrichmentContext',
        'Enricher',
        'ComputationBackend',
        'EnricherSpec',
        'EnrichmentPipeline',
        'EnrichmentRegistry',
        'default_registry',
        'stable_id',
        'DependencyPlanner',
        'EnrichmentPlan',
        'execute_plan',
        'BenchmarkComparisonEnricher',
        'PeerReturnComparisonEnricher',
        'DrawdownEnricher',
        'LiquidityEnricher',
        'MovingAverageEnricher',
        'MultiResolutionSummaryEnricher',
        'RelativePerformanceEnricher',
        'ReturnHorizonSummaryEnricher',
        'ReturnSeriesEnricher',
        'SimpleReturnEnricher',
        'ReturnSummaryEnricher',
        'RollingVolatilityEnricher',
        'VolatilitySummaryEnricher',
        'BackendAdapter',
        'BackendComputation',
        'BackendUnavailableError',
        'BackendRegistry',
        'default_backend_registry',
        'FinanceToolkitBackend',
        'OptionalBackend',
        'PandasTABackend',
        'QuantStatsBackend',
        'CORE_MARKET_PROFILE',
        'CORE_FUNDAMENTAL_PROFILE',
        'RELATIVE_MARKET_PROFILE',
        'BENCHMARK_COMPARATIVE_PROFILE',
        'PEER_COMPARATIVE_PROFILE',
        'OWNERSHIP_PROFILE',
        'EVENT_PROFILE',
        'REGIME_PROFILE',
        'RESEARCH_CORE_PROFILE',
        'EnrichmentProfile',
        'ProfileRegistry',
        'ProfilePlanner',
        'default_profile_registry',
        'COMPACT_RESEARCH_CONTEXT',
        'MEDIUM_RESEARCH_CONTEXT',
        'FULL_RESEARCH_CONTEXT',
        'FundamentalGrowthEnricher',
        'FundamentalTTMEnricher',
        'FundamentalProfitabilityEnricher',
        'FundamentalSolvencyEnricher',
        'FundamentalCashFlowEnricher',
        'ShareholdingChangeEnricher',
        'InsiderActivityEnricher',
        'LargeDealActivityEnricher',
        'CompanyEventSummaryEnricher',
        'EventReactionEnricher',
        'HistoricalStateSummaryEnricher',
        'TrendRegimeEnricher',
        'VolatilityRegimeEnricher',
        'ExtremesRegimeEnricher',
        'PersistenceRegimeEnricher'
    ),
    "data_enrichment.models": (
        "DerivedObservation", "DerivedSeries", "DerivedSeriesPoint",
        "DerivedSummary", "DerivationLineage", "EnrichmentIssue", "EnrichmentResult",
    ),
    "data_enrichment.core.protocols": ("Enricher", "ComputationBackend"),
    "data_enrichment.core.registry": ("EnricherSpec", "EnrichmentRegistry", "EnrichmentPipeline", "default_registry"),
    "data_enrichment.core.planner": ("DependencyPlanner", "EnrichmentPlan", "execute_plan"),
    "data_enrichment.context": ("ContextPack", "ContextPackBuilder", "ContextPackProfile", "ContextItemRef", "ContextSectionSpec"),
    "data_enrichment.profiles": ("EnrichmentProfile", "ProfileRegistry", "ProfilePlanner", "default_profile_registry"),
    "data_enrichment.backends": ("BackendAdapter", "BackendComputation", "BackendUnavailableError", "BackendRegistry", "FinanceToolkitBackend", "QuantStatsBackend", "PandasTABackend", "default_backend_registry"),
}


GUARANTEES = (
    "Derived outputs are deterministic unless explicitly documented otherwise.",
    "Derived outputs retain calculation metadata and evidence lineage when inputs provide it.",
    "Point-in-time filtering delegates temporal visibility to data_foundation.",
    "Optional computation backends are not required by the base package.",
    "Context packs select existing derived outputs; they do not recalculate metrics.",
    "No provider-specific market-data acquisition is performed by this package.",
    "The v1.x public API is covered by contract tests and changes require a deliberate compatibility decision.",
)

CONTRACT = EnrichmentContract(
    package_version=__version__,
    contract_version=CONTRACT_VERSION,
    foundation_contract=FOUNDATION_CONTRACT,
    stable_exports=STABLE_EXPORTS,
    guarantees=GUARANTEES,
)


def public_contract() -> EnrichmentContract:
    """Return the stable v1 contract."""
    return CONTRACT


def validate_public_contract() -> tuple[str, ...]:
    """Return missing stable exports; an empty tuple means the contract is intact."""
    missing: list[str] = []
    for module_name, names in STABLE_EXPORTS.items():
        module = import_module(module_name)
        for name in names:
            if not hasattr(module, name):
                missing.append(f"{module_name}.{name}")
    return tuple(sorted(missing))


def is_compatible_contract(contract_version: str) -> bool:
    """Return whether a major-version-compatible contract can be consumed."""
    major = contract_version.split(".", 1)[0]
    return major == CONTRACT_VERSION.split(".", 1)[0]


def assert_compatible_contract(contract_version: str) -> None:
    """Raise ValueError when a downstream contract is outside this package's major line."""
    if not is_compatible_contract(contract_version):
        raise ValueError(
            f"Unsupported data_enrichment contract {contract_version!r}; "
            f"supported major contract is {CONTRACT_VERSION!r}"
        )
