from __future__ import annotations

from typing import Any, Iterable

from data_collection.collection.market import MarketCollector
from data_collection.export.markdown import models_to_markdown
from data_collection.providers.yfinance import YahooFinanceProvider
from data_enrichment import (
    CORE_MARKET_PROFILE,
    EnrichmentContext,
    ProfilePlanner,
    default_profile_registry,
    default_registry,
    execute_plan,
)

HISTORY_PERIOD = "1mo"


def enrich_equities_basic(*equity_names: str) -> dict[str, Any]:
    if not isinstance(equity_names, Iterable):
        raise TypeError("equity_names must be a list of strings")

    if not equity_names:
        return {}

    symbols: list[str] = []
    seen: set[str] = set()

    for value in equity_names:
        if not isinstance(value, str):
            raise TypeError(f"Each equity name must be a string, got {type(value).__name__}")

        symbol = value.strip().upper()
        if not symbol:
            continue
        if symbol not in seen:
            symbols.append(symbol)
            seen.add(symbol)

    if not symbols:
        return {}

    yahoo = YahooFinanceProvider()

    market_collector = MarketCollector(yfinance=yahoo)

    enricher_registry = default_registry()
    profile_registry = default_profile_registry()

    planner = ProfilePlanner(enricher_registry, profile_registry, )

    plan = planner.plan(CORE_MARKET_PROFILE, available={"price.close"}, )

    if not plan.is_executable:
        raise RuntimeError(
            "Basic market enrichment plan is not executable. "
            f"Missing capabilities: {sorted(plan.missing_capabilities)}"
        )

    results: dict[str, Any] = {}

    try:
        for symbol in symbols:
            collected = market_collector.daily_history(
                symbol=symbol,
                period=HISTORY_PERIOD,
                sources=("yfinance",),
            )

            if collected.errors:
                results[symbol] = {
                    "status": "error",
                    "errors": collected.errors,
                    "issues": collected.issues,
                }
                continue

            if not collected.records:
                results[symbol] = {
                    "status": "empty",
                    "errors": [],
                    "issues": collected.issues,
                }
                continue

            instrument_id = collected.records[0].instrument_id

            context = EnrichmentContext(
                records=collected.records,
                instrument_id=instrument_id,
                metadata={
                    "requested_symbol": symbol,
                    "source": "yfinance",
                    "history_period": HISTORY_PERIOD,
                },
            )

            enriched = execute_plan(context, plan, )

            enriched.metadata.update(
                {
                    "requested_symbol": symbol,
                    "instrument_id": instrument_id,
                    "history_period": HISTORY_PERIOD,
                    "collected_record_count": len(collected.records),
                    "collection_errors": collected.errors,
                    "collection_issues": collected.issues,
                }
            )

            results[symbol] = {
                "status": "ok",
                "result": enriched,
            }

    finally:
        yahoo  # provider is lightweight; no explicit close required

    return results


main_callable = enrich_equities_basic


if __name__ == '__main__':
    data = enrich_equities_basic("RELIANCE", "PINELABS")
    import json
    from pydantic import BaseModel

    def pydantic_encoder(obj):
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode='json')
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


    print(json.dumps(data, default=pydantic_encoder))

