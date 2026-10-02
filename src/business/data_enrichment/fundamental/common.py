from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
import math
import re
from typing import Any, Iterable

from ..core.context import EnrichmentContext


@dataclass(frozen=True)
class FinancialPoint:
    """Normalized internal view of one point in a fundamental statement series."""

    timestamp: datetime
    period_end: date | None
    period_type: str | None
    statement_type: str | None
    statement_name: str | None
    values: dict[str, float]
    source_record: Any
    raw_metric_names: dict[str, str]
    source_records: tuple[Any, ...] = ()
    metric_source_records: dict[str, tuple[Any, ...]] = field(default_factory=dict)


def _as_float(value: Any) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def normalize_key(value: Any) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _flatten_metrics(node: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[str, float]]:
    """Flatten nested financial payloads while preserving leaf and value-style fields."""
    if isinstance(node, dict):
        if "value" in node:
            numeric = _as_float(node.get("value"))
            if numeric is not None:
                key = normalize_key(" ".join(path))
                if key:
                    yield key, numeric
        for key, value in node.items():
            normalized = normalize_key(key)
            next_path = path + ((normalized,) if normalized else ())
            if normalized == "value":
                continue
            if isinstance(value, (dict, list, tuple)):
                yield from _flatten_metrics(value, next_path)
            else:
                numeric = _as_float(value)
                if numeric is not None:
                    leaf_key = normalize_key(" ".join(next_path))
                    if leaf_key:
                        yield leaf_key, numeric
    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from _flatten_metrics(item, path)


# Aliases deliberately describe concepts rather than provider field names only.
# More aliases can be added without changing any enricher implementation.
METRIC_ALIASES: dict[str, tuple[str, ...]] = {
    "revenue": (
        "revenue", "total revenue", "revenue from operations", "net sales", "sales", "operating revenue",
    ),
    "gross_profit": ("gross profit",),
    "ebitda": ("ebitda", "earnings before interest tax depreciation and amortization"),
    "ebit": ("ebit", "operating profit", "operating income", "profit from operations"),
    "ebt": ("profit before tax", "pbt", "ebt", "profit before income tax"),
    "net_income": ("profit after tax", "pat", "net profit", "net income", "profit attributable to owners", "profit attributable to shareholders"),
    "eps": ("eps", "earning per share", "earnings per share", "diluted eps", "basic eps"),
    "total_assets": ("total assets",),
    "current_assets": ("current assets",),
    "current_liabilities": ("current liabilities",),
    "inventory": ("inventory", "inventories"),
    "cash": ("cash and cash equivalents", "cash equivalents", "cash & cash equivalents", "cash"),
    "total_equity": ("total equity", "shareholders equity", "shareholder equity", "total shareholders equity", "equity attributable to owners"),
    "total_debt": ("total debt", "total borrowings", "borrowings", "interest bearing debt", "debt"),
    "interest_expense": ("interest expense", "finance costs", "finance cost", "interest and finance charges"),
    "operating_cash_flow": ("operating cash flow", "cash flow from operations", "net cash from operating activities", "cash generated from operations"),
    "capital_expenditure": ("capital expenditure", "capex", "purchase of property plant and equipment", "purchase of fixed assets", "purchase of property plant equipment"),
    "free_cash_flow": ("free cash flow",),
    "tax_expense": ("tax expense", "income tax expense", "taxation"),
}


def resolve_metric(flat: dict[str, float], canonical_name: str) -> tuple[float | None, str | None]:
    """Resolve one conceptual metric from normalized leaves, preferring exact matches."""
    aliases = METRIC_ALIASES.get(canonical_name, (canonical_name,))
    normalized_aliases = [normalize_key(alias) for alias in aliases]
    exact = {key: value for key, value in flat.items() if key in normalized_aliases}
    if exact:
        key = normalized_aliases[0]
        if key in exact:
            return exact[key], key
        chosen_key = next(iter(exact))
        return exact[chosen_key], chosen_key

    # Permit nested keys such as "income statement revenue" while avoiding
    # unrelated concepts that happen to contain the alias as a substring.
    for alias in normalized_aliases:
        matches = [(key, value) for key, value in flat.items() if key.endswith(" " + alias) or key == alias]
        if matches:
            key, value = sorted(matches, key=lambda item: (len(item[0]), item[0]))[0]
            return value, key
    return None, None


