from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from data_foundation import (
    IdentityAlias,
    IdentityRegistry,
    InstrumentIdentity,
    QualityFinding,
    build_quality_report,
    choose_canonical_observation,
    reconcile_numeric,
    reconcile_numeric_with_decisions,
)
from data_foundation.models import SourceObservation

UTC = timezone.utc
NOW = datetime(2026, 10, 2, 12, tzinfo=UTC)


def obs(source: str, value, *, entity="i1", field="close", observed_at=NOW):
    return SourceObservation(
        observation_id=f"{source}-{value}", entity_key=entity, field=field, value=value,
        source=source, observed_at=observed_at, retrieved_at=NOW,
    )


def test_reconciliation_agree():
    result = reconcile_numeric([obs("nse", 100.0), obs("upstox", 100.005)])
    assert result[0].status == "agree"


def test_reconciliation_minor_difference():
    result = reconcile_numeric([obs("nse", 100.0), obs("upstox", 100.5)], tolerance=0.001, minor_tolerance=0.01)
    assert result[0].status == "minor_difference"


def test_reconciliation_conflicting():
    result = reconcile_numeric([obs("nse", 100.0), obs("upstox", 120.0)], tolerance=0.001, minor_tolerance=0.01)
    assert result[0].status == "conflicting"


def test_reconciliation_missing_expected_source():
    result = reconcile_numeric([obs("nse", 100.0), obs("upstox", 100.0)], expected_sources=["nse", "upstox", "yahoo"])
    assert result[0].status == "missing"
    assert result[0].missing_sources == ["yahoo"]


def test_reconciliation_unresolvable_non_numeric():
    result = reconcile_numeric([obs("nse", "N/A"), obs("upstox", "unknown")])
    assert result[0].status == "unresolvable"


def test_canonical_decision_uses_source_priority():
    observations = [obs("upstox", 100.05), obs("nse", 100.0)]
    finding = reconcile_numeric(observations)[0]
    decision = choose_canonical_observation(observations, finding, source_priority=["nse", "upstox"])
    assert decision.selected_observation_id == "nse-100.0"
    assert decision.selected_value == 100.0


def test_conflict_does_not_select_without_explicit_permission():
    observations = [obs("upstox", 101.0), obs("nse", 120.0)]
    finding = reconcile_numeric(observations, tolerance=0.001)[0]
    decision = choose_canonical_observation(observations, finding, source_priority=["nse", "upstox"])
    assert finding.status == "conflicting"
    assert decision.selected_observation_id is None


def test_reconcile_with_decisions_returns_pair():
    observations = [obs("nse", 100.0), obs("upstox", 100.0)]
    results = reconcile_numeric_with_decisions(observations, source_priority=["nse", "upstox"])
    assert results[0].finding.status == "agree"
    assert results[0].decision.selected_observation_id == "nse-100.0"


def test_missing_required_field_is_reported():
    record = SimpleNamespace(instrument_id="i1", provenance=SimpleNamespace(source="nse"))
    findings = build_quality_report(records=[record], required_fields=["instrument_id", "close"]).findings
    assert any(f.category == "missing_field" and f.field == "close" for f in findings)


def test_stale_source_is_reported():
    old = obs("nse", 100.0, observed_at=datetime(2026, 10, 2, 10, tzinfo=UTC))
    report = build_quality_report(observations=[old], as_of=NOW, max_age=3600)
    assert any(f.category == "stale_source" for f in report.findings)


def test_duplicate_records_are_reported():
    a = SimpleNamespace(instrument_id="i1", timestamp=NOW, provenance=SimpleNamespace(published_at=NOW))
    b = SimpleNamespace(instrument_id="i1", timestamp=NOW, provenance=SimpleNamespace(published_at=NOW))
    report = build_quality_report(records=[a, b])
    assert any(f.category == "duplicate" for f in report.findings)


def test_timestamp_anomaly_is_reported():
    record = SimpleNamespace(
        instrument_id="i1",
        timestamp=NOW,
        provenance=SimpleNamespace(
            published_at=datetime(2026, 10, 2, 13, tzinfo=UTC),
            retrieved_at=datetime(2026, 10, 2, 12, tzinfo=UTC),
            observed_at=None,
        ),
    )
    report = build_quality_report(records=[record])
    assert any(f.category == "timestamp_anomaly" and f.severity == "error" for f in report.findings)
    assert not report.passed


def test_schema_drift_is_reported():
    a = SimpleNamespace(source="nse", domain="market", metadata={"dataset": "quotes"}, payload={"close": 100, "volume": 10})
    b = SimpleNamespace(source="nse", domain="market", metadata={"dataset": "quotes"}, payload={"close": 100, "volume": 10, "vwap": 100.1})
    report = build_quality_report(payloads=[a, b])
    assert any(f.category == "schema_drift" for f in report.findings)


def test_identity_ambiguity_is_reported():
    identities = [
        InstrumentIdentity(
            instrument_id="i1",
            aliases=[IdentityAlias(alias_type="symbol", value="ABC", instrument_id="i1")],
        ),
        InstrumentIdentity(
            instrument_id="i2",
            aliases=[IdentityAlias(alias_type="symbol", value="ABC", instrument_id="i2")],
        ),
    ]
    registry = IdentityRegistry.from_identities(identities)
    report = build_quality_report(identity_registry=registry)
    assert any(f.category == "identity_ambiguity" for f in report.findings)


def test_invalid_numeric_is_reported():
    finding_report = build_quality_report(observations=[obs("nse", float("nan"))])
    assert any(f.category == "invalid_value" for f in finding_report.findings)


def test_reconciliation_conflict_flows_into_quality_report():
    observations = [obs("nse", 100.0), obs("upstox", 120.0)]
    finding = reconcile_numeric(observations, tolerance=0.001)[0]
    report = build_quality_report(reconciliation_findings=[finding])
    assert report.summary["conflict"] == 1
    assert not report.passed


def test_cross_source_records_are_not_default_duplicates():
    a = SimpleNamespace(instrument_id="i1", timestamp=NOW, provenance=SimpleNamespace(published_at=NOW, source="nse"))
    b = SimpleNamespace(instrument_id="i1", timestamp=NOW, provenance=SimpleNamespace(published_at=NOW, source="upstox"))
    report = build_quality_report(records=[a, b])
    assert not any(f.category == "duplicate" for f in report.findings)


def test_quality_report_summary_and_passed():
    report = build_quality_report()
    assert report.passed
    assert report.summary == {}
    assert report.severity_summary == {}
