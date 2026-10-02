from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Any

from data_collection.collection.results import CollectionResult, RawPayload
from data_collection.domains.indices import IndexConstituent, IndexPriceBar, IndexSnapshot, IndexValuationSnapshot, SectorClassification
from data_collection.domains.models import Instrument, Provenance
from data_collection.processing.indices import deduplicate_index_constituents, deduplicate_index_snapshots
from data_collection.providers.nse_indices import NSEIndexProvider
from data_collection.providers.nse_archives import NSEArchivesProvider


def _first(row: dict[str, Any], *names: str) -> Any:
    normalized = {str(k).strip().lower().replace("_", "").replace(" ", ""): k for k in row}
    for name in names:
        key = normalized.get(name.lower().replace("_", "").replace(" ", ""))
        if key is not None:
            return row[key]
    return None


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, "", "-", "None", "nan"):
        return None
    try:
        return Decimal(str(value).replace(",", "").replace("%", ""))
    except Exception:
        return None


class IndexContextCollector:
    """Collect index levels, index membership and NSE sector classification."""

    domain = "indices"

    def __init__(self, *, nse: NSEIndexProvider | None = None, archives: NSEArchivesProvider | None = None):
        self.nse = nse
        self.archives = archives

    def current_indices(self) -> CollectionResult[IndexSnapshot]:
        result: CollectionResult[IndexSnapshot] = CollectionResult(domain=self.domain)
        if self.nse is None:
            result.errors.append({"source": "nse", "error": "provider is not configured"})
            return result
        now = datetime.now(timezone.utc)
        try:
            payload = self.nse.all_indices()
            result.raw_payloads.append(RawPayload(source="nse", domain=self.domain, retrieved_at=now, payload=payload, request={"endpoint": "allIndices"}))
            for row in self.nse.parse_index_snapshots(payload, retrieved_at=now):
                index_symbol = row.pop("index_symbol")
                index_name = row.pop("index_name")
                result.records.append(IndexSnapshot(
                    index_id=f"NSE:{index_symbol}", index_symbol=index_symbol, index_name=index_name,
                    provenance=Provenance(source="nse", source_type="primary_exchange", source_dataset="allIndices", retrieved_at=now, observed_at=now),
                    **row,
                ))
            result.records = deduplicate_index_snapshots(result.records)
        except Exception as exc:
            result.errors.append({"source": "nse", "endpoint": "allIndices", "error": str(exc)})
        return result

    def constituents(self, index: str, *, instruments: list[Instrument] | None = None) -> CollectionResult[IndexConstituent]:
        result: CollectionResult[IndexConstituent] = CollectionResult(domain=self.domain)
        if self.nse is None:
            result.errors.append({"source": "nse", "error": "provider is not configured"})
            return result
        now = datetime.now(timezone.utc)
        by_symbol = {i.symbol.upper(): i.instrument_id for i in (instruments or [])}
        try:
            payload = self.nse.index_constituents(index)
            result.raw_payloads.append(RawPayload(source="nse", domain=self.domain, retrieved_at=now, payload=payload, request={"endpoint": "equity-stockIndices", "index": index}))
            for row in self.nse.parse_constituents(payload, instrument_ids_by_symbol=by_symbol, retrieved_at=now):
                index_symbol = row.pop("index_symbol")
                index_name = row.pop("index_name")
                symbol = row["symbol"]
                source_key = f"{index_symbol}|{symbol}|{row.get('rank') or ''}"
                result.records.append(IndexConstituent(
                    index_id=f"NSE:{index_symbol}", index_symbol=index_symbol, index_name=index_name,
                    provenance=Provenance(source="nse", source_type="primary_exchange", source_dataset="equity-stockIndices", retrieved_at=now, observed_at=now, raw_ref=sha256(source_key.encode()).hexdigest()),
                    **row,
                ))
            result.records = deduplicate_index_constituents(result.records)
        except Exception as exc:
            result.errors.append({"source": "nse", "endpoint": "equity-stockIndices", "index": index, "error": str(exc)})
        return result

    def sector_classification(self, symbol: str, *, instrument: Instrument | None = None) -> CollectionResult[SectorClassification]:
        result: CollectionResult[SectorClassification] = CollectionResult(domain="sector_classification")
        if self.nse is None:
            result.errors.append({"source": "nse", "error": "provider is not configured"})
            return result
        now = datetime.now(timezone.utc)
        instrument_id = instrument.instrument_id if instrument else f"NSE:{symbol.upper()}"
        try:
            payload = self.nse.equity_quote(symbol)
            result.raw_payloads.append(RawPayload(source="nse", domain=result.domain, retrieved_at=now, payload=payload, request={"endpoint": "quote-equity", "symbol": symbol}))
            parsed = self.nse.parse_sector_classification(payload, symbol=symbol, instrument_id=instrument_id, retrieved_at=now)
            result.records.append(SectorClassification(
                provenance=Provenance(source="nse", source_type="primary_exchange", source_dataset="quote-equity", retrieved_at=now, observed_at=parsed["classification_as_of"]),
                **parsed,
            ))
        except Exception as exc:
            result.errors.append({"source": "nse", "endpoint": "quote-equity", "symbol": symbol, "error": str(exc)})
        return result

    def historical_index(self, index_symbol: str, trading_date: date) -> CollectionResult[IndexPriceBar]:
        result: CollectionResult[IndexPriceBar] = CollectionResult(domain="index_history")
        if self.archives is None:
            result.errors.append({"source": "nse_archives", "error": "provider is not configured"})
            return result
        now = datetime.now(timezone.utc)
        try:
            frame = self.archives.index_daily_close(trading_date)
            payload = frame.where(frame.notna(), None).to_dict(orient="records") if frame is not None else []
            result.raw_payloads.append(RawPayload(source="nse", domain=result.domain, retrieved_at=now, payload=payload, request={"dataset": "ind_close_all", "trading_date": trading_date.isoformat()}))
            for row in payload:
                symbol = str(_first(row, "INDEX_NAME", "index_name", "Index Name", "index") or "").strip()
                if symbol.upper() != index_symbol.upper():
                    continue
                from dateutil.parser import parse
                raw_date = _first(row, "HistoricalDate", "historical_date", "Date", "date") or trading_date
                try:
                    observed_date = parse(str(raw_date), dayfirst=True).date()
                except Exception:
                    observed_date = trading_date
                observed = datetime.combine(observed_date, datetime.min.time(), tzinfo=timezone.utc)
                result.records.append(IndexPriceBar(
                    index_id=f"NSE:{symbol}", index_symbol=symbol, index_name=_first(row, "Index Name", "index_name", "index"), timestamp=observed,
                    open=_to_decimal(_first(row, "OPEN", "open")), high=_to_decimal(_first(row, "HIGH", "high")),
                    low=_to_decimal(_first(row, "LOW", "low")), close=_to_decimal(_first(row, "CLOSE", "close")),
                    provenance=Provenance(source="nse", source_type="primary_exchange", source_dataset="ind_close_all", retrieved_at=now, observed_at=observed),
                ))
        except Exception as exc:
            result.errors.append({"source": "nse_archives", "dataset": "ind_close_all", "index": index_symbol, "trading_date": trading_date.isoformat(), "error": str(exc)})
        return result

    def valuation(self, index_symbol: str, trading_date: date) -> CollectionResult[IndexValuationSnapshot]:
        result: CollectionResult[IndexValuationSnapshot] = CollectionResult(domain="index_valuation")
        if self.archives is None:
            result.errors.append({"source": "nse_archives", "error": "provider is not configured"})
            return result
        now = datetime.now(timezone.utc)
        try:
            frame = self.archives.index_valuation(trading_date)
            payload = frame.where(frame.notna(), None).to_dict(orient="records") if frame is not None else []
            result.raw_payloads.append(RawPayload(source="nse", domain=result.domain, retrieved_at=now, payload=payload, request={"dataset": "pe", "trading_date": trading_date.isoformat()}))
            for row in payload:
                symbol = str(_first(row, "INDEX_NAME", "index_name", "Index Name", "index") or "").strip()
                if symbol.upper() != index_symbol.upper():
                    continue
                result.records.append(IndexValuationSnapshot(
                    index_id=f"NSE:{symbol}", index_symbol=symbol, index_name=_first(row, "Index Name", "index_name", "index"), observation_date=trading_date,
                    pe=_to_decimal(_first(row, "P/E", "PE", "p/e")), pb=_to_decimal(_first(row, "P/B", "PB", "p/b")),
                    dividend_yield=_to_decimal(_first(row, "Div Yield", "Dividend Yield", "DY", "dividend_yield")),
                    metadata={"raw": row},
                    provenance=Provenance(source="nse", source_type="primary_exchange", source_dataset="pe", retrieved_at=now, observed_at=datetime.combine(trading_date, datetime.min.time(), tzinfo=timezone.utc)),
                ))
        except Exception as exc:
            result.errors.append({"source": "nse_archives", "dataset": "pe", "index": index_symbol, "trading_date": trading_date.isoformat(), "error": str(exc)})
        return result

