from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from data_collection.domains.models import PriceBar


def deduplicate_price_bars(items: Iterable[PriceBar], *, preserve_sources: bool = True) -> list[PriceBar]:
    """Deduplicate observations while retaining independent source observations by default."""
    by_key: dict[tuple, PriceBar] = {}
    for item in items:
        source = item.provenance.source if preserve_sources else None
        by_key[(item.instrument_id, item.timeframe, item.timestamp, source)] = item
    return sorted(by_key.values(), key=lambda x: (x.instrument_id, x.timeframe, x.timestamp, x.provenance.source))


def collapse_price_sources(items: Iterable[PriceBar]) -> list[PriceBar]:
    """Explicitly collapse multiple source observations into one last-seen record."""
    return deduplicate_price_bars(items, preserve_sources=False)


def validate_price_bars(items: Iterable[PriceBar]) -> list[str]:
    """Return data-quality findings without mutating collected records."""
    findings: list[str] = []
    for item in items:
        supplied = [x for x in (item.open, item.high, item.low, item.close) if x is not None]
        if supplied and any(x <= 0 for x in supplied):
            findings.append(f"{item.instrument_id} {item.timestamp}: non-positive price")
        if item.high is not None and item.low is not None and item.high < item.low:
            findings.append(f"{item.instrument_id} {item.timestamp}: high < low")
        if item.open is not None and item.high is not None and item.open > item.high:
            findings.append(f"{item.instrument_id} {item.timestamp}: open > high")
        if item.open is not None and item.low is not None and item.open < item.low:
            findings.append(f"{item.instrument_id} {item.timestamp}: open < low")
        if item.close is not None and item.high is not None and item.close > item.high:
            findings.append(f"{item.instrument_id} {item.timestamp}: close > high")
        if item.close is not None and item.low is not None and item.close < item.low:
            findings.append(f"{item.instrument_id} {item.timestamp}: close < low")
        if item.volume is not None and item.volume < 0:
            findings.append(f"{item.instrument_id} {item.timestamp}: negative volume")
        if item.delivery_percent is not None and not Decimal("0") <= item.delivery_percent <= Decimal("100"):
            findings.append(f"{item.instrument_id} {item.timestamp}: invalid delivery_percent")
    return findings


def reconcile_prices(items: Iterable[PriceBar], *, tolerance: Decimal = Decimal("0.0001")) -> list[dict]:
    """Report material cross-source close-price gaps without choosing a winner."""
    groups: dict[tuple[str, str, object], list[PriceBar]] = defaultdict(list)
    for item in items:
        groups[(item.instrument_id, item.timeframe, item.timestamp)].append(item)

    findings: list[dict] = []
    for key, observations in groups.items():
        closes = [x.close for x in observations if x.close is not None]
        if len(closes) < 2:
            continue
        spread = max(closes) - min(closes)
        baseline = max(abs(x) for x in closes)
        if baseline == 0:
            continue
        relative_spread = spread / baseline
        if relative_spread > tolerance:
            findings.append({
                "key": key,
                "relative_close_spread": relative_spread,
                "sources": [x.provenance.source for x in observations],
                "closes": [str(x.close) for x in observations],
            })
    return findings
