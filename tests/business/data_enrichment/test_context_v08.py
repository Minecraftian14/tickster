from datetime import datetime, timedelta, timezone

from data_foundation import CanonicalRecord

from data_enrichment import (
    COMPACT_RESEARCH_CONTEXT,
    ContextPackBuilder,
    ContextPackProfile,
    ContextSectionSpec,
    EnrichmentContext,
    MultiResolutionSummaryEnricher,
    ReturnSeriesEnricher,
    ReturnSummaryEnricher,
)

BASE = datetime(2020, 1, 1, tzinfo=timezone.utc)


def bar(i: int, close: float, *, available_offset: int | None = None) -> CanonicalRecord:
    ts = BASE + timedelta(days=i)
    payload = {
        "instrument_id": "REL",
        "timestamp": ts,
        "close": close,
        "published_at": ts,
    }
    if available_offset is not None:
        payload["available_at"] = BASE + timedelta(days=available_offset)
    return CanonicalRecord(record_id=f"r{i}", domain="market", record_type="PriceBar", payload=payload)


def results():
    context = EnrichmentContext([bar(i, 100 + i) for i in range(80)], instrument_id="REL")
    return [
        ReturnSeriesEnricher().enrich(context),
        ReturnSummaryEnricher().enrich(context),
        MultiResolutionSummaryEnricher().enrich(context),
    ]


def test_compact_context_selects_summaries_and_multi_resolution_series():
    out = ContextPackBuilder().build(results(), COMPACT_RESEARCH_CONTEXT, instrument_id="REL")
    assert out.profile == "compact_research"
    assert out.item_count > 0
    assert any(item.summary_type == "return_summary" for item in out.summaries) or any(item.summary_type == "return_horizons" for item in out.summaries)
    assert any(item.metric == "week_return" for item in out.series)
    assert out.point_count <= 500


def test_pack_budget_trims_series_from_the_tail():
    profile = ContextPackProfile(
        name="tiny",
        sections=(ContextSectionSpec(name="recent", metrics=("return_1p",), max_points_per_series=10, include_summaries=False),),
        max_items=2,
        max_points=3,
    )
    out = ContextPackBuilder().build(results(), profile, instrument_id="REL")
    series = out.series[0]
    assert len(series.points) == 3
    assert series.points[-1].timestamp > series.points[0].timestamp
    assert out.metadata["omitted_points"] > 0
    assert out.metadata["selection_is_lossy"] is True


def test_pack_is_deterministic_for_same_inputs():
    builder = ContextPackBuilder()
    a = builder.build(results(), COMPACT_RESEARCH_CONTEXT, instrument_id="REL")
    b = builder.build(results(), COMPACT_RESEARCH_CONTEXT, instrument_id="REL")
    assert a.pack_id == b.pack_id


def test_pack_deduplicates_same_derived_output_from_multiple_results():
    result = results()[0]
    out = ContextPackBuilder().build([result, result], COMPACT_RESEARCH_CONTEXT, instrument_id="REL")
    ids = [item.derived_id for item in out.items]
    assert len(ids) == len(set(ids))


def test_pack_filters_future_series_points_by_as_of_when_available_at_is_present():
    from data_enrichment import DerivedSeries, DerivedSeriesPoint, DerivationLineage, EnrichmentResult, stable_id

    result = EnrichmentResult(enricher="test", enricher_version="1.0.0")
    series = DerivedSeries(
        derived_id=stable_id("test.series"),
        instrument_id="REL",
        metric="return_1p",
        unit="fraction",
        points=[
            DerivedSeriesPoint(timestamp=BASE + timedelta(days=1), value=0.01, available_at=BASE + timedelta(days=1)),
            DerivedSeriesPoint(timestamp=BASE + timedelta(days=2), value=0.02, available_at=BASE + timedelta(days=2)),
        ],
        lineage=DerivationLineage(algorithm="test.series", algorithm_version="1.0.0", calculated_at=BASE),
    )
    result.series.append(series)
    profile = ContextPackProfile(
        name="temporal",
        sections=(ContextSectionSpec(name="returns", metrics=("return_1p",), max_points_per_series=10, include_summaries=False),),
    )
    out = ContextPackBuilder().build([result], profile, instrument_id="REL", as_of=BASE + timedelta(days=1, hours=12))
    assert out.point_count == 1
    assert out.series[0].points[0].timestamp == BASE + timedelta(days=1)


def test_empty_profile_is_explicitly_empty():
    profile = ContextPackProfile(name="empty")
    out = ContextPackBuilder().build(results(), profile, instrument_id="REL")
    assert out.item_count == 0
    assert out.metadata["drilldown_available"] is True


def test_builtin_profiles_expose_stable_versions_and_budgets():
    from data_enrichment import MEDIUM_RESEARCH_CONTEXT, FULL_RESEARCH_CONTEXT

    for profile in (COMPACT_RESEARCH_CONTEXT, MEDIUM_RESEARCH_CONTEXT, FULL_RESEARCH_CONTEXT):
        from data_enrichment import __version__
        assert profile.version == __version__
        assert profile.sections
        assert profile.max_items is not None
        assert profile.max_points is not None
        assert profile.max_items > 0
        assert profile.max_points > 0
