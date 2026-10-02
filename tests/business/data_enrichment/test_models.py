from datetime import datetime, timezone

from data_enrichment import DerivedObservation, DerivedSummary, DerivationLineage


def test_derived_models_roundtrip():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    lineage = DerivationLineage(algorithm="test", algorithm_version="1", calculated_at=now, source_record_ids=["r1"])
    obs = DerivedObservation(derived_id="d", metric="x", value=1.2, lineage=lineage)
    summary = DerivedSummary(derived_id="s", summary_type="x", values={"a": 1}, lineage=lineage)
    assert obs.model_dump()["lineage"]["source_record_ids"] == ["r1"]
    assert summary.values["a"] == 1
