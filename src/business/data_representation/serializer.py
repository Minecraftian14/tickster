from __future__ import annotations

import csv
import io
import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from .policies import GENERIC_DROP_FIELDS, GENERIC_DROP_SUFFIXES, RECORD_POLICIES

OutputFormat = Literal["markdown", "csv", "tsv"]


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool, Decimal, date, datetime))


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _coerce_object(value: Any) -> Any:
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return value.model_dump(mode="python", exclude_none=False)
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return dict(vars(value))
    return value


def _unwrap_record(value: Any) -> tuple[str, dict[str, Any]]:
    original_type = value.__class__.__name__
    if hasattr(value, "model_dump") and callable(value.model_dump):
        dumped = value.model_dump(mode="python", exclude_none=False)
        if isinstance(dumped, Mapping):
            if isinstance(dumped.get("payload"), Mapping) and dumped.get("record_type"):
                return str(dumped["record_type"]), dict(dumped["payload"])
            return original_type, dict(dumped)
    if isinstance(value, Mapping):
        if isinstance(value.get("payload"), Mapping) and value.get("record_type"):
            return str(value["record_type"]), dict(value["payload"])
        record_type = str(value.get("record_type") or value.get("type") or "Record")
        payload = {str(key): item for key, item in value.items() if key not in {"record_type", "type"}}
        return record_type, payload
    value = _coerce_object(value)
    if isinstance(value, Mapping):
        return original_type, dict(value)
    return original_type, {"value": value}


def _policy(record_type: str) -> dict[str, object]:
    return RECORD_POLICIES.get(record_type, {})


def _get_drop_fields(record_type: str, *, scoped_instrument: bool) -> set[str]:
    policy = _policy(record_type)
    drop = set(GENERIC_DROP_FIELDS)
    drop.update(policy.get("drop", ()))
    if scoped_instrument:
        drop.add("instrument_id")
    return drop


def _should_drop_key(key: str, record_type: str, *, scoped_instrument: bool) -> bool:
    if key in _get_drop_fields(record_type, scoped_instrument=scoped_instrument):
        return True
    # Any remaining identifier-shaped field is machine bookkeeping unless a
    # type-specific policy explicitly keeps it (e.g. ISIN is not *_id).
    if key == "id" or any(key.endswith(suffix) for suffix in GENERIC_DROP_SUFFIXES):
        return True
    if key.endswith("_ids"):
        return True
    return False


def _format_datetime(value: Any, *, field: str, row: Mapping[str, Any]) -> str:
    if isinstance(value, str):
        text = value.strip()
        try:
            value = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed_date = date.fromisoformat(text)
            except ValueError:
                return text
            return parsed_date.isoformat()
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if not isinstance(value, datetime):
        return str(value)
    dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if field in {"timestamp", "observation_date", "event_date", "announcement_date", "ex_date", "record_date", "trade_date", "period_end", "period_start", "effective_date", "classification_as_of", "published_at", "received_at", "revised_at", "intimation_date", "broadcast_at"}:
        timeframe = str(row.get("timeframe") or "").lower()
        if field == "timestamp" and timeframe in {"1d", "1day", "day", "daily"}:
            return dt.date().isoformat()
        if dt.hour == dt.minute == dt.second == dt.microsecond == 0:
            return dt.date().isoformat()
        return dt.isoformat(timespec="minutes")
    return dt.isoformat(timespec="minutes")


def _format_scalar(value: Any, *, field: str, row: Mapping[str, Any]) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return _format_datetime(value, field=field, row=row)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and field in {
        "timestamp", "observation_date", "event_date", "announcement_date", "ex_date", "record_date",
        "trade_date", "period_end", "period_start", "effective_date", "classification_as_of",
        "published_at", "received_at", "revised_at", "intimation_date", "broadcast_at", "available_at", "as_of",
    }:
        return _format_datetime(value, field=field, row=row)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return str(value)
        return str(value)
    return str(value)


