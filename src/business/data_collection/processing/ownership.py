from __future__ import annotations

from collections import OrderedDict
from typing import Iterable

from data_collection.domains.ownership import InsiderTransaction, LargeDeal
from data_collection.domains.models import ShareholdingSnapshot


def deduplicate_shareholding(items: Iterable[ShareholdingSnapshot]) -> list[ShareholdingSnapshot]:
    out: OrderedDict[tuple, ShareholdingSnapshot] = OrderedDict()
    for item in items:
        out[(item.instrument_id, item.period_end)] = item
    return list(out.values())


def deduplicate_insider_transactions(items: Iterable[InsiderTransaction]) -> list[InsiderTransaction]:
    out: OrderedDict[str, InsiderTransaction] = OrderedDict()
    for item in items:
        out[item.event_id] = item
    return list(out.values())


def deduplicate_large_deals(items: Iterable[LargeDeal]) -> list[LargeDeal]:
    out: OrderedDict[str, LargeDeal] = OrderedDict()
    for item in items:
        out[item.event_id] = item
    return list(out.values())
