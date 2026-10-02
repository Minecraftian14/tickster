"""Extensible deterministic enrichment layer for the Indian equity knowledge substrate."""

from ._version import __version__
from .contract import CONTRACT_VERSION, FOUNDATION_CONTRACT, EnrichmentContract, public_contract, validate_public_contract, is_compatible_contract, assert_compatible_contract
from .context import ContextItemRef, ContextPack, ContextPackBuilder, ContextPackProfile, ContextSectionSpec
from .models import DerivedObservation, DerivedSeries, DerivedSeriesPoint, DerivedSummary, DerivationLineage, EnrichmentIssue, EnrichmentResult
from .core.context import EnrichmentContext
from .core.protocols import Enricher, ComputationBackend
from .core.registry import EnricherSpec, EnrichmentPipeline, EnrichmentRegistry, default_registry
from .core.planner import DependencyPlanner, EnrichmentPlan, execute_plan
from .core.hashing import stable_id
from .market.basic import SimpleReturnEnricher, ReturnSummaryEnricher
from .comparative import BenchmarkComparisonEnricher, PeerReturnComparisonEnricher
from .market import (
    DrawdownEnricher,
    LiquidityEnricher,
    MovingAverageEnricher,
    MultiResolutionSummaryEnricher,
    RelativePerformanceEnricher,
    ReturnHorizonSummaryEnricher,
    ReturnSeriesEnricher,
    RollingVolatilityEnricher,
    VolatilitySummaryEnricher,
)
from .backends import BackendAdapter, BackendComputation, BackendUnavailableError, BackendRegistry, FinanceToolkitBackend, OptionalBackend, PandasTABackend, QuantStatsBackend, default_backend_registry
from .fundamental import FundamentalCashFlowEnricher, FundamentalGrowthEnricher, FundamentalProfitabilityEnricher, FundamentalSolvencyEnricher, FundamentalTTMEnricher
from .ownership import ShareholdingChangeEnricher, InsiderActivityEnricher, LargeDealActivityEnricher
from .events import CompanyEventSummaryEnricher, EventReactionEnricher
from .regimes import HistoricalStateSummaryEnricher, TrendRegimeEnricher, VolatilityRegimeEnricher, ExtremesRegimeEnricher, PersistenceRegimeEnricher
from .profiles import (CORE_MARKET_PROFILE, CORE_FUNDAMENTAL_PROFILE, RELATIVE_MARKET_PROFILE, BENCHMARK_COMPARATIVE_PROFILE, PEER_COMPARATIVE_PROFILE, OWNERSHIP_PROFILE, EVENT_PROFILE, REGIME_PROFILE, RESEARCH_CORE_PROFILE, EnrichmentProfile, ProfileRegistry, ProfilePlanner, default_profile_registry)

__all__ = [
    "__version__", "CONTRACT_VERSION", "FOUNDATION_CONTRACT", "EnrichmentContract", "public_contract", "validate_public_contract", "is_compatible_contract", "assert_compatible_contract",
    "ContextItemRef", "ContextPack", "ContextPackBuilder", "ContextPackProfile", "ContextSectionSpec",
    "DerivedObservation", "DerivedSeries", "DerivedSeriesPoint", "DerivedSummary", "DerivationLineage",
    "EnrichmentIssue", "EnrichmentResult", "EnrichmentContext", "Enricher", "ComputationBackend",
    "EnricherSpec", "EnrichmentPipeline", "EnrichmentRegistry", "default_registry", "stable_id",
    "DependencyPlanner", "EnrichmentPlan", "execute_plan",
    "BenchmarkComparisonEnricher", "PeerReturnComparisonEnricher",
    "DrawdownEnricher", "LiquidityEnricher", "MovingAverageEnricher", "MultiResolutionSummaryEnricher",
    "RelativePerformanceEnricher", "ReturnHorizonSummaryEnricher", "ReturnSeriesEnricher", "SimpleReturnEnricher", "ReturnSummaryEnricher",
    "RollingVolatilityEnricher", "VolatilitySummaryEnricher",
    "BackendAdapter", "BackendComputation", "BackendUnavailableError", "BackendRegistry", "default_backend_registry", "FinanceToolkitBackend", "OptionalBackend", "PandasTABackend", "QuantStatsBackend",
    "CORE_MARKET_PROFILE", "CORE_FUNDAMENTAL_PROFILE", "RELATIVE_MARKET_PROFILE", "BENCHMARK_COMPARATIVE_PROFILE", "PEER_COMPARATIVE_PROFILE", "OWNERSHIP_PROFILE", "EVENT_PROFILE", "REGIME_PROFILE", "RESEARCH_CORE_PROFILE", "EnrichmentProfile", "ProfileRegistry", "ProfilePlanner", "default_profile_registry",
    "COMPACT_RESEARCH_CONTEXT", "MEDIUM_RESEARCH_CONTEXT", "FULL_RESEARCH_CONTEXT",
    "FundamentalGrowthEnricher", "FundamentalTTMEnricher", "FundamentalProfitabilityEnricher", "FundamentalSolvencyEnricher", "FundamentalCashFlowEnricher",
    "ShareholdingChangeEnricher", "InsiderActivityEnricher", "LargeDealActivityEnricher",
    "CompanyEventSummaryEnricher", "EventReactionEnricher",
    "HistoricalStateSummaryEnricher", "TrendRegimeEnricher", "VolatilityRegimeEnricher", "ExtremesRegimeEnricher", "PersistenceRegimeEnricher",
]

from .profiles.context import COMPACT_RESEARCH_CONTEXT, MEDIUM_RESEARCH_CONTEXT, FULL_RESEARCH_CONTEXT
