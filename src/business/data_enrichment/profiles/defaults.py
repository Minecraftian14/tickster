from __future__ import annotations

from dataclasses import dataclass, field

from .._version import __version__


@dataclass(frozen=True)
class EnrichmentProfile:
    name: str
    enrichers: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""
    version: str = __version__
    available_capabilities: frozenset[str] = field(default_factory=frozenset)
    required_capabilities: frozenset[str] = field(default_factory=frozenset)


CORE_MARKET_PROFILE = EnrichmentProfile(
    name="market_core",
    enrichers=(
        "market.returns",
        "market.return_horizons",
        "market.rolling_volatility",
        "market.volatility_summary",
        "market.drawdown",
        "market.moving_averages",
        "market.liquidity",
        "market.multi_resolution",
    ),
    description="Deterministic descriptive market enrichment pack: returns, volatility, drawdown, trend, liquidity, and multi-resolution summaries.",
)

RELATIVE_MARKET_PROFILE = EnrichmentProfile(
    name="market_relative",
    enrichers=("market.relative_performance",),
    description="Benchmark-relative market enrichment. Requires benchmark.close and benchmark records in the context metadata.",
)


CORE_FUNDAMENTAL_PROFILE = EnrichmentProfile(
    name="fundamental_core",
    enrichers=(
        "fundamental.growth",
        "fundamental.ttm",
        "fundamental.profitability",
        "fundamental.solvency",
        "fundamental.cashflow",
    ),
    description="Deterministic fundamental enrichment pack: growth, TTM flows, profitability, liquidity/leverage, and cash-flow quality.",
)


BENCHMARK_COMPARATIVE_PROFILE = EnrichmentProfile(
    name="benchmark_comparative",
    enrichers=("comparative.benchmark",),
    description="Benchmark-relative performance and risk statistics using aligned daily returns.",
)

PEER_COMPARATIVE_PROFILE = EnrichmentProfile(
    name="peer_comparative",
    enrichers=("comparative.peer_returns",),
    description="Peer-group return comparison using a caller-supplied peer record mapping.",
)


OWNERSHIP_PROFILE = EnrichmentProfile(
    name="ownership_core",
    enrichers=(
        "ownership.shareholding_changes",
        "ownership.insider_activity",
        "ownership.large_deal_activity",
    ),
    description="Descriptive ownership, insider and large-deal activity over configurable windows.",
)

EVENT_PROFILE = EnrichmentProfile(
    name="events_core",
    enrichers=(
        "events.company_summary",
        "events.market_reaction",
    ),
    description="Company-event frequency plus descriptive forward market reactions. Event reactions use subsequent observations and are explicitly outcome-based.",
)


REGIME_PROFILE = EnrichmentProfile(
    name="regime_core",
    enrichers=(
        "regime.historical_state",
        "regime.trend_state",
        "regime.volatility_state",
        "regime.extremes",
        "regime.persistence",
    ),
    description="Descriptive historical-state enrichment: compact multi-horizon history, trend state, volatility state, extremes, and persistence.",
)


RESEARCH_CORE_PROFILE = EnrichmentProfile(
    name="research_core",
    enrichers=(
        "market.returns",
        "market.return_horizons",
        "market.rolling_volatility",
        "market.volatility_summary",
        "market.drawdown",
        "market.moving_averages",
        "market.liquidity",
        "market.multi_resolution",
        "market.relative_performance",
        "comparative.benchmark",
        "fundamental.growth",
        "fundamental.ttm",
        "fundamental.profitability",
        "fundamental.solvency",
        "fundamental.cashflow",
        "ownership.shareholding_changes",
        "ownership.insider_activity",
        "ownership.large_deal_activity",
        "events.company_summary",
        "regime.historical_state",
        "regime.trend_state",
        "regime.volatility_state",
        "regime.extremes",
        "regime.persistence",
    ),
    description="Broad descriptive research enrichment profile. Requires benchmark.close for benchmark-relative enrichment and the relevant foundation capabilities for each domain.",
)
