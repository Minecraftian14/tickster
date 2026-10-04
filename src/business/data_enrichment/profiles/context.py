from __future__ import annotations

from ..context import ContextPackProfile, ContextSectionSpec


COMPACT_RESEARCH_CONTEXT = ContextPackProfile(
    name="compact_research",
    description="Small, recent analytical pack: summaries plus recent returns/volatility/trend series and weekly/monthly context.",
    sections=(
        ContextSectionSpec(
            name="identity_facts",
            source_record_types=("Instrument", "SectorClassification"),
            include_source_records=True,
            max_source_records=2,
            include_series=False,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="recent_market_facts",
            source_record_types=("PriceBar",),
            include_source_records=True,
            max_source_records=30,
            include_series=False,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="fundamental_facts",
            source_record_types=("FundamentalSnapshot",),
            include_source_records=True,
            max_source_records=8,
            include_series=False,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="ownership_facts",
            source_record_types=("ShareholdingSnapshot",),
            include_source_records=True,
            max_source_records=8,
            include_series=False,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="event_facts",
            source_record_types=("CorporateAction", "CompanyEvent", "Filing", "NewsItem"),
            include_source_records=True,
            max_source_records=20,
            include_series=False,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="summaries",
            summary_prefixes=("historical_state_", "historical_percentiles", "volatility_state", "trend_state", "historical_extremes", "persistence", "return_", "volatility_", ),
            include_series=False,
        ),
        ContextSectionSpec(
            name="recent_market",
            metric_prefixes=("close", "return_", "realized_volatility_", "drawdown", "sma_"),
            max_points_per_series=30,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="weekly_context",
            metrics=("week_return",),
            max_points_per_series=52,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="monthly_context",
            metrics=("month_return",),
            max_points_per_series=60,
            include_summaries=False,
        ),
    ),
    max_items=24,
    max_points=500,
)


MEDIUM_RESEARCH_CONTEXT = ContextPackProfile(
    name="medium_research",
    description="Medium-sized analytical pack with broader historical market series and summaries.",
    sections=(
        ContextSectionSpec(
            name="identity_facts",
            source_record_types=("Instrument", "SectorClassification"),
            include_source_records=True,
            max_source_records=2,
            include_series=False,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="recent_market_facts",
            source_record_types=("PriceBar",),
            include_source_records=True,
            max_source_records=90,
            include_series=False,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="fundamental_facts",
            source_record_types=("FundamentalSnapshot",),
            include_source_records=True,
            max_source_records=20,
            include_series=False,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="ownership_facts",
            source_record_types=("ShareholdingSnapshot",),
            include_source_records=True,
            max_source_records=12,
            include_series=False,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="event_facts",
            source_record_types=("CorporateAction", "CompanyEvent", "Filing", "NewsItem"),
            include_source_records=True,
            max_source_records=40,
            include_series=False,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="summaries",
            summary_prefixes=("historical_state_", "historical_percentiles", "volatility_state", "trend_state", "historical_extremes", "persistence", "return_", "volatility_"),
            include_series=False,
        ),
        ContextSectionSpec(
            name="recent_market",
            metric_prefixes=("close", "return_", "realized_volatility_", "drawdown", "sma_", "liquidity_"),
            max_points_per_series=90,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="weekly_context",
            metrics=("week_return",),
            max_points_per_series=156,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="monthly_context",
            metrics=("month_return",),
            max_points_per_series=120,
            include_summaries=False,
        ),
    ),
    max_items=40,
    max_points=1600,
)


FULL_RESEARCH_CONTEXT = ContextPackProfile(
    name="full_research",
    description="Large analytical pack for research workflows; still bounded and multi-resolution, never a raw data dump.",
    sections=(
        ContextSectionSpec(
            name="identity_facts",
            source_record_types=("Instrument", "SectorClassification"),
            include_source_records=True,
            max_source_records=2,
            include_series=False,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="market_facts",
            source_record_types=("PriceBar",),
            include_source_records=True,
            max_source_records=252,
            include_series=False,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="fundamental_facts",
            source_record_types=("FundamentalSnapshot",),
            include_source_records=True,
            max_source_records=40,
            include_series=False,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="ownership_facts",
            source_record_types=("ShareholdingSnapshot",),
            include_source_records=True,
            max_source_records=20,
            include_series=False,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="event_facts",
            source_record_types=("CorporateAction", "CompanyEvent", "Filing", "NewsItem"),
            include_source_records=True,
            max_source_records=100,
            include_series=False,
            include_summaries=False,
        ),
        ContextSectionSpec(
            name="summaries",
            include_all_summaries=True,
            include_series=False,
        ),
        ContextSectionSpec(
            name="market_series",
            metric_prefixes=("return_", "realized_volatility_", "drawdown", "sma_", "liquidity_", ),
            max_points_per_series=252,
            include_summaries=False,
        ),
    ),
    max_items=100,
    max_points=8000,
)


__all__ = ["COMPACT_RESEARCH_CONTEXT", "MEDIUM_RESEARCH_CONTEXT", "FULL_RESEARCH_CONTEXT"]