def _compact_nested(value: Any, *, row: Mapping[str, Any], field: str) -> str:
    if isinstance(value, Mapping):
        parts = []
        for key, item in value.items():
            if _is_empty(item):
                continue
            rendered = _compact_nested(item, row=row, field=str(key))
            if rendered:
                parts.append(f"{key}={rendered}")
        return "; ".join(parts)
    if isinstance(value, (list, tuple)):
        if not value:
            return ""
        if all(_is_scalar(item) for item in value):
            return ", ".join(_format_scalar(item, field=field, row=row) for item in value)
        return "; ".join(_compact_nested(item, row=row, field=field) for item in value)
    return _format_scalar(value, field=field, row=row)


def _prepare_records(
    records: Iterable[Any],
    *,
    instrument_id: str | None = None,
    include_source: bool = True,
) -> tuple[str | None, list[dict[str, Any]], dict[str, Any]]:
    materialized = list(records)
    if not materialized:
        return None, [], {}

    unwrapped = [_unwrap_record(item) for item in materialized]
    record_types = {record_type for record_type, _ in unwrapped}
    record_type = next(iter(record_types)) if len(record_types) == 1 else None
    if record_type is None:
        raise ValueError("render_records requires records of one type; use render() for mixed collections")

    policy = _policy(record_type)
    expand_fields = set(policy.get("expand", ()))
    text_limits = dict(policy.get("text_limits", {}))
    scoped = instrument_id is not None

    rows: list[dict[str, Any]] = []
    for _, payload in unwrapped:
        row: dict[str, Any] = {}
        for key, value in payload.items():
            if _should_drop_key(key, record_type, scoped_instrument=scoped):
                continue
            if _is_empty(value):
                continue
            if key in expand_fields and isinstance(value, Mapping) and all(_is_scalar(item) or _is_empty(item) for item in value.values()):
                for nested_key, nested_value in value.items():
                    if _is_empty(nested_value):
                        continue
                    row[f"{key}.{nested_key}"] = nested_value
                continue
            if key in text_limits and isinstance(value, str) and len(value) > int(text_limits[key]):
                row[key] = value[: int(text_limits[key])].rstrip() + "…"
            else:
                row[key] = value

        provenance = payload.get("provenance")
        if include_source and isinstance(provenance, Mapping):
            source = provenance.get("source")
            if source and "source" not in row:
                row["source"] = source
            source_type = provenance.get("source_type")
            if source_type and "source_type" not in row:
                row["source_type"] = source_type

        rows.append(row)

    # Drop fields that are empty in every row.
    all_keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in all_keys:
                all_keys.append(key)
    nonempty_keys = [key for key in all_keys if any(not _is_empty(row.get(key)) for row in rows)]
    rows = [{key: row.get(key) for key in nonempty_keys if key in row} for row in rows]

    common: dict[str, Any] = {}
    if len(rows) > 1:
        for key in nonempty_keys:
            values = [row.get(key) for row in rows]
            first = values[0]
            if _is_scalar(first) and all(_same_value(first, value) for value in values[1:]):
                common[key] = first

    for row in rows:
        for key in common:
            row.pop(key, None)

    header_order = list(policy.get("header", ()))
    for key in common:
        if key not in header_order:
            header_order.append(key)
    common = {key: common[key] for key in header_order if key in common}

    order = list(policy.get("order", ()))
    headers: list[str] = [key for key in order if any(key in row for row in rows)]
    for row in rows:
        for key in row:
            if key not in headers:
                headers.append(key)
    return record_type, [{key: row.get(key) for key in headers} for row in rows], common


def _same_value(left: Any, right: Any) -> bool:
    if isinstance(left, datetime) and isinstance(right, datetime):
        return left == right
    return left == right


def _render_headers(common: Mapping[str, Any], *, context_instrument: str | None, record_type: str) -> list[str]:
    lines = []
    if context_instrument:
        lines.append(f"Instrument: {context_instrument}")
    if record_type:
        lines.append(f"Type: {record_type}")
    if common:
        parts = [f"{key}={_format_scalar(value, field=key, row=common)}" for key, value in common.items() if not _is_empty(value)]
        if parts:
            lines.append("Context: " + "; ".join(parts))
    return lines


