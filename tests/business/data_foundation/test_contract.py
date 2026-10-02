from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import data_foundation
from data_foundation import (
    CanonicalRecord,
    ContractViolation,
    FoundationStore,
    RawArtifact,
    SourceObservation,
    assert_evidence_chain,
    contract_manifest,
    validate_evidence_chain,
    validate_store_layout,
)

UTC = timezone.utc


def test_public_contract_version_and_manifest() -> None:
    assert data_foundation.__version__ == "1.0.0"
    manifest = contract_manifest()
    assert manifest.package_version == "1.0.0"
    assert manifest.contract_version == "1.0"
    assert "CanonicalRecord" in manifest.stable_models
    assert "FoundationStore" in manifest.stable_classes
    assert "what_was_known_at" in manifest.stable_functions
    assert "load_bundle" in manifest.stable_store_methods


def test_public_root_exports_are_contractually_stable() -> None:
    names = contract_manifest().stable_classes + contract_manifest().stable_models + contract_manifest().stable_functions
    missing = [name for name in names if not hasattr(data_foundation, name)]
    assert missing == []


def test_public_store_methods_are_contractually_stable() -> None:
    missing = [name for name in contract_manifest().stable_store_methods if not hasattr(FoundationStore, name)]
    assert missing == []


def test_evidence_chain_validator_accepts_complete_chain() -> None:
    artifact = RawArtifact(
        artifact_id="raw1", source="nse", domain="market", content_hash="0" * 64,
        size_bytes=0, storage_path="raw/nse/00/0.bin", retrieved_at=datetime(2026, 10, 2, tzinfo=UTC)
    )
    obs = SourceObservation(
        observation_id="obs1", entity_key="REL", field="close", value=100, source="nse",
        raw_ref="raw1", canonical_record_id="rec1"
    )
    record = CanonicalRecord(
        record_id="rec1", domain="market", record_type="PriceBar", payload={"instrument_id": "REL"},
        source_observation_ids=["obs1"]
    )
    assert validate_evidence_chain([record], [obs], [artifact]) == []
    assert_evidence_chain([record], [obs], [artifact]) is None


def test_evidence_chain_validator_reports_broken_references() -> None:
    record = CanonicalRecord(
        record_id="rec1", domain="market", record_type="PriceBar", payload={}, source_observation_ids=["missing"]
    )
    violations = validate_evidence_chain([record], [], [])
    assert any("missing observation" in value for value in violations)
    try:
        assert_evidence_chain([record], [], [])
    except ContractViolation:
        pass
    else:
        raise AssertionError("expected ContractViolation")


def test_store_load_roundtrip(tmp_path: Path) -> None:
    store = FoundationStore(str(tmp_path))
    record = CanonicalRecord(record_id="rec1", domain="market", record_type="PriceBar", payload={"instrument_id": "REL"})
    obs = SourceObservation(observation_id="obs1", entity_key="REL", field="close", value=100, source="nse", canonical_record_id="rec1")
    from data_foundation.storage import write_canonical_records, write_source_observations
    write_canonical_records([record], tmp_path, domain="market")
    write_source_observations([obs], tmp_path)
    assert store.load_canonical_records(domain="market")[0].record_id == "rec1"
    assert store.load_source_observations()[0].observation_id == "obs1"


def test_store_load_bundle_and_raw_artifact_roundtrip(tmp_path: Path) -> None:
    from data_collection.collection.results import CollectionResult, RawPayload
    now = datetime(2026, 10, 2, 10, tzinfo=UTC)
    raw = RawPayload(source="nse", domain="market", retrieved_at=now, payload={"close": 100}, request={"symbol": "REL"})
    result = CollectionResult(domain="market", records=[], raw_payloads=[raw])
    store = FoundationStore(str(tmp_path))
    store.persist_collection_result(result)
    canonical, observations, artifacts = store.load_bundle()
    assert canonical == []
    assert observations == []
    assert artifacts[0].artifact_id == raw.stable_id()
    assert store.load_raw_artifact(raw.stable_id()) == b'{"close":100}'


def test_validate_store_layout_accepts_valid_metadata(tmp_path: Path) -> None:
    store = FoundationStore(str(tmp_path))
    store.persist_records([], domain="market")
    assert validate_store_layout(tmp_path) == []

def test_pydantic_contract_allows_forward_fields_on_envelopes() -> None:
    record = CanonicalRecord(
        record_id="rec1", domain="market", record_type="PriceBar", payload={},
        future_extension={"x": 1},
    )
    assert record.future_extension == {"x": 1}

