from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSeries, DerivedSeriesPoint, DerivedSummary, EnrichmentIssue, EnrichmentResult
from .common import prepare_price_records


class MultiResolutionSummaryEnricher:
    name = "market.multi_resolution"
    version = "0.2.0"
    requires = frozenset({"price.close"})
    provides = frozenset({"market.multi_resolution"})

    def __init__(self, resolutions: tuple[str, ...] = ("week", "month")) -> None:
        allowed = {"week", "month"}
        unknown = set(resolutions) - allowed
        if unknown:
            raise ValueError(f"Unsupported resolutions: {sorted(unknown)}")
        self.resolutions = tuple(dict.fromkeys(resolutions))

    @staticmethod
    def _period(ts: datetime, resolution: str) -> tuple[int, int]:
        if resolution == "week":
            iso = ts.isocalendar()
            return iso.year, iso.week
        return ts.year, ts.month

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        prepared = prepare_price_records(context)
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if not prepared:
            result.issues.append(EnrichmentIssue(code="no_observations", severity="warning", message="No valid closes are available."))
            return result
        for resolution in self.resolutions:
            buckets: dict[tuple[int, int], list[tuple[datetime, Any, float]]] = defaultdict(list)
            for item in prepared:
                buckets[self._period(item[0], resolution)].append(item)
            points: list[DerivedSeriesPoint] = []
            periods = []
            for key, items in sorted(buckets.items()):
                first = items[0][2]
                last = items[-1][2]
                change = last / first - 1.0 if first > 0 else None
                if change is None:
                    continue
                points.append(DerivedSeriesPoint(timestamp=items[-1][0], value=change, source_record_ids=[x for x in (context.record_id(items[0][1]), context.record_id(items[-1][1])) if x]))
                periods.append({"period": key, "observations": len(items), "start_close": first, "end_close": last, "return": change})
            result.series.append(DerivedSeries(
                derived_id=stable_id(self.name, context.instrument_id, resolution, periods),
                instrument_id=context.instrument_id,
                metric=f"{resolution}_return",
                unit="fraction",
                points=points,
                lineage=context.lineage_for_records([x[1] for x in prepared], algorithm=self.name, algorithm_version=self.version, parameters={"resolution": resolution}, calculated_at=datetime.now(timezone.utc)),
                metadata={"resolution": resolution},
            ))
            result.summaries.append(DerivedSummary(
                derived_id=stable_id(self.name, context.instrument_id, resolution, periods),
                instrument_id=context.instrument_id,
                summary_type=f"{resolution}_aggregation",
                values={"periods": len(periods), "latest_period": periods[-1] if periods else None},
                lineage=context.lineage_for_records([x[1] for x in prepared], algorithm=self.name, algorithm_version=self.version, parameters={"resolution": resolution}),
                metadata={"resolution": resolution},
            ))
        return result
