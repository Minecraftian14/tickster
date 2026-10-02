from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace

from data_collection.domains.filings import DocumentAsset, Filing
from data_collection.domains.events import CompanyEvent
from data_collection.domains.models import Instrument, Provenance
from data_foundation import (
    CanonicalRecord,
    build_company_timeline,
    build_relationship_graph,
    RelationshipIndex,
    make_relationship,
)

UTC = timezone.utc


def prov(*, published_at=None, observed_at=None, raw_ref=None):
    return SimpleNamespace(
        source="nse",
        published_at=published_at,
        observed_at=observed_at,
        retrieved_at=datetime(2026, 10, 2, 12, tzinfo=UTC),
        raw_ref=raw_ref,
    )


def test_relationship_id_changes_with_validity_window():
    a = make_relationship("a", "p", "b", valid_from=date(2025, 1, 1))
    b = make_relationship("a", "p", "b", valid_from=date(2026, 1, 1))
    assert a.relationship_id != b.relationship_id


def test_graph_links_instrument_to_company():
    instrument = Instrument(
        instrument_id="REL", name="Reliance Industries", symbol="RELIANCE", exchange="NSE",
        provenance=Provenance(source="nse", source_type="exchange", retrieved_at=datetime(2026, 10, 2, 12, tzinfo=UTC), raw_ref="raw-1"),
    )
    graph = build_relationship_graph([instrument])
    assert {node.node_id for node in graph.nodes} >= {"company:REL", "instrument:REL"}
    assert any(
        edge.subject_id == "company:REL"
        and edge.predicate == "has_instrument"
        and edge.object_id == "instrument:REL"
        for edge in graph.relationships
    )


def test_graph_links_filing_and_document_asset():
    filing = Filing(
        filing_id="F1", instrument_id="REL", filing_type="results",
        assets=["A1"],
        provenance=Provenance(source="nse", source_type="exchange", retrieved_at=datetime(2026, 10, 2, 12, tzinfo=UTC), published_at=datetime(2026, 5, 15, tzinfo=UTC), raw_ref="raw-f1"),
    )
    asset = DocumentAsset(
        asset_id="A1", filing_id="F1", instrument_id="REL", title="Results.pdf", url="https://example.test/results.pdf",
        provenance=Provenance(source="nse", source_type="exchange", retrieved_at=datetime(2026, 10, 2, 12, tzinfo=UTC), published_at=datetime(2026, 5, 15, tzinfo=UTC), raw_ref="raw-a1"),
    )
    graph = build_relationship_graph([filing, asset])
    predicates = {(e.subject_id, e.predicate, e.object_id) for e in graph.relationships}
    assert ("company:REL", "has_filing", "filing:F1") in predicates
    assert ("filing:F1", "has_document_asset", "document_asset:A1") in predicates
    assert any("raw-f1" in e.evidence_ids for e in graph.relationships if e.object_id == "filing:F1")
    matching_asset_edges = [e for e in graph.relationships if e.object_id == "document_asset:A1"]
    assert any("raw-f1" in e.evidence_ids for e in matching_asset_edges)
    assert any("raw-a1" in e.evidence_ids for e in matching_asset_edges)


def test_graph_links_index_constituent_to_instrument():
    constituent = SimpleNamespace(
        record_type="IndexConstituent", index_id="N50", index_symbol="NIFTY 50",
        instrument_id="REL", symbol="RELIANCE", effective_date=date(2026, 9, 1),
        provenance=prov(raw_ref="raw-i"),
    )
    graph = build_relationship_graph([constituent])
    edge = next(e for e in graph.relationships if e.predicate == "contains_instrument")
    assert edge.subject_id == "index:N50"
    assert edge.object_id == "instrument:REL"
    assert edge.valid_from == date(2026, 9, 1)


def test_graph_supports_canonical_records():
    record = CanonicalRecord(
        record_id="C1", domain="market", record_type="PriceBar",
        payload={"instrument_id": "REL", "timestamp": "2026-10-01T00:00:00Z", "close": "100"},
        source_observation_ids=["OBS1"],
    )
    graph = build_relationship_graph([record])
    assert any(
        e.subject_id == "company:REL" and e.predicate == "has_price_observation"
        and e.object_id == "record:PriceBar:C1" and "OBS1" in e.evidence_ids
        for e in graph.relationships
    )


