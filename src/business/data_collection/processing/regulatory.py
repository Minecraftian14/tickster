from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from data_collection.domains.regulatory import RegulatoryItem


def deduplicate_regulatory(records: Iterable[RegulatoryItem]) -> list[RegulatoryItem]:
    latest: dict[str, RegulatoryItem] = {}
    for record in records:
        latest[record.regulatory_id] = record
    return list(latest.values())


def group_regulatory_by_category(records: Iterable[RegulatoryItem]) -> dict[str, list[RegulatoryItem]]:
    grouped: dict[str, list[RegulatoryItem]] = defaultdict(list)
    for record in records:
        grouped[record.category].append(record)
    return dict(grouped)


def titles_containing(records: Iterable[RegulatoryItem], text: str) -> list[RegulatoryItem]:
    needle = text.casefold()
    return [record for record in records if needle in record.title.casefold()]
