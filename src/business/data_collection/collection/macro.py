from __future__ import annotations

from datetime import datetime, date, timezone
from hashlib import sha256
from typing import Any, Iterable

from data_collection.collection.results import CollectionResult, RawPayload
from data_collection.domains.models import MacroObservation, Provenance
from data_collection.providers.mospi import MOSPIProvider
from data_collection.providers.rbi import RBIProvider


def _first(row: dict[str, Any], *names: str) -> Any:
    normalized = {str(k).strip().lower().replace("_", "").replace(" ", ""): k for k in row}
    for name in names:
        key = normalized.get(name.lower().replace("_", "").replace(" ", ""))
        if key is not None:
            return row[key]
    return None


def _as_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value)
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%b-%Y", "%Y-%m"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    # ISO date-like fallback; raises ValueError if unusable.
    return datetime.fromisoformat(text).date()


def _rows(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("data", "results", "records", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
        return [payload]
    raise TypeError(f"Unsupported payload type: {type(payload).__name__}")


def observations_from_rows(
    rows: Iterable[dict[str, Any]],
    *,
    source: str,
    source_dataset: str,
    series_id: str | None = None,
    date_fields: tuple[str, ...] = ("date", "observation_date", "period", "month", "year"),
    value_fields: tuple[str, ...] = ("value", "index", "inflation", "rate", "value_numeric"),
    unit: str | None = None,
    metadata_fields: tuple[str, ...] = (),
) -> list[MacroObservation]:
    now = datetime.now(timezone.utc)
    output: list[MacroObservation] = []
    for row in rows:
        raw_date = _first(row, *date_fields)
        raw_value = _first(row, *value_fields)
        if raw_date in (None, "") or raw_value in (None, "", "-"):
            continue
        observed_date = _as_date(raw_date)
        resolved_series = series_id or str(_first(row, "series", "series_id", "series_code", "item", "group") or source_dataset)
        metadata = {k: row[k] for k in metadata_fields if k in row}
        output.append(MacroObservation(
            series_id=str(resolved_series),
            observation_date=observed_date,
            value=raw_value,
            unit=unit or _first(row, "unit", "units"),
            metadata=metadata | {"raw": row},
            provenance=Provenance(
                source=source,
                source_type="primary_macro",
                source_dataset=source_dataset,
                retrieved_at=now,
                observed_at=datetime.combine(observed_date, datetime.min.time(), tzinfo=timezone.utc),
                raw_ref=sha256(repr(row).encode("utf-8")).hexdigest(),
            ),
        ))
    return output


class MacroCollector:
    """High-level collection functions for Indian macro context."""

    domain = "macro"

    def __init__(self, *, rbi: RBIProvider | None = None, mospi: MOSPIProvider | None = None):
        self.rbi = rbi
        self.mospi = mospi

    def rbi_table(
        self,
        source: str | bytes,
        *,
        source_dataset: str,
        series_id: str,
        format_hint: str = "csv",
        date_fields: tuple[str, ...] = ("date", "observation_date", "period"),
        value_fields: tuple[str, ...] = ("value",),
        unit: str | None = None,
    ) -> CollectionResult[MacroObservation]:
        result: CollectionResult[MacroObservation] = CollectionResult(domain=self.domain)
        if self.rbi is None:
            result.errors.append({"source": "rbi", "error": "provider is not configured"})
            return result
        now = datetime.now(timezone.utc)
        try:
            frame = self.rbi.read_table(source, format_hint=format_hint)
            payload = frame.where(frame.notna(), None).to_dict(orient="records")
            result.raw_payloads.append(RawPayload(source="rbi", domain=self.domain, retrieved_at=now, payload=payload, request={"dataset": source_dataset, "format": format_hint}))
            result.records.extend(observations_from_rows(payload, source="rbi", source_dataset=source_dataset, series_id=series_id, date_fields=date_fields, value_fields=value_fields, unit=unit))
        except Exception as exc:
            result.errors.append({"source": "rbi", "dataset": source_dataset, "error": str(exc)})
        return result

    def mospi_cpi(self, **params: Any) -> CollectionResult[MacroObservation]:
        return self._mospi_collection("getCPIIndex", self.mospi.cpi_index, params)

    def mospi_cpi_item(self, **params: Any) -> CollectionResult[MacroObservation]:
        return self._mospi_collection("getItemIndex", self.mospi.cpi_item_index, params)

    def mospi_iip(self, **params: Any) -> CollectionResult[MacroObservation]:
        return self._mospi_collection("getIIPData", self.mospi.iip, params)

    def _mospi_collection(self, endpoint: str, fetch: Any, params: dict[str, Any]) -> CollectionResult[MacroObservation]:
        result: CollectionResult[MacroObservation] = CollectionResult(domain=self.domain)
        if self.mospi is None:
            result.errors.append({"source": "mospi", "error": "provider is not configured"})
            return result
        now = datetime.now(timezone.utc)
        try:
            payload = fetch(**params)
            result.raw_payloads.append(RawPayload(source="mospi", domain=self.domain, retrieved_at=now, payload=payload, request={"endpoint": endpoint, **params}))
            result.records.extend(observations_from_rows(_rows(payload), source="mospi", source_dataset=endpoint, date_fields=("date", "period", "month", "year", "time"), value_fields=("value", "index", "inflation", "value_index", "rate")))
        except Exception as exc:
            result.errors.append({"source": "mospi", "endpoint": endpoint, "error": str(exc)})
        return result
