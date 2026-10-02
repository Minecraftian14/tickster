from __future__ import annotations

import math
from datetime import datetime, timezone

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSeries, DerivedSeriesPoint, DerivedSummary, EnrichmentIssue, EnrichmentResult
from .common import prepare_price_records


class ReturnSeriesEnricher:
    name = "market.returns"
    version = "0.2.0"
    requires = frozenset({"price.close"})
    provides = frozenset({"market.return", "market.log_return", "market.cumulative_return"})

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        prepared = prepare_price_records(context)
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if len(prepared) < 2:
            result.issues.append(EnrichmentIssue(code="insufficient_observations", severity="warning", message="At least two valid closes are required."))
            return result

        simple_points: list[DerivedSeriesPoint] = []
        log_points: list[DerivedSeriesPoint] = []
        cumulative = 1.0
        cumulative_points: list[DerivedSeriesPoint] = []

        for (prev_ts, prev_record, prev_close), (cur_ts, cur_record, cur_close) in zip(prepared, prepared[1:]):
            record_ids = [rid for record in (prev_record, cur_record) if (rid := context.record_id(record))]
            if prev_close <= 0 or cur_close <= 0:
                result.issues.append(EnrichmentIssue(
                    code="non_positive_price",
                    severity="error",
                    message="Returns require strictly positive consecutive closes.",
                    metric="return_1p",
                    record_ids=record_ids,
                ))
                continue
            simple = cur_close / prev_close - 1.0
            log = math.log(cur_close / prev_close)
            cumulative *= 1.0 + simple
            simple_points.append(DerivedSeriesPoint(timestamp=cur_ts, value=simple, source_record_ids=record_ids))
            log_points.append(DerivedSeriesPoint(timestamp=cur_ts, value=log, source_record_ids=record_ids))
            cumulative_points.append(DerivedSeriesPoint(timestamp=cur_ts, value=cumulative - 1.0, source_record_ids=record_ids))

        calculated_at = datetime.now(timezone.utc)
        all_records = [record for _, record, _ in prepared]
        lineage = context.lineage_for_records(all_records, algorithm=self.name, algorithm_version=self.version, parameters={}, calculated_at=calculated_at)
        for metric, points, unit in (
            ("return_1p", simple_points, "fraction"),
            ("log_return_1p", log_points, "log-return"),
            ("cumulative_return", cumulative_points, "fraction"),
        ):
            result.series.append(DerivedSeries(
                derived_id=stable_id(self.name, context.instrument_id, metric, [(p.timestamp.isoformat(), p.value) for p in points]),
                instrument_id=context.instrument_id,
                metric=metric,
                unit=unit,
                points=points,
                lineage=lineage,
                metadata={"frequency": "input-observation-frequency"},
            ))
        return result


class ReturnHorizonSummaryEnricher:
    name = "market.return_horizons"
    version = "0.2.0"
    requires = frozenset({"price.close"})
    provides = frozenset({"market.return_horizons"})

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        prepared = prepare_price_records(context)
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if len(prepared) < 2:
            result.issues.append(EnrichmentIssue(code="insufficient_observations", severity="warning", message="At least two closes are required."))
            return result
        horizons = {"1p": 1, "5p": 5, "21p": 21, "63p": 63, "126p": 126, "252p": 252}
        values: dict[str, float | None] = {}
        closes = [x[2] for x in prepared]
        for label, offset in horizons.items():
            values[f"return_{label}"] = closes[-1] / closes[-1 - offset] - 1.0 if len(closes) > offset and closes[-1 - offset] > 0 else None
        start = closes[0]
        end = closes[-1]
        span_days = max((prepared[-1][0] - prepared[0][0]).days, 0)
        values["cumulative_return"] = end / start - 1.0 if start > 0 else None
        values["calendar_span_days"] = span_days
        if start > 0 and end > 0 and span_days >= 365:
            years = span_days / 365.2425
            values["annualized_return"] = (end / start) ** (1 / years) - 1.0
        else:
            values["annualized_return"] = None
        result.summaries.append(DerivedSummary(
            derived_id=stable_id(self.name, context.instrument_id, values),
            instrument_id=context.instrument_id,
            summary_type="return_horizons",
            values=values,
            lineage=context.lineage_for_records([x[1] for x in prepared], algorithm=self.name, algorithm_version=self.version, parameters=horizons),
        ))
        return result
