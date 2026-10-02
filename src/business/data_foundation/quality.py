from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from typing import Any, Callable, Iterable, Mapping, Sequence

from .models import (
    DataQuality,
    QualityFinding,
    QualityReport,
    ReconciliationFinding,
    SourceObservation,
)
from .temporal import temporal_envelope


def classify_missing(value: Any, *, source: str | None = None, field: str | None = None, raw_ref: str | None = None) -> DataQuality:
    if value is not None:
        return DataQuality(status="present", source=source, field=field, raw_ref=raw_ref)
    return DataQuality(status="unknown", source=source, field=field, raw_ref=raw_ref, message="No value was supplied; the reason is not yet known.")


def summarize_quality(findings: Iterable[DataQuality]) -> dict[str, int]:
    out: dict[str, int] = {}
    for finding in findings:
        out[finding.status] = out.get(finding.status, 0) + 1
    return out


def _finding_id(category: str, payload: Any) -> str:
    body = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return sha256(f"{category}|{body}".encode()).hexdigest()


def check_missing_fields(
    records: Iterable[Any],
    required_fields: Mapping[str, Sequence[str]] | Sequence[str],
    *,
    source: str | None = None,
) -> list[QualityFinding]:
    """Report fields that are absent/None on records.

    A mapping can specify fields by record class name; a flat sequence applies to
    every record.
    """
    findings: list[QualityFinding] = []
    flat = list(required_fields) if not isinstance(required_fields, Mapping) else None
    for record in records:
        fields = list(required_fields.get(record.__class__.__name__, ())) if isinstance(required_fields, Mapping) else flat or []
        record_id = _record_identity(record)
        for field in fields:
            if not hasattr(record, field) or getattr(record, field) is None:
                findings.append(QualityFinding(
                    finding_id=_finding_id("missing_field", (record_id, field)),
                    category="missing_field",
                    severity="warning",
                    message=f"Required field '{field}' is missing.",
                    entity_key=_entity_key(record),
                    field=field,
                    source=source or getattr(getattr(record, "provenance", None), "source", None),
                    record_ids=[record_id] if record_id else [],
                ))
    return findings


def check_stale_sources(
    observations: Iterable[SourceObservation],
    *,
    as_of: datetime,
    max_age: Mapping[str, float] | float,
) -> list[QualityFinding]:
    """Report observations older than a configured age in seconds."""
    findings: list[QualityFinding] = []
    for obs in observations:
        timestamp = obs.observed_at or obs.published_at or obs.retrieved_at
        if timestamp is None:
            continue
        point = _as_utc(timestamp)
        age = (as_of.astimezone(timezone.utc) - point).total_seconds()
        threshold = float(max_age.get(obs.source, float("inf")) if isinstance(max_age, Mapping) else max_age)
        if age > threshold:
            findings.append(QualityFinding(
                finding_id=_finding_id("stale_source", (obs.observation_id, threshold)),
                category="stale_source",
                severity="warning",
                message=f"Observation is {age:.0f}s old, exceeding the configured {threshold:.0f}s freshness threshold.",
                entity_key=obs.entity_key,
                field=obs.field,
                source=obs.source,
                observation_ids=[obs.observation_id],
                metadata={"age_seconds": age, "threshold_seconds": threshold},
            ))
    return findings


def check_reconciliation_findings(findings: Iterable[ReconciliationFinding]) -> list[QualityFinding]:
    """Translate reconciliation outcomes into quality findings where appropriate."""
    out: list[QualityFinding] = []
    severity_by_status = {"conflicting": "error", "missing": "warning", "unresolvable": "warning"}
    for finding in findings:
        severity = severity_by_status.get(finding.status)
        if severity is None:
            continue
        out.append(QualityFinding(
            finding_id=_finding_id("conflict", finding.finding_id),
            category="conflict",
            severity=severity,
            message=finding.message,
            entity_key=finding.entity_key,
            field=finding.field,
            observation_ids=list(finding.observations),
            metadata={"reconciliation_status": finding.status, "missing_sources": finding.missing_sources},
        ))
    return out


