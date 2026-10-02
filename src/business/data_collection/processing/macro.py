from __future__ import annotations

from collections import defaultdict
from data_collection.domains.models import MacroObservation


def deduplicate_macro(observations: list[MacroObservation]) -> list[MacroObservation]:
    best: dict[tuple[str, object], MacroObservation] = {}
    for item in observations:
        key = (item.series_id, item.observation_date)
        best[key] = item
    return sorted(best.values(), key=lambda x: (x.series_id, x.observation_date))


def group_macro_by_series(observations: list[MacroObservation]) -> dict[str, list[MacroObservation]]:
    grouped: dict[str, list[MacroObservation]] = defaultdict(list)
    for item in deduplicate_macro(observations):
        grouped[item.series_id].append(item)
    return dict(grouped)
