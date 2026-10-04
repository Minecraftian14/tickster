from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Iterable

from data_foundation.temporal import is_visible_at

from ..core.hashing import stable_id
from ..core.context import EnrichmentContext
from ..models import DerivedObservation, DerivedSeries, DerivedSeriesPoint, DerivedSummary, EnrichmentResult
from .models import ContextItemRef, ContextPack, ContextPackProfile, ContextSectionSpec, _MutableBudget


class ContextPackBuilder:
    """Build bounded, deterministic research contexts.

    Context packs can contain two kinds of information:
      * selected canonical source records that may never have participated in an
        enrichment calculation but are still useful to research;
      * selected deterministic enrichment outputs.

    The builder only selects data. It does not serialize or otherwise simplify
    records for an LLM; that responsibility belongs to ``data_representation``.
    """

    def build(
        self,
        results: Iterable[EnrichmentResult],
        profile: ContextPackProfile,
        *,
        instrument_id: str | None = None,
        as_of: datetime | None = None,
        source_records: Iterable[Any] = (),
    ) -> ContextPack:
        observations, series, summaries = self._collect(results, instrument_id=instrument_id)
        source_records = self._select_source_records(
            source_records,
            instrument_id=instrument_id,
            as_of=as_of,
        )
        budget = _MutableBudget(
            max_items=profile.max_items,
            max_points=profile.max_points,
            tail_series_points=profile.tail_series_points,
        )

        selected_source_records: list[Any] = []
        selected_observations: list[DerivedObservation] = []
        selected_series: list[DerivedSeries] = []
        selected_summaries: list[DerivedSummary] = []
        refs: list[ContextItemRef] = []
        selected_ids: set[str] = set()
        selected_source_ids: set[str] = set()
        section_counts: dict[str, int] = defaultdict(int)
        omitted_points_total = 0
        omitted_items_total = 0
        omitted_source_records_total = 0

        for section in profile.sections:
            if section.include_source_records:
                source_items = self._match_source_records(source_records, section)
                if section.max_source_records is not None:
                    limit = max(section.max_source_records, 0)
                    if len(source_items) > limit:
                        omitted_source_records_total += len(source_items) - limit
                    if section.tail_source_records:
                        source_items = source_items[-limit:] if limit else []
                    else:
                        source_items = source_items[:limit]
                for record in source_items:
                    rid = self._record_id(record)
                    if rid and rid in selected_source_ids:
                        continue
                    selected_source_records.append(record)
                    if rid:
                        selected_source_ids.add(rid)
                        refs.append(ContextItemRef(kind="record", record_id=rid, section=section.name))
                    else:
                        refs.append(ContextItemRef(kind="record", section=section.name))
                    section_counts[section.name] += 1

            # Summaries first: they are the most compressed representation.
            if section.include_summaries:
                for summary in summaries:
                    if not self._matches_summary(summary, section):
                        continue
                    if summary.derived_id in selected_ids:
                        continue
                    if not budget.can_add_item():
                        omitted_items_total += 1
                        continue
                    selected_summaries.append(summary)
                    refs.append(ContextItemRef(kind="summary", derived_id=summary.derived_id, section=section.name))
                    budget.item_count += 1
                    selected_ids.add(summary.derived_id)
                    section_counts[section.name] += 1

            if section.include_observations:
                for observation in observations:
                    if not self._matches_observation(observation, section):
                        continue
                    if observation.derived_id in selected_ids:
                        continue
                    if not budget.can_add_item():
                        omitted_items_total += 1
                        continue
                    if as_of is not None and observation.available_at is not None and observation.available_at > as_of:
                        continue
                    selected_observations.append(observation)
                    refs.append(ContextItemRef(kind="observation", derived_id=observation.derived_id, section=section.name))
                    budget.item_count += 1
                    selected_ids.add(observation.derived_id)
                    section_counts[section.name] += 1

            if section.include_series:
                for item in series:
                    if not self._matches_series(item, section):
                        continue
                    if item.derived_id in selected_ids:
                        continue
                    if not budget.can_add_item():
                        omitted_items_total += 1
                        continue
                    points = self._visible_points(item.points, as_of)
                    if not points:
                        continue
                    if section.max_points_per_series is not None:
                        points = self._tail(points, section.max_points_per_series) if profile.tail_series_points else points[:section.max_points_per_series]
                    points, omitted = self._fit_points_to_budget(points, budget)
                    if not points:
                        continue
                    selected = item.model_copy(update={"points": points})
                    selected_series.append(selected)
                    refs.append(ContextItemRef(kind="series", derived_id=item.derived_id, section=section.name, included_points=len(points), omitted_points=omitted))
                    budget.item_count += 1
                    budget.point_count += len(points)
                    selected_ids.add(item.derived_id)
                    omitted_points_total += omitted
                    section_counts[section.name] += 1

        pack_id = stable_id(
            "context.pack",
            profile.name,
            profile.model_dump(mode="json"),
            instrument_id,
            as_of.isoformat() if as_of else None,
            [self._record_id(record) or self._payload_fingerprint(record) for record in selected_source_records],
            [ref.model_dump(mode="json") for ref in refs],
        )
        return ContextPack(
            pack_id=pack_id,
            profile=profile.name,
            profile_version=profile.version,
            instrument_id=instrument_id,
            as_of=as_of,
            source_records=selected_source_records,
            observations=selected_observations,
            series=selected_series,
            summaries=selected_summaries,
            items=refs,
            metadata={
                "sections": [s.name for s in profile.sections],
                "section_counts": dict(section_counts),
                "max_items": profile.max_items,
                "max_points": profile.max_points,
                "included_source_records": len(selected_source_records),
                "omitted_source_records": omitted_source_records_total,
                "included_items": budget.item_count,
                "included_points": budget.point_count,
                "omitted_points": omitted_points_total,
                "omitted_items": omitted_items_total,
                "selection_is_lossy": bool(omitted_points_total or omitted_items_total or omitted_source_records_total),
                "drilldown_available": True,
            },
        )

    @staticmethod
    def _collect(
        results: Iterable[EnrichmentResult], *, instrument_id: str | None
    ) -> tuple[list[DerivedObservation], list[DerivedSeries], list[DerivedSummary]]:
        observations: dict[str, DerivedObservation] = {}
        series: dict[str, DerivedSeries] = {}
        summaries: dict[str, DerivedSummary] = {}
        for result in results:
            for item in result.observations:
                if instrument_id is None or item.instrument_id in {None, instrument_id}:
                    observations.setdefault(item.derived_id, item)
            for item in result.series:
                if instrument_id is None or item.instrument_id in {None, instrument_id}:
                    series.setdefault(item.derived_id, item)
            for item in result.summaries:
                if instrument_id is None or item.instrument_id in {None, instrument_id}:
                    summaries.setdefault(item.derived_id, item)
        return list(observations.values()), list(series.values()), list(summaries.values())

    @classmethod
    def _select_source_records(
        cls,
        records: Iterable[Any],
        *,
        instrument_id: str | None,
        as_of: datetime | None,
    ) -> list[Any]:
        selected = []
        for record in records:
            if instrument_id is not None and not cls._matches_instrument(record, instrument_id):
                continue
            if as_of is not None and not is_visible_at(record, as_of, strict=True):
                continue
            selected.append(record)
        return selected

    @staticmethod
    def _match_source_records(records: Iterable[Any], section: ContextSectionSpec) -> list[Any]:
        wanted = set(section.source_record_types)
        prefixes = tuple(section.source_record_type_prefixes)
        matched: list[Any] = []
        for record in records:
            record_type = ContextPackBuilder._record_type(record)
            if wanted or prefixes:
                if record_type not in wanted and not any(record_type.startswith(prefix) for prefix in prefixes):
                    continue
            matched.append(record)
        return matched

    @staticmethod
    def _matches_instrument(record: Any, instrument_id: str) -> bool:
        rid = getattr(record, "instrument_id", None)
        payload = getattr(record, "payload", None)
        if rid is None and isinstance(payload, dict):
            rid = payload.get("instrument_id")
        if rid == instrument_id:
            return True
        rids = getattr(record, "instrument_ids", None)
        if rids is None and isinstance(payload, dict):
            rids = payload.get("instrument_ids", [])
        return instrument_id in (rids or [])

    @staticmethod
    def _record_type(record: Any) -> str:
        value = getattr(record, "record_type", None)
        if value:
            return str(value)
        return record.__class__.__name__

    @staticmethod
    def _record_id(record: Any) -> str | None:
        value = getattr(record, "record_id", None)
        if value:
            return str(value)
        for key in ("event_id", "filing_id", "document_id", "news_id", "observation_id", "relationship_id"):
            value = getattr(record, key, None)
            if value:
                return str(value)
        return None

    @staticmethod
    def _payload_fingerprint(record: Any) -> str:
        payload = EnrichmentContext.payload(record)
        if payload:
            return stable_id("context.source", payload)
        return stable_id("context.source", repr(record))

    @staticmethod
    def _visible_points(points: list[DerivedSeriesPoint], as_of: datetime | None) -> list[DerivedSeriesPoint]:
        if as_of is None:
            return list(points)
        return [p for p in points if p.available_at is None or p.available_at <= as_of]

    @staticmethod
    def _tail(points: list[DerivedSeriesPoint], limit: int) -> list[DerivedSeriesPoint]:
        if limit <= 0:
            return []
        return points[-limit:]

    @staticmethod
    def _fit_points_to_budget(points: list[DerivedSeriesPoint], budget: _MutableBudget) -> tuple[list[DerivedSeriesPoint], int]:
        remaining = budget.remaining_points()
        if remaining is None or len(points) <= remaining:
            return points, 0
        if remaining <= 0:
            return [], len(points)
        selected = points[-remaining:] if budget.tail_series_points else points[:remaining]
        return selected, len(points) - len(selected)

    @staticmethod
    def _matches_summary(summary: DerivedSummary, section: ContextSectionSpec) -> bool:
        if section.include_all_summaries:
            return True
        if not (section.summary_types or section.summary_prefixes):
            return False
        if summary.summary_type in section.summary_types:
            return True
        return any(summary.summary_type.startswith(prefix) for prefix in section.summary_prefixes)

    @staticmethod
    def _matches_series(series: DerivedSeries, section: ContextSectionSpec) -> bool:
        if series.metric in section.metrics:
            return True
        if section.metric_prefixes and any(series.metric.startswith(prefix) for prefix in section.metric_prefixes):
            return True
        return False

    @staticmethod
    def _matches_observation(observation: DerivedObservation, section: ContextSectionSpec) -> bool:
        if observation.metric in section.metrics:
            return True
        return bool(section.metric_prefixes and any(observation.metric.startswith(prefix) for prefix in section.metric_prefixes))
