from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from data_foundation import CanonicalRecord, SourceObservation

from data_enrichment import (
    CORE_MARKET_PROFILE,
    EnrichmentContext,
    EnrichmentPipeline,
    EnrichmentRegistry,
    default_registry,
    ReturnSummaryEnricher,
    SimpleReturnEnricher,
    DerivedSeries,
    FinanceToolkitBackend,
    QuantStatsBackend,
    PandasTABackend,
)


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def bar(record_id: str, instrument_id: str, close: float, day: int):
    ts = BASE + timedelta(days=day)
    return CanonicalRecord(
        record_id=record_id,
        domain="market",
        record_type="PriceBar",
        payload={
            "instrument_id": instrument_id,
            "timestamp": ts,
            "close": close,
            "published_at": ts,
        },
    )


def test_context_filters_point_in_time_and_payload():
    records = [
        bar("a", "REL", 100, 0),
        bar("b", "REL", 110, 1),
        bar("future", "REL", 130, 3),
    ]
    context = EnrichmentContext(records, as_of=BASE + timedelta(days=1, hours=1), instrument_id="REL")
    selected = context.records_for_instrument()
    assert [r.record_id for r in selected] == ["a", "b"]
    assert EnrichmentContext.payload(selected[0])["close"] == 100


def test_simple_return_enricher_is_deterministic():
    context = EnrichmentContext([
        bar("a", "REL", 100, 0),
        bar("b", "REL", 110, 1),
        bar("c", "REL", 121, 2),
    ], instrument_id="REL")
    result = SimpleReturnEnricher().enrich(context)
    assert len(result.series) == 1
    assert [round(p.value, 8) for p in result.series[0].points] == [0.1, 0.1]
    assert result.series[0].lineage.source_record_ids == ["a", "b", "c"]


def test_return_summary():
    context = EnrichmentContext([bar("a", "REL", 100, 0), bar("b", "REL", 120, 1)], instrument_id="REL")
    result = ReturnSummaryEnricher().enrich(context)
    assert result.summaries[0].values["cumulative_return"] == pytest.approx(0.2)


def test_registry_pipeline_and_capability_planning():
    registry = EnrichmentRegistry()
    registry.register(SimpleReturnEnricher())
    registry.register(ReturnSummaryEnricher())
    pipeline = EnrichmentPipeline(registry)
    names = pipeline.registry.names()
    assert names == ("market.return_summary", "market.simple_return")
    plan = pipeline.plan(["market.simple_return", "market.return_summary"], available={"price.close"})
    assert [x.name for x in plan] == ["market.simple_return", "market.return_summary"]


def test_pipeline_combines_outputs():
    registry = EnrichmentRegistry()
    registry.register(SimpleReturnEnricher())
    registry.register(ReturnSummaryEnricher())
    pipeline = EnrichmentPipeline(registry)
    context = EnrichmentContext([bar("a", "REL", 100, 0), bar("b", "REL", 110, 1)], instrument_id="REL")
    result = pipeline.run(context, ["market.simple_return", "market.return_summary"], available={"price.close"})
    assert len(result.series) == 1
    assert len(result.summaries) == 1


def test_lineage_has_algorithm_version_and_sources():
    context = EnrichmentContext([bar("a", "REL", 100, 0), bar("b", "REL", 110, 1)], instrument_id="REL")
    result = SimpleReturnEnricher().enrich(context)
    lineage = result.series[0].lineage
    assert lineage.algorithm == "market.simple_return"
    assert lineage.algorithm_version == "0.1.0"
    assert lineage.source_record_ids == ["a", "b"]


def test_lineage_can_include_foundation_observations_and_raw_refs():
    records = [bar("a", "REL", 100, 0), bar("b", "REL", 110, 1)]
    observations = [
        SourceObservation(observation_id="o1", entity_key="REL", field="close", value=100, source="nse", raw_ref="raw-1", canonical_record_id="a"),
        SourceObservation(observation_id="o2", entity_key="REL", field="close", value=110, source="nse", raw_ref="raw-2", canonical_record_id="b"),
    ]
    records[0].source_observation_ids = ["o1"]
    records[1].source_observation_ids = ["o2"]
    context = EnrichmentContext(records, instrument_id="REL", source_observations=observations)
    result = SimpleReturnEnricher().enrich(context)
    lineage = result.series[0].lineage
    assert lineage.source_observation_ids == ["o1", "o2"]
    assert lineage.raw_artifact_ids == ["raw-1", "raw-2"]


@pytest.mark.parametrize("backend_cls", [FinanceToolkitBackend, QuantStatsBackend, PandasTABackend])
def test_optional_backends_are_lazy(backend_cls):
    backend = backend_cls()
    assert backend.name
    assert backend.capabilities
    assert backend.dependency_name


def test_default_registry_is_ready_to_use():
    registry = default_registry()
    assert "market.returns" in registry.names()
    assert "market.multi_resolution" in registry.names()
