from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from math import isfinite
from typing import Any, Iterable, Mapping, Sequence

from .models import ReconciliationDecision, ReconciliationFinding, ReconciliationResult, SourceObservation


def _stable_repr(value: Any) -> str:
    return repr(value)


def observation_id(entity_key: str, field: str, source: str, observed_at: Any, value: Any) -> str:
    raw = _stable_repr((entity_key, field, source, observed_at, value)).encode()
    return sha256(raw).hexdigest()


def to_numeric(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        n = float(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return n if isfinite(n) else None


def _group_observations(observations: Iterable[SourceObservation]) -> dict[tuple[str, str], list[SourceObservation]]:
    groups: dict[tuple[str, str], list[SourceObservation]] = defaultdict(list)
    for item in observations:
        groups[(item.entity_key, item.field)].append(item)
    return groups


def _finding_id(entity_key: str, field: str, observations: Sequence[SourceObservation], status: str) -> str:
    key = "|".join(
        [entity_key, field, status, *sorted(item.observation_id for item in observations)]
    )
    return sha256(key.encode()).hexdigest()


def _missing_sources(group: Sequence[SourceObservation], expected_sources: Sequence[str] | None) -> list[str]:
    if not expected_sources:
        return []
    present = {item.source for item in group}
    return sorted(set(expected_sources) - present)


def reconcile_numeric(
    observations: Iterable[SourceObservation],
    *,
    tolerance: Decimal | float = Decimal("0.0001"),
    minor_tolerance: Decimal | float | None = None,
    absolute_tolerance: Decimal | float = Decimal("0"),
    expected_sources: Sequence[str] | None = None,
) -> list[ReconciliationFinding]:
    """Compare numeric observations and classify their agreement.

    ``tolerance`` is the relative-spread threshold for ``agree``. Values above that
    threshold but within ``minor_tolerance`` become ``minor_difference``. Anything
    beyond ``minor_tolerance`` is ``conflicting``. ``expected_sources`` allows a
    missing source to be represented explicitly instead of silently disappearing.
    """
    agree_threshold = float(tolerance)
    minor_threshold = float(minor_tolerance if minor_tolerance is not None else Decimal(str(agree_threshold * 10)))
    abs_threshold = float(absolute_tolerance)
    findings: list[ReconciliationFinding] = []

    for (entity_key, field), group in _group_observations(observations).items():
        missing_sources = _missing_sources(group, expected_sources)
        numeric = [(item, to_numeric(item.value)) for item in group]
        numeric_values = [(item, value) for item, value in numeric if value is not None]
        non_numeric = [item for item, value in numeric if value is None and item.value is not None]

        if not numeric_values and not group:
            status = "missing"
            message = "No source observations are available."
            spread = relative = None
        elif not numeric_values:
            status = "unresolvable"
            message = "Source observations exist, but none contain numeric values."
            spread = relative = None
        elif len(numeric_values) < 2:
            if missing_sources:
                status = "missing"
                message = "At least one expected source observation is missing."
            else:
                status = "unresolvable"
                message = "Only one numeric observation is available, so reconciliation cannot establish agreement."
            spread = relative = None
        else:
            values = [value for _, value in numeric_values]
            spread = max(values) - min(values)
            baseline = max(abs(value) for value in values)
            relative = spread / baseline if baseline else 0.0
            absolute_agreement = spread <= abs_threshold
            if absolute_agreement or relative <= agree_threshold:
                status = "agree"
                message = "Source values agree within configured tolerance."
            elif relative <= minor_threshold:
                status = "minor_difference"
                message = "Source values differ slightly but remain within the minor-difference threshold."
            else:
                status = "conflicting"
                message = "Source values materially disagree."
            if non_numeric:
                message += " Some source observations could not be interpreted numerically."

        if missing_sources and status == "agree":
            status = "missing"
            message = f"Numeric values agree among available sources, but expected sources are missing: {', '.join(missing_sources)}."

        findings.append(
            ReconciliationFinding(
                finding_id=_finding_id(entity_key, field, group, status),
                entity_key=entity_key,
                field=field,
                status=status,
                observations=[item.observation_id for item in group],
                message=message,
                spread=spread,
                relative_spread=relative,
                missing_sources=missing_sources,
                metadata={"expected_sources": list(expected_sources or [])},
            )
        )
    return findings


def choose_canonical_observation(
    observations: Iterable[SourceObservation],
    finding: ReconciliationFinding,
    *,
    source_priority: Sequence[str] = (),
    allow_conflict: bool = False,
) -> ReconciliationDecision:
    """Choose a source deterministically when the reconciliation status permits it.

    Conflicting observations are intentionally left unresolved unless the caller
    explicitly permits a conflict decision. This prevents a silent source preference
    from masquerading as factual reconciliation.
    """
    group = [item for item in observations if item.observation_id in set(finding.observations)]
    by_priority = {source: index for index, source in enumerate(source_priority)}
    ranked = sorted(group, key=lambda item: (by_priority.get(item.source, len(by_priority)), item.source, item.observation_id))

    selected = None
    reason = "No canonical observation selected."
    if finding.status in {"agree", "minor_difference"}:
        selected = ranked[0] if ranked else None
        if selected:
            reason = f"Selected highest-priority available source: {selected.source}."
    elif finding.status == "conflicting" and allow_conflict:
        selected = ranked[0] if ranked else None
        if selected:
            reason = f"Conflict was explicitly allowed; selected highest-priority source: {selected.source}."
    elif finding.status == "missing":
        reason = "Canonical selection withheld because required source coverage is incomplete."
    elif finding.status == "unresolvable":
        reason = "Canonical selection withheld because observations cannot be reliably reconciled."
    elif finding.status == "conflicting":
        reason = "Canonical selection withheld because sources materially conflict."

    decision_id = sha256(f"{finding.finding_id}|{selected.observation_id if selected else ''}|{finding.status}".encode()).hexdigest()
    return ReconciliationDecision(
        decision_id=decision_id,
        finding_id=finding.finding_id,
        selected_observation_id=selected.observation_id if selected else None,
        selected_value=selected.value if selected else None,
        status=finding.status,
        reason=reason,
        policy="source_priority",
        metadata={"source_priority": list(source_priority), "allow_conflict": allow_conflict},
    )


def reconcile_numeric_with_decisions(
    observations: Iterable[SourceObservation],
    *,
    source_priority: Sequence[str] = (),
    allow_conflict: bool = False,
    tolerance: Decimal | float = Decimal("0.0001"),
    minor_tolerance: Decimal | float | None = None,
    absolute_tolerance: Decimal | float = Decimal("0"),
    expected_sources: Sequence[str] | None = None,
) -> list[ReconciliationResult]:
    observations = list(observations)
    findings = reconcile_numeric(
        observations,
        tolerance=tolerance,
        minor_tolerance=minor_tolerance,
        absolute_tolerance=absolute_tolerance,
        expected_sources=expected_sources,
    )
    return [
        ReconciliationResult(
            finding=finding,
            decision=choose_canonical_observation(
                observations,
                finding,
                source_priority=source_priority,
                allow_conflict=allow_conflict,
            ),
        )
        for finding in findings
    ]


def observations_from_record(record: Any, *, fields: Iterable[str] | None = None) -> list[SourceObservation]:
    """Extract scalar canonical fields into source observations without mutating the record."""
    provenance = getattr(record, "provenance", None)
    source = getattr(provenance, "source", record.__class__.__name__)
    source_type = getattr(provenance, "source_type", None)
    entity_key = str(
        getattr(record, "instrument_id", None)
        or getattr(record, "news_id", None)
        or getattr(record, "event_id", None)
        or getattr(record, "filing_id", None)
        or getattr(record, "series_id", None)
        or getattr(record, "index_id", None)
        or record.__class__.__name__
    )
    candidate_fields = list(fields) if fields is not None else [
        "open", "high", "low", "close", "volume", "turnover", "delivery_quantity",
        "delivery_percent", "last_price", "previous_close", "net_change", "day_open",
        "day_high", "day_low", "average_price", "total_buy_quantity", "total_sell_quantity",
        "open_interest", "previous_oi", "pe", "pb", "dividend_yield",
    ]
    timestamp = getattr(record, "timestamp", None) or getattr(record, "observation_date", None)
    observations: list[SourceObservation] = []
    for field in candidate_fields:
        if not hasattr(record, field):
            continue
        value = getattr(record, field)
        if value is None:
            continue
        oid = observation_id(entity_key, field, source, timestamp, value)
        observations.append(SourceObservation(
            observation_id=oid,
            entity_key=entity_key,
            field=field,
            value=value,
            source=source,
            source_type=source_type,
            observed_at=getattr(provenance, "observed_at", None) or timestamp,
            published_at=getattr(provenance, "published_at", None),
            retrieved_at=getattr(provenance, "retrieved_at", None),
            raw_ref=getattr(provenance, "raw_ref", None),
        ))
    return observations