def test_graph_deduplicates_equivalent_relationships():
    record = CompanyEvent(
        event_id="E1", instrument_id="REL", event_type="board_meeting",
        provenance=Provenance(source="nse", source_type="exchange", retrieved_at=datetime(2026, 10, 2, 12, tzinfo=UTC), raw_ref="raw-e"),
    )
    graph = build_relationship_graph([record, record])
    matching = [e for e in graph.relationships if e.predicate == "has_event"]
    assert len(matching) == 1
    assert graph.metadata["relationship_count"] == len(graph.relationships)


def test_timeline_accepts_canonical_records_and_preserves_observation_evidence():
    records = [
        CanonicalRecord(
            record_id="C2", domain="market", record_type="PriceBar",
            payload={"instrument_id": "REL", "timestamp": "2026-10-02T00:00:00Z"},
            source_observation_ids=["OBS2"],
        )
    ]
    timeline = build_company_timeline("REL", records)
    assert len(timeline.entries) == 1
    assert timeline.entries[0].source_record_id == "C2"
    assert timeline.entries[0].evidence_ids == ["OBS2"]
    assert timeline.entries[0].event_time == datetime(2026, 10, 2, tzinfo=UTC)


def test_timeline_sorts_mixed_date_and_datetime_values_deterministically():
    records = [
        SimpleNamespace(
            event_id="E2", instrument_id="REL", event_type="later", event_date=date(2026, 10, 2),
            provenance=prov(raw_ref="raw-2"),
        ),
        SimpleNamespace(
            event_id="E1", instrument_id="REL", event_type="earlier",
            event_date=datetime(2026, 10, 1, 15, tzinfo=UTC), provenance=prov(raw_ref="raw-1"),
        ),
    ]
    timeline = build_company_timeline("REL", records)
    assert [entry.source_record_id for entry in timeline.entries] == ["E1", "E2"]
    assert timeline.metadata["entry_count"] == 2


def test_timeline_keeps_availability_metadata():
    published = datetime(2026, 10, 2, 10, tzinfo=UTC)
    record = SimpleNamespace(
        event_id="E3", instrument_id="REL", event_type="announcement",
        event_date=date(2026, 10, 2), provenance=prov(published_at=published, raw_ref="raw-3"),
    )
    entry = build_company_timeline("REL", [record]).entries[0]
    assert entry.available_at == published
    assert entry.metadata["availability_basis"] == "published"


def test_graph_merges_evidence_from_multiple_sources():
    a = CompanyEvent(
        event_id="E2", instrument_id="REL", event_type="acquisition",
        provenance=Provenance(source="nse", source_type="exchange", retrieved_at=datetime(2026, 10, 2, 12, tzinfo=UTC), raw_ref="raw-nse"),
    )
    b = CompanyEvent(
        event_id="E2", instrument_id="REL", event_type="acquisition",
        provenance=Provenance(source="upstox", source_type="broker", retrieved_at=datetime(2026, 10, 2, 12, tzinfo=UTC), raw_ref="raw-upstox"),
    )
    graph = build_relationship_graph([a, b])
    edge = next(e for e in graph.relationships if e.predicate == "has_event" and e.object_id == "record:CompanyEvent:E2")
    assert edge.source == "multiple"
    assert edge.metadata["sources"] == ["nse", "upstox"]
    assert edge.evidence_ids == ["raw-nse", "raw-upstox"]


def test_relationship_index_supports_outgoing_incoming_and_neighbors():
    graph = build_relationship_graph([
        CompanyEvent(
            event_id="E10", instrument_id="REL", event_type="results",
            provenance=Provenance(source="nse", source_type="exchange", retrieved_at=datetime(2026, 10, 2, 12, tzinfo=UTC)),
        )
    ])
    index = RelationshipIndex.from_graph(graph)
    outgoing = index.outgoing("company:REL", predicate="has_event")
    assert len(outgoing) == 1
    assert outgoing[0].object_id == "record:CompanyEvent:E10"
    assert index.incoming("record:CompanyEvent:E10")[0].subject_id == "company:REL"
    assert "record:CompanyEvent:E10" in index.neighbors("company:REL")


def test_relationship_index_is_sorted_deterministically():
    a = make_relationship("company:REL", "has_event", "record:b")
    b = make_relationship("company:REL", "has_event", "record:a")
    index = RelationshipIndex([a, b])
    assert [edge.object_id for edge in index.outgoing("company:REL")] == ["record:a", "record:b"]
