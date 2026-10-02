from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from pydantic import BaseModel

from data_foundation.models import CanonicalRecord, SourceObservation
from data_foundation.persistence import canonical_record_id, canonicalize_record
from data_foundation.storage import load_raw_artifact, read_jsonl, write_canonical_indexes, write_canonical_records, write_raw_artifact, write_raw_manifest, write_source_observations


class FakePrice(BaseModel):
    instrument_id: str
    close: float


def test_raw_artifact_is_content_addressed_and_idempotent(tmp_path: Path) -> None:
    now = datetime(2026, 10, 2, 10, tzinfo=timezone.utc)
    first = write_raw_artifact({"close": 100}, tmp_path, source="nse", domain="market", retrieved_at=now, media_type="application/json")
    second = write_raw_artifact({"close": 100}, tmp_path, source="nse", domain="market", retrieved_at=now, media_type="application/json")
    assert first.artifact_id == second.artifact_id
    assert first.storage_path == second.storage_path
    assert load_raw_artifact(tmp_path, first) == b'{"close":100}'


def test_raw_integrity_is_checked(tmp_path: Path) -> None:
    now = datetime(2026, 10, 2, 10, tzinfo=timezone.utc)
    artifact = write_raw_artifact(b"abc", tmp_path, source="nse", domain="market", retrieved_at=now)
    path = tmp_path / artifact.storage_path
    path.write_bytes(b"tampered")
    try:
        load_raw_artifact(tmp_path, artifact)
    except ValueError as exc:
        assert "integrity" in str(exc)
    else:
        raise AssertionError("expected integrity failure")


def test_canonical_record_id_is_stable() -> None:
    record = FakePrice(instrument_id="REL", close=100)
    assert canonical_record_id(record, domain="market") == canonical_record_id(record, domain="market")
    assert canonical_record_id(record, domain="market") != canonical_record_id(record, domain="fundamentals")


def test_canonical_record_wraps_typed_payload() -> None:
    record = FakePrice(instrument_id="REL", close=100)
    wrapped = canonicalize_record(record, domain="market", source_observation_ids=["obs1"])
    assert isinstance(wrapped, CanonicalRecord)
    assert wrapped.record_type == "FakePrice"
    assert wrapped.payload["close"] == 100.0
    assert wrapped.source_observation_ids == ["obs1"]


def test_persisted_canonical_and_observation_indexes(tmp_path: Path) -> None:
    record = canonicalize_record(FakePrice(instrument_id="REL", close=100), domain="market", source_observation_ids=["obs1"])
    obs = SourceObservation(observation_id="obs1", entity_key="REL", field="close", value=100, source="nse", raw_ref="raw1", canonical_record_id=record.record_id)
    write_canonical_records([record], tmp_path, domain="market")
    write_source_observations([obs], tmp_path)
    indexes = write_canonical_indexes([record], [obs], tmp_path)
    assert read_jsonl(tmp_path / "canonical/market/records.jsonl")[0]["record_id"] == record.record_id
    assert read_jsonl(indexes["canonical_to_observations"])[0] == {"record_id": record.record_id, "observation_id": "obs1"}
    assert read_jsonl(indexes["observation_to_raw"])[0] == {"observation_id": "obs1", "raw_artifact_id": "raw1"}


def test_raw_manifest_persists_metadata(tmp_path: Path) -> None:
    now = datetime(2026, 10, 2, 10, tzinfo=timezone.utc)
    artifact = write_raw_artifact("hello", tmp_path, source="yahoo", domain="news", retrieved_at=now, media_type="text/plain")
    path = write_raw_manifest([artifact], tmp_path)
    data = read_jsonl(path)
    assert data[0]["artifact_id"] == artifact.artifact_id
    assert data[0]["media_type"] == "text/plain"


def test_raw_path_is_content_addressed_across_retrieval_dates(tmp_path: Path) -> None:
    first = write_raw_artifact(
        b"same",
        tmp_path,
        source="nse",
        domain="market",
        retrieved_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    second = write_raw_artifact(
        b"same",
        tmp_path,
        source="nse",
        domain="market",
        retrieved_at=datetime(2026, 10, 2, tzinfo=timezone.utc),
    )
    assert first.content_hash == second.content_hash
    assert first.storage_path == second.storage_path


def test_source_specific_artifact_id_can_point_to_content_hash(tmp_path: Path) -> None:
    artifact = write_raw_artifact(
        {"x": 1},
        tmp_path,
        source="upstox",
        domain="market",
        retrieved_at=datetime(2026, 10, 2, tzinfo=timezone.utc),
        artifact_id="source-response-123",
        media_type="application/json",
    )
    assert artifact.artifact_id == "source-response-123"
    assert len(artifact.content_hash) == 64
    assert load_raw_artifact(tmp_path, artifact) == b'{"x":1}'


def test_observation_set_uses_the_same_domain_as_canonical_records() -> None:
    from data_foundation.persistence import observation_set_for_records

    record = FakePrice(instrument_id="REL", close=100)
    observations = observation_set_for_records([record], domain="market")
    assert observations
    assert observations[0].canonical_record_id == canonical_record_id(record, domain="market")


def test_raw_payload_bridge_preserves_collection_stable_id(tmp_path: Path) -> None:
    from data_collection.collection.results import RawPayload
    from data_foundation.persistence import persist_raw_payloads

    now = datetime(2026, 10, 2, 10, tzinfo=timezone.utc)
    payload = RawPayload(source="nse", domain="market", retrieved_at=now, payload={"close": 100}, request={"symbol": "REL"})
    artifacts = persist_raw_payloads([payload], str(tmp_path))
    assert artifacts[0].artifact_id == payload.stable_id()
    assert artifacts[0].content_hash != artifacts[0].artifact_id


def test_store_persists_collection_result_end_to_end(tmp_path: Path) -> None:
    from data_collection.collection.results import CollectionResult, RawPayload
    from data_collection.domains.models import PriceBar, Provenance
    from data_foundation.persistence import FoundationStore

    now = datetime(2026, 10, 2, 10, tzinfo=timezone.utc)
    raw = RawPayload(source="nse", domain="market", retrieved_at=now, payload={"close": 100}, request={"symbol": "REL"})
    record = PriceBar(
        instrument_id="REL", timestamp=now, timeframe="1d", close=100,
        provenance=Provenance(source="nse", source_type="exchange", retrieved_at=now, raw_ref=raw.stable_id()),
    )
    result = CollectionResult(domain="market", records=[record], raw_payloads=[raw])
    store = FoundationStore(str(tmp_path))
    persisted = store.persist_collection_result(result)
    assert persisted["raw_artifacts"][0].artifact_id == raw.stable_id()
    assert persisted["canonical_records"][0].source_observation_ids
    observation = persisted["source_observations"][0]
    assert observation.canonical_record_id == persisted["canonical_records"][0].record_id
    assert observation.raw_ref == raw.stable_id()
    assert read_jsonl(tmp_path / "indexes/raw_artifacts.jsonl")


def test_package_version() -> None:
    import data_foundation
    assert data_foundation.__version__ == "1.0.0"