def check_duplicates(
    records: Iterable[Any],
    *,
    key_fn: Callable[[Any], Any] | None = None,
) -> list[QualityFinding]:
    """Find repeated records using a caller-defined or conservative stable key."""
    groups: dict[str, list[str]] = defaultdict(list)
    for record in records:
        key = key_fn(record) if key_fn else _default_duplicate_key(record)
        groups[json.dumps(key, sort_keys=True, default=str, separators=(",", ":"))].append(_record_identity(record))
    findings: list[QualityFinding] = []
    for key, record_ids in groups.items():
        if len(record_ids) > 1:
            findings.append(QualityFinding(
                finding_id=_finding_id("duplicate", (key, len(record_ids))),
                category="duplicate",
                severity="warning",
                message="Multiple records share the same duplicate-detection key.",
                record_ids=record_ids,
                metadata={"duplicate_key": json.loads(key), "occurrences": len(record_ids)},
            ))
    return findings


def check_timestamp_anomalies(records: Iterable[Any]) -> list[QualityFinding]:
    """Detect chronology contradictions in record/provenance timestamps."""
    findings: list[QualityFinding] = []
    for record in records:
        envelope = temporal_envelope(record)
        provenance = getattr(record, "provenance", None)
        published = getattr(provenance, "published_at", None) or getattr(record, "published_at", None)
        observed = getattr(provenance, "observed_at", None) or getattr(record, "observed_at", None)
        received = getattr(record, "received_at", None) or getattr(provenance, "received_at", None)
        retrieved = getattr(provenance, "retrieved_at", None) or getattr(record, "retrieved_at", None)

        checks = [
            ("published_after_retrieval", published, retrieved),
            ("observed_after_retrieval", observed, retrieved),
            ("received_after_retrieval", received, retrieved),
        ]
        for name, earlier, later in checks:
            if earlier is None or later is None:
                continue
            if _as_utc(earlier) > _as_utc(later):
                record_id = _record_identity(record)
                findings.append(QualityFinding(
                    finding_id=_finding_id("timestamp_anomaly", (record_id, name)),
                    category="timestamp_anomaly",
                    severity="error",
                    message=f"Timestamp ordering anomaly: {name}.",
                    entity_key=_entity_key(record),
                    record_ids=[record_id] if record_id else [],
                    metadata={"check": name, "earlier": earlier, "later": later},
                ))
        if envelope.period_start is not None and envelope.period_end is not None:
            if _as_utc(envelope.period_start) > _as_utc(envelope.period_end):
                record_id = _record_identity(record)
                findings.append(QualityFinding(
                    finding_id=_finding_id("timestamp_anomaly", (record_id, "period_order")),
                    category="timestamp_anomaly",
                    severity="error",
                    message="Period start occurs after period end.",
                    entity_key=_entity_key(record),
                    record_ids=[record_id] if record_id else [],
                ))
    return findings


