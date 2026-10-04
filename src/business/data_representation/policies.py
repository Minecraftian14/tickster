from __future__ import annotations

# The representation layer intentionally works from names rather than importing
# every collection model. This keeps it decoupled from data_collection while still
# allowing type-specific presentation rules.

GENERIC_DROP_FIELDS = frozenset({
    "algorithm",
    "algorithm_version",
    "calculated_at",
    "calculation_basis",
    "canonical_record_id",
    "content_hash",
    "decision_id",
    "derived_id",
    "enricher",
    "enricher_version",
    "finding_id",
    "instrument_ids",
    "lineage",
    "local_path",
    "metadata",
    "observation_id",
    "pack_id",
    "parameters",
    "provenance",
    "quality_ids",
    "raw_artifact_ids",
    "raw_ref",
    "record_id",
    "relationship_id",
    "sha256",
    "source_observation_ids",
    "source_record_ids",
    "text_ref",
})

# These fields are implementation plumbing rather than equity-analysis content.
# They are suppressed unless a type-specific policy explicitly keeps them.
GENERIC_DROP_SUFFIXES = ("_id",)


RECORD_POLICIES: dict[str, dict[str, object]] = {
    "Instrument": {
        "drop": frozenset({
            "instrument_id",
            "provider_identifiers",
            "instrument_key",
            "exchange_token",
            "tick_size",
            "lot_size",
            "freeze_quantity",
            "cas_eligible",
        }),
        "order": (
            "isin", "symbol", "exchange", "name", "short_name", "segment",
            "series", "security_type", "sector", "industry", "currency", "active",
        ),
        "expand": frozenset(),
    },
    "PriceBar": {
        "drop": frozenset({"instrument_id"}),
        "header": frozenset({"timeframe"}),
        "order": (
            "timestamp", "open", "high", "low", "close", "volume",
            "turnover", "delivery_quantity", "delivery_percent",
        ),
        "expand": frozenset(),
    },
    "MarketQuote": {
        "drop": frozenset({
            "instrument_id", "bid_depth", "ask_depth", "raw_quote",
            "total_buy_quantity", "total_sell_quantity", "open_interest",
            "previous_oi", "oi_day_high", "oi_day_low", "indicative_imbalance_quantity_total",
            "indicative_imbalance_quantity_market",
        }),
        "order": (
            "timestamp", "last_price", "previous_close", "net_change", "day_open",
            "day_high", "day_low", "volume", "year_high", "year_low", "average_price",
            "last_trade_time", "ohlc_timestamp", "reference_price",
        ),
        "expand": frozenset(),
    },
    "FundamentalSnapshot": {
        "drop": frozenset({"instrument_id"}),
        "order": (
            "period_end", "period_start", "period_type", "statement_type", "statement_name",
            "fiscal_year", "units_in",
        ),
        "expand": frozenset({"metrics"}),
    },
    "ShareholdingSnapshot": {
        "drop": frozenset({"instrument_id"}),
        "order": ("period_end", "holders"),
        "expand": frozenset(),
    },
    "CorporateAction": {
        "drop": frozenset({"instrument_id"}),
        "order": (
            "action_type", "announcement_date", "ex_date", "record_date", "amount", "ratio",
            "details", "face_value", "company_name", "series", "book_closure_start", "book_closure_end",
        ),
        "expand": frozenset(),
    },
    "CompanyEvent": {
        "drop": frozenset({"event_id", "instrument_id"}),
        "order": ("event_type", "event_date", "announcement_date", "subject", "description", "url", "details"),
        "expand": frozenset(),
    },
    "NewsItem": {
        "drop": frozenset({"news_id", "instrument_ids"}),
        "order": ("published_at", "source_name", "title", "text", "url"),
        "expand": frozenset(),
        "text_limits": {"text": 900},
    },
    "CompanyDocument": {
        "drop": frozenset({
            "document_id", "instrument_id", "filing_id", "raw_ref", "text_ref", "content_hash",
        }),
        "order": ("document_type", "published_at", "title", "url", "mime_type", "byte_size"),
        "expand": frozenset(),
    },
    "Filing": {
        "drop": frozenset({"filing_id", "instrument_id"}),
        "order": (
            "filing_type", "category", "subcategory", "period_end", "period_start", "financial_year",
            "statement_type", "submission_type", "audited", "published_at", "received_at", "revised_at",
            "revision_remarks", "details_url", "assets",
        ),
        "expand": frozenset(),
    },
    "DocumentAsset": {
        "drop": frozenset({
            "asset_id", "filing_id", "instrument_id", "content_hash", "sha256", "local_path", "text_ref",
        }),
        "order": ("document_type", "title", "url", "mime_type", "byte_size"),
        "expand": frozenset(),
    },
    "XBRLFact": {
        "drop": frozenset({"filing_id", "instrument_id", "context_ref", "unit_ref", "raw_xml"}),
        "order": (
            "concept", "label", "value", "decimals", "period_start", "period_end", "instant", "dimensions",
        ),
        "expand": frozenset({"dimensions"}),
    },
    "CompanyPeer": {
        "drop": frozenset({"instrument_id", "peer_instrument_key", "peer_isin"}),
        "order": (
            "peer_name", "sector", "description", "sector_market_cap_inr", "sector_market_cap_usd",
        ),
        "expand": frozenset(),
    },
    "InsiderTransaction": {
        "drop": frozenset({"event_id", "instrument_id", "xbrl_url"}),
        "order": (
            "intimation_date", "company_name", "person_name", "person_category", "transaction_type",
            "security_type_prior", "securities_prior", "holding_percent_prior", "security_type_acquired",
            "securities_acquired", "transaction_value", "security_type_post", "securities_post",
            "holding_percent_post", "acquisition_from", "acquisition_to", "mode", "buy_value", "buy_quantity",
            "sell_value", "sell_quantity", "remarks",
        ),
        "expand": frozenset(),
    },
    "LargeDeal": {
        "drop": frozenset({"event_id", "instrument_id"}),
        "order": (
            "trade_date", "company_name", "deal_type", "client_name", "side", "quantity",
            "weighted_average_price", "remarks", "details",
        ),
        "expand": frozenset(),
    },
    "SectorClassification": {
        "drop": frozenset({"instrument_id", "symbol"}),
        "order": ("classification_as_of", "sector_macro", "sector", "industry", "basic_industry"),
        "expand": frozenset(),
    },
    "IndexPriceBar": {
        "drop": frozenset({"index_id", "index_symbol", "index_name"}),
        "order": ("timestamp", "open", "high", "low", "close"),
        "expand": frozenset(),
    },
    "IndexSnapshot": {
        "drop": frozenset({"index_id", "index_symbol", "index_name"}),
        "order": (
            "timestamp", "value", "change", "change_percent", "previous_close", "open", "high", "low",
            "year_high", "year_low", "one_year_return_percent", "one_month_return_percent", "constituent_count",
        ),
        "expand": frozenset(),
    },
    "IndexValuationSnapshot": {
        "drop": frozenset({"index_id", "index_symbol", "index_name"}),
        "order": ("observation_date", "pe", "pb", "dividend_yield"),
        "expand": frozenset(),
    },
    "IndexConstituent": {
        "drop": frozenset({"index_id", "index_symbol", "index_name", "instrument_id"}),
        "order": (
            "effective_date", "symbol", "company_name", "weight_percent", "rank", "price", "change",
            "change_percent", "market_cap", "free_float_market_cap", "volume", "traded_value",
        ),
        "expand": frozenset(),
    },
    "MacroObservation": {
        "drop": frozenset({"series_id"}),
        "order": ("observation_date", "value", "unit"),
        "expand": frozenset(),
    },
    "MacroSeries": {
        "drop": frozenset({"series_id"}),
        "order": ("name", "description", "frequency", "unit", "source"),
        "expand": frozenset(),
    },
    "MacroRelease": {
        "drop": frozenset({"release_id"}),
        "order": ("published_at", "title", "reference_period", "source", "url"),
        "expand": frozenset(),
    },
    "RegulatoryItem": {
        "drop": frozenset({"regulatory_id", "instrument_ids"}),
        "order": ("category", "subcategory", "published_at", "title", "department", "section", "detail_url", "document_urls", "entity_names"),
        "expand": frozenset(),
    },
    "RegulatoryDocument": {
        "drop": frozenset({"document_id", "regulatory_id", "content_hash", "local_path"}),
        "order": ("title", "url", "mime_type", "byte_size", "text_ref"),
        "expand": frozenset(),
    },
}


__all__ = ["GENERIC_DROP_FIELDS", "GENERIC_DROP_SUFFIXES", "RECORD_POLICIES"]
