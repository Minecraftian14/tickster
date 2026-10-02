from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from data_collection.providers.nse_public import NSEPublicProvider


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, "", "-", "None", "nan"):
        return None
    try:
        return Decimal(str(value).replace(",", "").replace("%", ""))
    except Exception:
        return None


def _to_int(value: Any) -> int | None:
    if value in (None, "", "-", "None", "nan"):
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except Exception:
        return None


def _first(mapping: dict[str, Any], *names: str) -> Any:
    normalized = {str(k).strip().lower().replace("_", "").replace(" ", ""): k for k in mapping}
    for name in names:
        key = normalized.get(name.lower().replace("_", "").replace(" ", ""))
        if key is not None:
            return mapping[key]
    return None


class NSEIndexProvider:
    """NSE index/industry context built on the project's warmed NSE HTTP adapter."""

    name = "nse"
    source_type = "primary_exchange"
    all_indices_path = "/api/allIndices"
    index_constituents_path = "/api/equity-stockIndices"
    equity_quote_path = "/api/quote-equity"

    def __init__(self, *, nse: NSEPublicProvider | None = None):
        self.nse = nse or NSEPublicProvider()

    def health(self) -> dict[str, Any]:
        return {"provider": self.name, "configured": self.nse is not None}

    def all_indices(self) -> dict[str, Any]:
        return self.nse._get(self.all_indices_path, params={}, referer="/market-data/live-market-indices")

    def index_constituents(self, index: str) -> dict[str, Any]:
        referer = "/market-data/live-market-indices"
        return self.nse._get(self.index_constituents_path, params={"index": index}, referer=referer)

    def equity_quote(self, symbol: str) -> dict[str, Any]:
        referer = f"/get-quotes/equity?symbol={symbol}"
        return self.nse._get(self.equity_quote_path, params={"symbol": symbol}, referer=referer)

    @staticmethod
    def records_from_payload(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        for key in ("records", "rows", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        return []

    @classmethod
    def parse_index_snapshots(cls, payload: dict[str, Any], *, retrieved_at: datetime | None = None):
        now = retrieved_at or datetime.now(timezone.utc)
        out = []
        for row in cls.records_from_payload(payload):
            symbol = str(_first(row, "indexSymbol", "index", "indexName") or "").strip()
            if not symbol:
                continue
            name = str(_first(row, "index", "indexName") or symbol).strip()
            observed = now
            out.append({
                "index_symbol": symbol,
                "index_name": name,
                "timestamp": observed,
                "value": _to_decimal(_first(row, "last", "lastPrice", "value")),
                "change": _to_decimal(_first(row, "variation", "change")),
                "change_percent": _to_decimal(_first(row, "percentChange", "pChange", "changePercent")),
                "previous_close": _to_decimal(_first(row, "previousClose", "prevClose")),
                "open": _to_decimal(_first(row, "open")),
                "high": _to_decimal(_first(row, "high", "dayHigh")),
                "low": _to_decimal(_first(row, "low", "dayLow")),
                "year_high": _to_decimal(_first(row, "yearHigh", "yearlyHigh")),
                "year_low": _to_decimal(_first(row, "yearLow", "yearlyLow")),
                "one_year_return_percent": _to_decimal(_first(row, "perChange365d", "pChange365d")),
                "one_month_return_percent": _to_decimal(_first(row, "perChange30d", "pChange30d")),
                "raw": row,
            })
        return out

    @classmethod
    def parse_constituents(cls, payload: dict[str, Any], *, instrument_ids_by_symbol: dict[str, str] | None = None, retrieved_at: datetime | None = None):
        now = retrieved_at or datetime.now(timezone.utc)
        instrument_ids_by_symbol = {k.upper(): v for k, v in (instrument_ids_by_symbol or {}).items()}
        meta = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        top_name = str(_first(meta, "indexName", "name", "index") or "").strip() or None
        out = []
        rows = cls.records_from_payload(payload)
        for rank, row in enumerate(rows, 1):
            symbol = str(_first(row, "symbol", "symbolName", "ticker") or "").strip().upper()
            if not symbol:
                continue
            index_symbol = str(_first(row, "indexSymbol", "index", "indexName") or meta.get("indexSymbol") or top_name or "").strip()
            out.append({
                "index_symbol": index_symbol,
                "index_name": top_name or index_symbol,
                "instrument_id": instrument_ids_by_symbol.get(symbol),
                "symbol": symbol,
                "company_name": _first(row, "identifier", "companyName", "company") ,
                "weight_percent": _to_decimal(_first(row, "weight", "weightage", "indexWeight")),
                "rank": rank,
                "price": _to_decimal(_first(row, "lastPrice", "ltp", "price")),
                "change": _to_decimal(_first(row, "change", "variation")),
                "change_percent": _to_decimal(_first(row, "pChange", "percentChange", "changePercent")),
                "market_cap": _to_decimal(_first(row, "marketCap", "marketCapitalisation")),
                "free_float_market_cap": _to_decimal(_first(row, "ffmc", "freeFloatMarketCap", "freeFloatMcap")),
                "volume": _to_int(_first(row, "totalTradedVolume", "volume")),
                "traded_value": _to_decimal(_first(row, "totalTradedValue", "tradedValue")),
                "raw": row,
            })
        return out

    @classmethod
    def parse_sector_classification(cls, payload: dict[str, Any], *, symbol: str, instrument_id: str, retrieved_at: datetime | None = None):
        now = retrieved_at or datetime.now(timezone.utc)
        info = payload.get("industryInfo") if isinstance(payload.get("industryInfo"), dict) else {}
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        return {
            "instrument_id": instrument_id,
            "symbol": symbol.upper(),
            "sector_macro": _first(info, "macro") or _first(metadata, "macro"),
            "sector": _first(info, "sector") or _first(metadata, "sector"),
            "industry": _first(info, "industry") or _first(metadata, "industry"),
            "basic_industry": _first(info, "basicIndustry", "basic_industry") or _first(metadata, "basicIndustry", "basic_industry"),
            "classification_as_of": _parse_last_update(payload, now),
            "metadata": {"raw": payload},
        }


def _parse_last_update(payload: dict[str, Any], fallback: datetime) -> datetime:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    raw = _first(metadata, "lastUpdateTime", "lastUpdate", "lastUpdated")
    if not raw:
        return fallback
    from dateutil.parser import parse
    try:
        dt = parse(str(raw), dayfirst=True)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except Exception:
        return fallback
