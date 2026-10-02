from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedObservation, DerivedSummary, EnrichmentIssue, EnrichmentResult
from .common import as_datetime, holder_value, record_date


class ShareholdingChangeEnricher:
    """Describe period-over-period changes in ownership categories."""

    name = "ownership.shareholding_changes"
    version = "0.5.0"
    requires = frozenset({"shareholding.snapshot"})
    provides = frozenset({"ownership.shareholding_change", "ownership.shareholding_summary"})

    HOLDER_FIELDS = {
        "promoter": ("promoter_and_promoter_group", "promoter", "pr_and_prgrp"),
        "public": ("public", "public_val", "public_shareholding"),
        "employee_trusts": ("employee_trusts", "employeeTrusts"),
        "fii": ("fii", "fii_shareholding", "foreign_institutional_investors", "fpi"),
        "dii": ("dii", "dii_shareholding", "domestic_institutional_investors"),
    }

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        records = [r for r in context.records_for_instrument() if record_date(r) is not None]
        records.sort(key=lambda r: record_date(r) or datetime.min.date())
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if len(records) < 2:
            result.issues.append(EnrichmentIssue(code="insufficient_shareholding_history", severity="warning", message="At least two dated shareholding snapshots are required."))
            return result

        observations: list[DerivedObservation] = []
        calculated_at = datetime.now(timezone.utc)
        latest_values: dict[str, Any] = {"period_end": record_date(records[-1]).isoformat() if record_date(records[-1]) else None}
        latest_record = records[-1]
        for field, aliases in self.HOLDER_FIELDS.items():
            current = holder_value(latest_record, aliases)
            previous_record = next((r for r in reversed(records[:-1]) if holder_value(r, aliases) is not None), None)
            previous = holder_value(previous_record, aliases) if previous_record is not None else None
            change = None if current is None or previous is None else current - previous
            latest_values[f"{field}_current"] = current
            latest_values[f"{field}_change"] = change
            if change is None:
                continue
            source_records = [latest_record, previous_record] if previous_record is not None else [latest_record]
            lineage = context.lineage_for_records(source_records, algorithm=self.name, algorithm_version=self.version, parameters={"holder": field}, calculated_at=calculated_at)
            observed_at = as_datetime(record_date(latest_record))
            available_at = max((EnrichmentContext.temporal(r).available_at for r in source_records if EnrichmentContext.temporal(r).available_at is not None), default=None)
            observations.append(DerivedObservation(
                derived_id=stable_id(self.name, context.instrument_id, field, record_date(latest_record), change),
                instrument_id=context.instrument_id,
                metric=f"shareholding_change_{field}",
                value=change,
                unit="percentage_points",
                observed_at=observed_at,
                available_at=available_at,
                lineage=lineage,
                metadata={"current": current, "previous": previous, "period_end": record_date(latest_record)},
            ))

        lineage = context.lineage_for_records(records, algorithm=self.name, algorithm_version=self.version, parameters={}, calculated_at=calculated_at)
        result.observations.extend(observations)
        result.summaries.append(DerivedSummary(
            derived_id=stable_id(self.name, context.instrument_id, latest_values),
            instrument_id=context.instrument_id,
            summary_type="shareholding_latest_change",
            values=latest_values,
            lineage=lineage,
            metadata={"snapshot_count": len(records)},
        ))
        return result