def _render_markdown_table(headers: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> str:
    if not headers:
        return "_empty_\n"
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        values = []
        for key in headers:
            text = _format_cell(row.get(key), field=key, row=row)
            text = text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")
            values.append(text)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def _format_cell(value: Any, *, field: str, row: Mapping[str, Any]) -> str:
    if _is_empty(value):
        return ""
    if _is_scalar(value):
        return _format_scalar(value, field=field, row=row)
    return _compact_nested(value, row=row, field=field)


def _render_csv(headers: Sequence[str], rows: Sequence[Mapping[str, Any]], *, delimiter: str) -> str:
    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter, lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_format_cell(row.get(key), field=key, row=row) for key in headers])
    return output.getvalue()


def render_records(
    records: Iterable[Any],
    *,
    format: OutputFormat = "markdown",
    instrument_id: str | None = None,
    include_source: bool = True,
    title: str | None = None,
) -> str:
    """Render one homogeneous record collection compactly.

    Common scalar fields are promoted into a one-line context header, machine
    identifiers and implementation metadata are suppressed, empty columns are
    omitted, and domain-specific nested fields can be flattened according to the
    record policy. Markdown is the default because it remains readable to humans;
    CSV/TSV are available when maximum compactness is preferred.
    """
    record_type, rows, common = _prepare_records(records, instrument_id=instrument_id, include_source=include_source)
    if record_type is None:
        return ""

    headers: list[str] = []
    for row in rows:
        for key in row:
            if key not in headers:
                headers.append(key)

    prefix: list[str] = []
    if title:
        prefix.append(title)
    prefix.extend(_render_headers(common, context_instrument=instrument_id, record_type=record_type))
    prefix = [line for line in prefix if line]

    if format == "markdown":
        body = _render_markdown_table(headers, rows)
        return ("\n".join(prefix) + "\n" if prefix else "") + body
    delimiter = "," if format == "csv" else "\t"
    header_lines = [f"# {line}" for line in prefix]
    body = _render_csv(headers, rows, delimiter=delimiter)
    return ("\n".join(header_lines) + "\n" if header_lines else "") + body


def _looks_like_record_collection(value: Any) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)) or not value:
        return False
    types = []
    for item in value:
        record_type, payload = _unwrap_record(item)
        if not isinstance(payload, Mapping):
            return False
        types.append(record_type)
    return len(set(types)) == 1


def _render_derived_series(series: Any, *, format: OutputFormat) -> str:
    metric = getattr(series, "metric", None) or "series"
    unit = getattr(series, "unit", None)
    instrument_id = getattr(series, "instrument_id", None)
    rows = []
    for point in getattr(series, "points", []):
        rows.append({"timestamp": point.timestamp, "value": point.value})
    header = f"{metric}" + (f" ({unit})" if unit else "")
    return render_records(rows_as_named_type(rows, "DerivedSeriesPoint"), format=format, instrument_id=instrument_id, include_source=False, title=header)


def rows_as_named_type(rows: list[dict[str, Any]], record_type: str) -> list[Any]:
    # Small adapter object-free representation used internally by the renderer.
    return [{"record_type": record_type, **row} for row in rows]


