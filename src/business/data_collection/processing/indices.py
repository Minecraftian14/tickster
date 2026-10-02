from __future__ import annotations

from data_collection.domains.indices import IndexConstituent, IndexSnapshot


def deduplicate_index_snapshots(records: list[IndexSnapshot]) -> list[IndexSnapshot]:
    seen: dict[tuple[str, str], IndexSnapshot] = {}
    for record in records:
        key = (record.index_symbol, record.timestamp.isoformat())
        seen[key] = record
    return list(seen.values())


def deduplicate_index_constituents(records: list[IndexConstituent]) -> list[IndexConstituent]:
    seen: dict[tuple[str, str], IndexConstituent] = {}
    for record in records:
        key = (record.index_symbol, record.symbol)
        seen[key] = record
    return list(seen.values())
