from __future__ import annotations

from datetime import datetime, timezone

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSeries, DerivedSeriesPoint, DerivedSummary, EnrichmentIssue, EnrichmentResult
from .common import delivery_percent, prepare_price_records, traded_value, volume


class LiquidityEnricher:
    name = "market.liquidity"
    version = "0.2.0"
    requires = frozenset({"price.close"})
    provides = frozenset({"market.liquidity"})

    def __init__(self, windows: tuple[int, ...] = (20, 60)) -> None:
        self.windows = tuple(sorted(set(windows)))

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        prepared = prepare_price_records(context)
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if not prepared:
            result.issues.append(EnrichmentIssue(code="no_observations", severity="warning", message="No valid price observations are available."))
            return result
        for window in self.windows:
            sample = prepared[-window:]
            vols = [volume(record) for _, record, _ in sample]
            vals = [traded_value(record) for _, record, _ in sample]
            delivery = [delivery_percent(record) for _, record, _ in sample]
            volume_values = [x for x in vols if x is not None]
            value_values = [x for x in vals if x is not None]
            delivery_values = [x for x in delivery if x is not None]
            values = {
                "window": window,
                "observations": len(sample),
                "avg_volume": sum(volume_values) / len(volume_values) if volume_values else None,
                "avg_traded_value": sum(value_values) / len(value_values) if value_values else None,
                "avg_delivery_percent": sum(delivery_values) / len(delivery_values) if delivery_values else None,
                "volume_coverage": len(volume_values) / len(sample),
                "traded_value_coverage": len(value_values) / len(sample),
                "delivery_coverage": len(delivery_values) / len(sample),
            }
            result.summaries.append(DerivedSummary(
                derived_id=stable_id(self.name, context.instrument_id, window, values),
                instrument_id=context.instrument_id,
                summary_type="liquidity_summary",
                values=values,
                lineage=context.lineage_for_records([x[1] for x in sample], algorithm=self.name, algorithm_version=self.version, parameters={"window": window}),
            ))
        return result