def schema_signature(payload: Any) -> tuple[str, ...]:
    """Produce a compact structural signature for JSON-like payloads."""
    paths: set[str] = set()

    def walk(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            if not value:
                paths.add(f"{path}:object")
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                walk(child, child_path)
        elif isinstance(value, list):
            paths.add(f"{path}:array")
            if value:
                walk(value[0], f"{path}[]")
        else:
            typename = type(value).__name__
            paths.add(f"{path}:{typename}")

    walk(payload, "")
    return tuple(sorted(paths))


def check_schema_drift(
    payloads: Iterable[Any],
    *,
    group_key_fn: Callable[[Any], str] | None = None,
) -> list[QualityFinding]:
    """Compare JSON-like payload schemas within a logical source/dataset group."""
    groups: dict[str, list[Any]] = defaultdict(list)
    for item in payloads:
        key = group_key_fn(item) if group_key_fn else _payload_group_key(item)
        groups[key].append(item)

    findings: list[QualityFinding] = []
    for group_key, items in groups.items():
        signatures = [schema_signature(_payload_content(item)) for item in items]
        baseline = signatures[0]
        for index, signature in enumerate(signatures[1:], start=1):
            if signature != baseline:
                added = sorted(set(signature) - set(baseline))
                removed = sorted(set(baseline) - set(signature))
                source = getattr(items[index], "source", None)
                findings.append(QualityFinding(
                    finding_id=_finding_id("schema_drift", (group_key, index, added, removed)),
                    category="schema_drift",
                    severity="warning",
                    message="Payload schema differs from the first observed schema in this source/dataset group.",
                    source=source,
                    metadata={"group": group_key, "added": added, "removed": removed},
                ))
    return findings


def check_identity_ambiguities(identity_registry: Any) -> list[QualityFinding]:
    """Report aliases that currently resolve to more than one instrument."""
    findings: list[QualityFinding] = []
    candidates = getattr(identity_registry, "_candidates", {})
    for (alias_type, normalized), instrument_ids in candidates.items():
        ids = sorted(instrument_ids)
        if len(ids) > 1:
            findings.append(QualityFinding(
                finding_id=_finding_id("identity_ambiguity", (alias_type, normalized, ids)),
                category="identity_ambiguity",
                severity="error",
                message=f"Alias '{normalized}' is ambiguous across {len(ids)} instruments.",
                entity_key=normalized,
                metadata={"alias_type": alias_type, "instrument_ids": ids},
            ))
    return findings


def check_invalid_numeric_values(observations: Iterable[SourceObservation]) -> list[QualityFinding]:
    """Detect NaN/Inf/non-finite numeric-looking observation values."""
    findings: list[QualityFinding] = []
    for obs in observations:
        value = obs.value
        if isinstance(value, float) and (value != value or value in {float("inf"), float("-inf")}):
            findings.append(QualityFinding(
                finding_id=_finding_id("invalid_value", (obs.observation_id, value)),
                category="invalid_value",
                severity="error",
                message="Observation contains a non-finite numeric value.",
                entity_key=obs.entity_key,
                field=obs.field,
                source=obs.source,
                observation_ids=[obs.observation_id],
            ))
    return findings


def build_quality_report(
    *,
    records: Iterable[Any] = (),
    observations: Iterable[SourceObservation] = (),
    payloads: Iterable[Any] = (),
    identity_registry: Any | None = None,
    required_fields: Mapping[str, Sequence[str]] | Sequence[str] | None = None,
    as_of: datetime | None = None,
    max_age: Mapping[str, float] | float | None = None,
    duplicate_key_fn: Callable[[Any], Any] | None = None,
    reconciliation_findings: Iterable[ReconciliationFinding] = (),
) -> QualityReport:
    """Run the quality checks appropriate to the supplied batch."""
    records = list(records)
    observations = list(observations)
    payloads = list(payloads)
    findings: list[QualityFinding] = []
    if required_fields is not None:
        findings.extend(check_missing_fields(records, required_fields))
    findings.extend(check_duplicates(records, key_fn=duplicate_key_fn))
    findings.extend(check_timestamp_anomalies(records))
    findings.extend(check_invalid_numeric_values(observations))
    if as_of is not None and max_age is not None:
        findings.extend(check_stale_sources(observations, as_of=as_of, max_age=max_age))
    if payloads:
        findings.extend(check_schema_drift(payloads))
    if identity_registry is not None:
        findings.extend(check_identity_ambiguities(identity_registry))
    findings.extend(check_reconciliation_findings(reconciliation_findings))
    return QualityReport(generated_at=datetime.now(timezone.utc), findings=findings)


def _as_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    raise TypeError(f"Unsupported temporal value: {value!r}")


def _record_identity(record: Any) -> str:
    for key in ("instrument_id", "event_id", "filing_id", "document_id", "news_id", "series_id", "index_id", "observation_id", "relationship_id"):
        value = getattr(record, key, None)
        if value:
            return f"{key}:{value}"
    return record.__class__.__name__ + ":" + sha256(json.dumps(record.model_dump(mode="json") if hasattr(record, "model_dump") else record, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def _entity_key(record: Any) -> str | None:
    for key in ("instrument_id", "event_id", "filing_id", "document_id", "news_id", "series_id", "index_id"):
        value = getattr(record, key, None)
        if value:
            return str(value)
    return None


def _default_duplicate_key(record: Any) -> Any:
    return {
        "type": record.__class__.__name__,
        "identity": _entity_key(record),
        "event_time": getattr(record, "timestamp", None) or getattr(record, "observation_date", None) or getattr(record, "announcement_date", None),
        "published_at": getattr(getattr(record, "provenance", None), "published_at", None) or getattr(record, "published_at", None),
        "source": getattr(getattr(record, "provenance", None), "source", None),
    }


def _payload_content(item: Any) -> Any:
    return getattr(item, "payload", item)


def _payload_group_key(item: Any) -> str:
    source = getattr(item, "source", None) or getattr(getattr(item, "provenance", None), "source", None) or "unknown"
    domain = getattr(item, "domain", None) or "unknown"
    metadata = getattr(item, "metadata", {}) or {}
    dataset = metadata.get("dataset") or metadata.get("endpoint") or "default"
    return f"{source}|{domain}|{dataset}"