def _period_end(record: Any) -> date | None:
    direct = getattr(record, "period_end", None)
    if isinstance(direct, datetime):
        return direct.date()
    if isinstance(direct, date):
        return direct
    payload = EnrichmentContext.payload(record)
    value = payload.get("period_end") or payload.get("period") or payload.get("period_label")
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        from datetime import datetime as dt
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%b %Y", "%B %Y"):
            try:
                parsed = dt.strptime(value.strip(), fmt)
                if fmt in ("%b %Y", "%B %Y"):
                    import calendar
                    return date(parsed.year, parsed.month, calendar.monthrange(parsed.year, parsed.month)[1])
                return parsed.date()
            except ValueError:
                continue
    return None


def _period_type(record: Any) -> str | None:
    value = getattr(record, "period_type", None)
    if value:
        return str(value).lower()
    payload = EnrichmentContext.payload(record)
    value = payload.get("period_type")
    return str(value).lower() if value else None


def _statement_name(record: Any) -> str | None:
    value = getattr(record, "statement_name", None)
    if value:
        return str(value)
    payload = EnrichmentContext.payload(record)
    value = payload.get("statement_name")
    return str(value) if value else None


def _statement_type(record: Any) -> str | None:
    value = getattr(record, "statement_type", None)
    if value:
        return str(value)
    payload = EnrichmentContext.payload(record)
    value = payload.get("statement_type")
    return str(value) if value else None


def period_timestamp(period_end: date) -> datetime:
    return datetime.combine(period_end, time.min, tzinfo=timezone.utc)


def _available_at(record: Any) -> datetime | None:
    envelope = EnrichmentContext.temporal(record)
    return envelope.available_at


