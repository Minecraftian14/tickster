"""The data demand declaration for the Tacit Abyss experiment.

The collection layer supplies ``message['context']`` as ``(pack, (result,
bundle))``. This profile is deliberately declarative: collection/provider
selection remains outside the experiment.
"""

from data_enrichment import ContextPackProfile, ContextSectionSpec


TACIT_ABYSS_CONTEXT = ContextPackProfile(
    name="tacit_abyss_india_research",
    description="Bounded India-equity evidence for technical, fundamental, news, sentiment, and risk research.",
    sections=(
        ContextSectionSpec(name="identity", source_record_types=("Instrument", "SectorClassification"), include_source_records=True, include_series=False, include_summaries=False, max_source_records=4),
        ContextSectionSpec(name="market_and_indices", source_record_types=("PriceBar", "IndexSnapshot", "IndexPriceBar"), include_source_records=True, include_series=False, include_summaries=False, max_source_records=252),
        ContextSectionSpec(name="fundamentals", source_record_types=("FundamentalSnapshot", "Filing"), include_source_records=True, include_series=False, include_summaries=False, max_source_records=48),
        ContextSectionSpec(name="ownership_and_events", source_record_types=("ShareholdingSnapshot", "InsiderTransaction", "LargeDeal", "CorporateAction", "CompanyEvent"), include_source_records=True, include_series=False, include_summaries=False, max_source_records=60),
        ContextSectionSpec(name="news_and_social", source_record_types=("NewsItem", "SocialPost"), include_source_records=True, include_series=False, include_summaries=False, max_source_records=80),
        ContextSectionSpec(name="macro", source_record_types=("MacroObservation", "MacroRelease"), include_source_records=True, include_series=False, include_summaries=False, max_source_records=60),
        ContextSectionSpec(name="derived_research", include_all_summaries=True, include_series=False),
        ContextSectionSpec(name="derived_market_series", metric_prefixes=("return_", "realized_volatility_", "drawdown", "sma_", "rsi_", "macd", "liquidity_"), include_summaries=False, max_points_per_series=252),
    ),
    max_items=180,
    max_points=4000,
)

__all__ = ["TACIT_ABYSS_CONTEXT"]
