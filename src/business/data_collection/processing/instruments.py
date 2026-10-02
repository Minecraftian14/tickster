from __future__ import annotations

from collections.abc import Iterable

from data_collection.domains.models import Instrument


def canonical_instrument_id(*, isin: str | None, exchange: str | None, symbol: str) -> str:
    """Return a stable security id for the equity domain."""
    if isin:
        return isin.upper()
    if exchange:
        return f"{exchange.upper()}:{symbol.upper()}"
    return symbol.upper()


def deduplicate_instruments(items: Iterable[Instrument]) -> list[Instrument]:
    """Prefer the latest observed record for a canonical instrument id."""
    by_id: dict[str, Instrument] = {}
    for item in items:
        by_id[item.instrument_id] = item
    return list(by_id.values())