def extract_financial_points(context: EnrichmentContext, *, statement_name: str | None = None) -> list[FinancialPoint]:
    points: list[FinancialPoint] = []
    for record in context.records_for_instrument():
        if str(getattr(record, "record_type", "")) != "FundamentalSnapshot" and _statement_name(record) is None:
            continue
        name = _statement_name(record)
        if statement_name and name != statement_name:
            continue
        period_end = _period_end(record)
        if period_end is None:
            continue
        payload = EnrichmentContext.payload(record)
        metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else getattr(record, "metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}
        flat = dict(_flatten_metrics(metrics))
        values: dict[str, float] = {}
        raw_names: dict[str, str] = {}
        for canonical in METRIC_ALIASES:
            value, raw_name = resolve_metric(flat, canonical)
            if value is not None:
                values[canonical] = value
                raw_names[canonical] = raw_name or canonical
        timestamp_value = _available_at(record) or EnrichmentContext.temporal(record).event_time
        if timestamp_value is None:
            timestamp_value = period_timestamp(period_end)
        elif isinstance(timestamp_value, date) and not isinstance(timestamp_value, datetime):
            timestamp_value = period_timestamp(timestamp_value)
        elif isinstance(timestamp_value, datetime) and timestamp_value.tzinfo is None:
            timestamp_value = timestamp_value.replace(tzinfo=timezone.utc)
        points.append(FinancialPoint(
            timestamp=period_timestamp(period_end),
            period_end=period_end,
            period_type=_period_type(record),
            statement_type=_statement_type(record),
            statement_name=name,
            values=values,
            source_record=record,
            raw_metric_names=raw_names,
            source_records=(record,),
            metric_source_records={metric: (record,) for metric in values},
        ))
    points.sort(key=lambda point: (point.period_end or date.min, point.statement_name or "", point.statement_type or ""))
    return points




def records_for_point(point: FinancialPoint) -> tuple[Any, ...]:
    return point.source_records or (point.source_record,)

def records_for_metric(point: FinancialPoint, metric: str) -> tuple[Any, ...]:
    return point.metric_source_records.get(metric, records_for_point(point))


def available_at_for_point(point: FinancialPoint):
    values = [EnrichmentContext.temporal(record).available_at for record in records_for_point(point)]
    values = [value for value in values if value is not None]
    return max(values) if values else None


def available_at_for_metric(point: FinancialPoint, metric: str):
    values = [EnrichmentContext.temporal(record).available_at for record in records_for_metric(point, metric)]
    values = [value for value in values if value is not None]
    return max(values) if values else None


def merge_financial_periods(points: Iterable[FinancialPoint]) -> list[FinancialPoint]:
    """Merge same-period statement snapshots into one analytical period.

    Income, balance-sheet and cash-flow statements commonly arrive as separate
    records. Derived ratios often need fields from more than one statement, so
    the enrichment layer combines them while retaining every source record.
    """
    buckets: dict[tuple[date, str | None, str | None], list[FinancialPoint]] = {}
    for point in points:
        if point.period_end is None:
            continue
        key = (point.period_end, point.period_type, point.statement_type)
        buckets.setdefault(key, []).append(point)

    merged: list[FinancialPoint] = []
    for (period_end, period_type, statement_type), bucket in buckets.items():
        values: dict[str, float] = {}
        raw_names: dict[str, str] = {}
        metric_records: dict[str, tuple[Any, ...]] = {}
        records: list[Any] = []
        for point in bucket:
            for metric, value in point.values.items():
                # Prefer the first deterministic value. Reconciliation belongs to
                # data_foundation; enrichment never silently blends observations.
                if metric not in values:
                    values[metric] = value
                    raw_names[metric] = point.raw_metric_names.get(metric, metric)
                    metric_records[metric] = records_for_metric(point, metric)
            records.extend(records_for_point(point))
        unique_records = []
        seen: set[str] = set()
        for record in records:
            rid = EnrichmentContext.record_id(record) or f"anonymous:{id(record)}"
            if rid not in seen:
                seen.add(rid)
                unique_records.append(record)
        primary = bucket[0].source_record
        merged.append(FinancialPoint(
            timestamp=period_timestamp(period_end),
            period_end=period_end,
            period_type=period_type,
            statement_type=statement_type,
            statement_name="combined",
            values=values,
            source_record=primary,
            raw_metric_names=raw_names,
            source_records=tuple(unique_records),
            metric_source_records=metric_records,
        ))
    merged.sort(key=lambda point: (point.period_end or date.min, point.period_type or "", point.statement_type or ""))
    return merged


def period_gap_is_valid(previous: date, current: date, *, period_type: str | None, lag: int) -> bool:
    text = (period_type or "").lower()
    if "quarter" in text:
        return quarter_index(current) - quarter_index(previous) == lag
    if "year" in text:
        return current.year - previous.year == lag
    return True

def group_statement_points(points: Iterable[FinancialPoint]) -> dict[tuple[str | None, str | None], list[FinancialPoint]]:
    groups: dict[tuple[str | None, str | None], list[FinancialPoint]] = {}
    for point in points:
        key = (point.statement_name, point.statement_type)
        groups.setdefault(key, []).append(point)
    for items in groups.values():
        items.sort(key=lambda item: item.period_end or date.min)
    return groups


def ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def average(previous: float | None, current: float | None) -> float | None:
    if previous is None or current is None:
        return None
    return (previous + current) / 2.0


def quarter_number(value: date) -> int:
    return (value.month - 1) // 3 + 1


def quarter_index(value: date) -> int:
    return value.year * 4 + quarter_number(value)
