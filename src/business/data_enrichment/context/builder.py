from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Iterable

from ..core.hashing import stable_id
from ..models import DerivedObservation, DerivedSeries, DerivedSeriesPoint, DerivedSummary, EnrichmentResult
from .models import ContextItemRef, ContextPack, ContextPackProfile, ContextSectionSpec, _MutableBudget


class ContextPackBuilder:
    """Build compact, deterministic analytical views from enrichment results.

    The builder never recalculates metrics. It selects existing derived outputs,
    filters point-in-time series points when requested, and truncates series by
    a declared budget. The full enrichment results remain unchanged.
    """

    def build(
        self,
        results: Iterable[EnrichmentResult],
        profile: ContextPackProfile,
        *,
        instrument_id: str | None = None,
        as_of: datetime | None = None,
    ) -> ContextPack:
        observations, series, summaries = self._collect(results, instrument_id=instrument_id)
        budget = _MutableBudget(
            max_items=profile.max_items,
            max_points=profile.max_points,
            tail_series_points=profile.tail_series_points,
        )

        selected_observations: list[DerivedObservation] = []
        selected_series: list[DerivedSeries] = []
        selected_summaries: list[DerivedSummary] = []
        refs: list[ContextItemRef] = []
        selected_ids: set[str] = set()
        section_counts: dict[str, int] = defaultdict(int)
        omitted_points_total = 0
        omitted_items_total = 0

        for section in profile.sections:
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

        # If no sections were specified, produce an explicitly empty pack rather than
        # silently selecting everything and defeating the purpose of a bounded context.
        pack_id = stable_id(
            "context.pack",
            profile.name,
            profile.model_dump(mode="json"),
            instrument_id,
            as_of.isoformat() if as_of else None,
            [ref.model_dump(mode="json") for ref in refs],
        )
        return ContextPack(
            pack_id=pack_id,
            profile=profile.name,
            profile_version=profile.version,
            instrument_id=instrument_id,
            as_of=as_of,
            observations=selected_observations,
            series=selected_series,
            summaries=selected_summaries,
            items=refs,
            metadata={
                "sections": [s.name for s in profile.sections],
                "section_counts": dict(section_counts),
                "max_items": profile.max_items,
                "max_points": profile.max_points,
                "included_items": budget.item_count,
                "included_points": budget.point_count,
                "omitted_points": omitted_points_total,
                "omitted_items": omitted_items_total,
                "selection_is_lossy": bool(omitted_points_total or omitted_items_total),
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
