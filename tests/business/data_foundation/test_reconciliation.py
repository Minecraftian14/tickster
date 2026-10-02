from data_foundation.models import SourceObservation
from data_foundation.reconciliation import observation_id, reconcile_numeric


def obs(source, value):
    return SourceObservation(observation_id=observation_id("I1|2026-05-01", "close", source, None, value), entity_key="I1|2026-05-01", field="close", value=value, source=source)


def test_reconciliation_agrees_within_tolerance():
    findings = reconcile_numeric([obs("nse", "100.00"), obs("yahoo", "100.005")])
    assert findings[0].status == "agree"


def test_reconciliation_flags_material_conflict():
    findings = reconcile_numeric([obs("nse", "100"), obs("yahoo", "101")])
    assert findings[0].status == "conflicting"
    assert findings[0].relative_spread > 0