def render_context_pack(
    pack: Any,
    *,
    format: OutputFormat = "markdown",
    include_source: bool = True,
) -> str:
    """Render a ContextPack as compact LLM-ready text.

    The source/derived separation in ContextPack is intentionally preserved in
    the output, but machine-only pack metadata, IDs and lineage are not rendered.
    """
    instrument_id = getattr(pack, "instrument_id", None)
    as_of = getattr(pack, "as_of", None)
    sections: list[str] = []

    header: list[str] = []
    if instrument_id:
        header.append(f"Instrument: {instrument_id}")
    if as_of:
        header.append(f"As of: {_format_datetime(as_of, field='as_of', row={})}")
    profile = getattr(pack, "profile", None)
    if profile:
        header.append(f"Context: {profile}")
    if header:
        sections.append("\n".join(header))

    source_records = list(getattr(pack, "source_records", []) or [])
    if source_records:
        grouped: dict[str, list[Any]] = defaultdict(list)
        for record in source_records:
            record_type, _ = _unwrap_record(record)
            grouped[record_type].append(record)
        for record_type, records in grouped.items():
            rendered = render_records(
                records,
                format=format,
                instrument_id=None,
                include_source=include_source,
                title=record_type,
            ).strip()
            if rendered:
                sections.append(rendered)

    observations = list(getattr(pack, "observations", []) or [])
    if observations:
        rows = []
        for item in observations:
            rows.append({
                "metric": getattr(item, "metric", None),
                "value": getattr(item, "value", None),
                "unit": getattr(item, "unit", None),
                "observed_at": getattr(item, "observed_at", None),
                "available_at": getattr(item, "available_at", None),
            })
        rendered = render_records(rows_as_named_type(rows, "DerivedObservation"), format=format, instrument_id=instrument_id, include_source=False, title="Derived observations")
        sections.append(rendered.strip())

    series = list(getattr(pack, "series", []) or [])
    for item in series:
        rows = [{"timestamp": point.timestamp, "value": point.value, "available_at": point.available_at} for point in item.points]
        title = str(getattr(item, "metric", "Derived series"))
        unit = getattr(item, "unit", None)
        if unit:
            title += f" ({unit})"
        if format == "markdown":
            record_type, prepared_rows, common = _prepare_records(rows_as_named_type(rows, "DerivedSeriesPoint"), instrument_id=instrument_id, include_source=False)
            headers = list(prepared_rows[0].keys()) if prepared_rows else []
            rendered = f"Type: {title}\n"
            if common:
                rendered += "Context: " + "; ".join(
                    f"{key}={_format_scalar(value, field=key, row=common)}" for key, value in common.items() if not _is_empty(value)
                ) + "\n"
            rendered += _render_markdown_table(headers, prepared_rows) if prepared_rows else "_empty_\n"
        else:
            _, prepared_rows, common = _prepare_records(rows_as_named_type(rows, "DerivedSeriesPoint"), instrument_id=instrument_id, include_source=False)
            headers = list(prepared_rows[0].keys()) if prepared_rows else []
            delimiter = "," if format == "csv" else "\t"
            context_line = ""
            if common:
                context_line = "# Context: " + "; ".join(
                    f"{key}={_format_scalar(value, field=key, row=common)}" for key, value in common.items() if not _is_empty(value)
                ) + "\n"
            rendered = f"# {title}\n" + context_line + _render_csv(headers, prepared_rows, delimiter=delimiter)
        sections.append(rendered.strip())

    summaries = list(getattr(pack, "summaries", []) or [])
    for item in summaries:
        values = getattr(item, "values", {}) or {}
        rows = [{"metric": key, "value": value} for key, value in values.items() if not _is_empty(value)]
        title = str(getattr(item, "summary_type", "Derived summary"))
        sections.append(render_records(rows_as_named_type(rows, "DerivedSummaryValue"), format=format, instrument_id=None, include_source=False, title=title).strip())

    text = "\n\n".join(section for section in sections if section).strip()
    return text + ("\n" if text else "")


def render(value: Any, *, format: OutputFormat = "markdown", instrument_id: str | None = None, include_source: bool = True, title: str | None = None) -> str:
    """Automatically choose compact rendering for a value.

    Homogeneous lists of records become tables; ContextPack receives its dedicated
    renderer; other mappings/sequences are rendered with the same compact field
    rules where possible.
    """
    if hasattr(value, "source_records") and hasattr(value, "series") and hasattr(value, "summaries"):
        return render_context_pack(value, format=format, include_source=include_source)
    if _looks_like_record_collection(value):
        return render_records(value, format=format, instrument_id=instrument_id, include_source=include_source, title=title)
    if isinstance(value, Mapping):
        # A mapping of homogeneous record lists is common in ad-hoc contexts.
        sections = []
        for key, item in value.items():
            if _looks_like_record_collection(item):
                sections.append(render_records(item, format=format, instrument_id=instrument_id, include_source=include_source, title=str(key)).strip())
            else:
                rendered = _compact_nested(item, row={}, field=str(key))
                if rendered:
                    sections.append(f"{key}: {rendered}")
        text = "\n\n".join(sections)
        return text + ("\n" if text else "")
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return "\n".join(_compact_nested(item, row={}, field="value") for item in value) + "\n"
    return _format_scalar(value, field="value", row={}) + "\n"


__all__ = ["render", "render_records", "render_context_pack"]
