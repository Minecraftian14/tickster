from __future__ import annotations

from collections import OrderedDict
from typing import Iterable

from data_collection.domains.models import CorporateAction
from data_collection.domains.events import CompanyEvent


def deduplicate_corporate_actions(items: Iterable[CorporateAction]) -> list[CorporateAction]:
    out: OrderedDict[tuple, CorporateAction] = OrderedDict()
    for item in items:
        key = (
            item.instrument_id, item.action_type, item.announcement_date,
            item.ex_date, item.record_date, item.amount, item.ratio,
        )
        out[key] = item
    return list(out.values())


def deduplicate_company_events(items: Iterable[CompanyEvent]) -> list[CompanyEvent]:
    out: OrderedDict[str, CompanyEvent] = OrderedDict()
    for item in items:
        out[item.event_id] = item
    return list(out.values())
