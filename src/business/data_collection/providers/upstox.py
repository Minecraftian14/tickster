from __future__ import annotations

import gzip
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from data_collection.domains.models import CorporateAction, Instrument, MarketQuote, PriceBar, Provenance
from data_collection.processing.instruments import canonical_instrument_id


def _decimal(value: Any) -> Decimal | None:
    if value in (None, "", "-", "None", "nan", "NaN"):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except Exception:
        return None


def _int(value: Any) -> int | None:
    if value in (None, "", "-", "None", "nan", "NaN"):
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def _parse_epoch_millis(value: Any, *, issues: list[dict[str, Any]] | None, context: dict[str, Any]) -> datetime | None:
    if value in (None, "", "-", "None"):
        return None
    try:
        return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc)
    except Exception as exc:
        if issues is not None:
            issues.append({"source": "upstox", "operation": "parse_timestamp", "message": str(exc), **context, "raw": value})
        return None


def _parse_timestamp(value: Any, *, default: datetime | None, issues: list[dict[str, Any]] | None, context: dict[str, Any]) -> datetime:
    if isinstance(value, (int, float)):
        parsed = _parse_epoch_millis(value, issues=issues, context=context)
        return parsed or default or datetime.now(timezone.utc)
    if value:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError as exc:
            if issues is not None:
                issues.append({"source": "upstox", "operation": "parse_timestamp", "message": str(exc), **context, "raw": value})
    if default is not None:
        return default
    raise ValueError(f"Unable to parse required timestamp: {value!r}")


class UpstoxProvider:
    """Thin REST adapter around documented Upstox APIs."""

    name = "upstox"
    source_type = "broker_api"
    base_url = "https://api.upstox.com"
    instrument_nse_json_url = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"

    def __init__(self, access_token: str, *, timeout: float = 20.0):
        if not access_token:
            raise ValueError("upstox_connector.upstox.anaytics_token is required")
        self.access_token = access_token
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Accept": "application/json", "Authorization": f"Bearer {access_token}"},
        )

    def close(self) -> None:
        self.client.close()

    def health(self) -> dict:
        return {"provider": self.name, "configured": bool(self.access_token)}

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.client.get(path, params=params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError(f"Expected JSON object from {path}, got {type(payload).__name__}")
        return payload

    def search_instruments(self, query: str, *, exchanges: str = "NSE", segments: str = "EQ", page_number: int = 1, records: int = 30) -> dict[str, Any]:
        return self._get("/v2/instruments/search", params={
            "query": query, "exchanges": exchanges, "segments": segments,
            "page_number": page_number, "records": records,
        })

    def download_nse_instrument_file(self) -> bytes:
        """Download the current Upstox NSE BOD instrument file as raw bytes."""
        response = httpx.get(self.instrument_nse_json_url, timeout=60.0)
        response.raise_for_status()
        return response.content

    @staticmethod
    def parse_instrument_file(payload: bytes) -> list[dict[str, Any]]:
        """Parse the compressed Upstox NSE instrument artifact.

        The parser accepts either a JSON array/object or JSON Lines so minor
        transport-format changes do not leak into the collection layer.
        """
        raw = gzip.decompress(payload) if payload[:2] == b"\x1f\x8b" else payload
        text = raw.decode("utf-8")
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            return [json.loads(line) for line in text.splitlines() if line.strip()]
        if isinstance(decoded, list):
            return [x for x in decoded if isinstance(x, dict)]
        if isinstance(decoded, dict):
            data = decoded.get("data")
            if isinstance(data, list):
                return [x for x in data if isinstance(x, dict)]
            return [decoded]
        raise TypeError(f"Unsupported instrument-file JSON shape: {type(decoded).__name__}")

    def historical_candles_v3(self, instrument_key: str, unit: str, interval: int, to_date: date, from_date: date | None = None) -> dict[str, Any]:
        path = f"/v3/historical-candle/{instrument_key}/{unit}/{interval}/{to_date.isoformat()}"
        if from_date is not None:
            path += f"/{from_date.isoformat()}"
        return self._get(path)

    def intraday_candles_v3(self, instrument_key: str, unit: str = "minutes", interval: int = 1) -> dict[str, Any]:
        return self._get(f"/v3/historical-candle/intraday/{instrument_key}/{unit}/{interval}")

    def ltp_v3(self, instrument_keys: list[str]) -> dict[str, Any]:
        return self._get("/v3/market-quote/ltp", params={"instrument_key": ",".join(instrument_keys)})

    def ohlc_v3(self, instrument_keys: list[str], interval: str = "1d") -> dict[str, Any]:
        return self._get("/v3/market-quote/ohlc", params={"instrument_key": ",".join(instrument_keys), "interval": interval})

    def full_quotes_v3(self, instrument_keys: list[str]) -> dict[str, Any]:
        return self._get("/v3/market-quote/quotes", params={"instrument_key": ",".join(instrument_keys)})

    def income_statement(self, isin: str, *, statement_type: str = "consolidated", time_period: str = "yearly", full_statement: bool = False) -> dict[str, Any]:
        return self._get(f"/v2/fundamentals/{isin}/income-statement", params={"type": statement_type, "time_period": time_period, "fs": "true" if full_statement else "false"})

    def cash_flow(self, isin: str, *, statement_type: str = "consolidated", full_statement: bool = False) -> dict[str, Any]:
        return self._get(f"/v2/fundamentals/{isin}/cash-flow", params={"type": statement_type, "fs": "true" if full_statement else "false"})

    def key_ratios(self, isin: str) -> dict[str, Any]:
        return self._get(f"/v2/fundamentals/{isin}/key-ratios")

    def share_holdings(self, isin: str) -> dict[str, Any]:
        return self._get(f"/v2/fundamentals/{isin}/share-holdings")

    def corporate_actions(self, isin: str) -> dict[str, Any]:
        return self._get(f"/v2/fundamentals/{isin}/corporate-actions")

    def company_profile(self, isin: str) -> dict[str, Any]:
        return self._get(f"/v2/fundamentals/{isin}/profile")

    def competitors(self, isin: str) -> dict[str, Any]:
        return self._get(f"/v2/fundamentals/{isin}/competitors")

    def balance_sheet(self, isin: str, *, full_statement: bool = False, statement_type: str = "consolidated") -> dict[str, Any]:
        return self._get(f"/v2/fundamentals/{isin}/balance-sheet", params={"fs": "true" if full_statement else "false", "type": statement_type})

    @staticmethod
    def normalize_instrument(item: dict[str, Any], retrieved_at: datetime | None = None) -> Instrument:
        now = retrieved_at or datetime.now(timezone.utc)
        symbol = str(item.get("trading_symbol") or item.get("short_name") or item.get("name") or "").strip()
        exchange = item.get("exchange")
        isin = item.get("isin")
        return Instrument(
            instrument_id=canonical_instrument_id(isin=isin, exchange=exchange, symbol=symbol),
            isin=isin, symbol=symbol,
            provider_identifiers={'upstox': isin},
            exchange=exchange if exchange in {"NSE", "BSE", "OTHER"} else "OTHER",
            segment=item.get("segment"), instrument_key=item.get("instrument_key"),
            exchange_token=str(item["exchange_token"]) if item.get("exchange_token") is not None else None,
            tick_size=Decimal(str(item["tick_size"])) if item.get("tick_size") is not None else None,
            lot_size=int(item["lot_size"]) if item.get("lot_size") is not None else None,
            freeze_quantity=Decimal(str(item["freeze_quantity"])) if item.get("freeze_quantity") is not None else None,
            name=item.get("name"), short_name=item.get("short_name"),
            security_type=item.get("security_type"), currency="INR", active=True,
            cas_eligible=item.get("cas_eligible"),
            provenance=Provenance(source="upstox", source_type="broker_api", source_dataset="instrument-search", retrieved_at=now),
        )

    @staticmethod
    def parse_candles(payload: dict[str, Any], instrument_id: str, *, timeframe: str, retrieved_at: datetime | None = None, issues: list[dict[str, Any]] | None = None) -> list[PriceBar]:
        now = retrieved_at or datetime.now(timezone.utc)
        candles = ((payload.get("data") or {}).get("candles") or [])
        out: list[PriceBar] = []
        for index, c in enumerate(candles):
            try:
                if not isinstance(c, (list, tuple)) or len(c) < 6:
                    raise ValueError("candle must contain at least timestamp + OHLCV")
                ts = _parse_timestamp(c[0], default=None, issues=issues, context={"row": index, "field": "timestamp"})
                out.append(PriceBar(
                    instrument_id=instrument_id, timestamp=ts, timeframe=timeframe,
                    open=_decimal(c[1]), high=_decimal(c[2]), low=_decimal(c[3]), close=_decimal(c[4]),
                    volume=_int(c[5]),
                    provenance=Provenance(source="upstox", source_type="broker_api", source_dataset="historical-candle-v3", retrieved_at=now, observed_at=ts),
                ))
            except Exception as exc:
                if issues is not None:
                    issues.append({"source": "upstox", "operation": "parse_candles", "message": str(exc), "row": index, "raw": c})
        return out

    @staticmethod
    def parse_ltp(payload: dict[str, Any], instrument_id_by_key: dict[str, str], retrieved_at: datetime | None = None, *, issues: list[dict[str, Any]] | None = None) -> list[MarketQuote]:
        now = retrieved_at or datetime.now(timezone.utc)
        out: list[MarketQuote] = []
        for key, item in (payload.get("data") or {}).items():
            if not isinstance(item, dict):
                if issues is not None:
                    issues.append({"source": "upstox", "operation": "parse_ltp", "message": "Skipped non-object quote", "instrument_key": key, "raw": item})
                continue
            instrument_id = instrument_id_by_key.get(key, key)
            observed = _parse_timestamp(item.get("ltt") or item.get("last_trade_time"), default=now, issues=issues, context={"instrument_key": key, "field": "last_trade_time"})
            out.append(MarketQuote(
                instrument_id=instrument_id, timestamp=observed,
                last_price=_decimal(item.get("ltp")),
                last_trade_quantity=_int(item.get("ltq")),
                previous_close=_decimal(item.get("cp")),
                volume=_int(item.get("volume")),
                raw_quote=item,
                provenance=Provenance(source="upstox", source_type="broker_api", source_dataset="ltp-v3", retrieved_at=now, observed_at=observed),
            ))
        return out

    @staticmethod
    def parse_full_quotes(payload: dict[str, Any], instrument_id_by_key: dict[str, str], retrieved_at: datetime | None = None, *, issues: list[dict[str, Any]] | None = None) -> list[MarketQuote]:
        now = retrieved_at or datetime.now(timezone.utc)
        out: list[MarketQuote] = []
        for key, item in (payload.get("data") or {}).items():
            if not isinstance(item, dict):
                if issues is not None:
                    issues.append({"source": "upstox", "operation": "parse_full_quotes", "message": "Skipped non-object quote", "instrument_key": key, "raw": item})
                continue
            instrument_id = instrument_id_by_key.get(key, key)
            ohlc = item.get("ohlc") or item.get("live_ohlc") or {}
            if not isinstance(ohlc, dict):
                ohlc = {}
            observed = _parse_timestamp(item.get("timestamp"), default=now, issues=issues, context={"instrument_key": key, "field": "timestamp"})
            ohlc_ts = _parse_timestamp(ohlc.get("ts"), default=None, issues=issues, context={"instrument_key": key, "field": "ohlc.ts"})
            depth = item.get("depth") or {}
            buy = depth.get("buy") if isinstance(depth, dict) else []
            sell = depth.get("sell") if isinstance(depth, dict) else []
            buy = buy if isinstance(buy, list) else []
            sell = sell if isinstance(sell, list) else []
            order_count = sum(_int(level.get("orders")) or 0 for level in [*buy, *sell] if isinstance(level, dict))
            out.append(MarketQuote(
                instrument_id=instrument_id, timestamp=observed,
                last_price=_decimal(item.get("last_price") if item.get("last_price") is not None else item.get("ltp")),
                last_trade_quantity=_int(item.get("last_trade_quantity") if item.get("last_trade_quantity") is not None else item.get("ltq")),
                previous_close=_decimal(item.get("prev_close_price")),
                net_change=_decimal(item.get("net_change")),
                day_open=_decimal(ohlc.get("open")),
                day_high=_decimal(ohlc.get("high")),
                day_low=_decimal(ohlc.get("low")),
                volume=_int(item.get("volume") if item.get("volume") is not None else ohlc.get("volume")),
                year_high=_decimal(item.get("year_high")),
                year_low=_decimal(item.get("year_low")),
                average_price=_decimal(item.get("average_price")),
                total_buy_quantity=_int(item.get("total_buy_quantity")),
                total_sell_quantity=_int(item.get("total_sell_quantity")),
                open_interest=_int(item.get("oi")),
                previous_oi=_int(item.get("previous_oi")),
                oi_day_high=_int(item.get("oi_day_high")),
                oi_day_low=_int(item.get("oi_day_low")),
                last_trade_time=_parse_epoch_millis(item.get("last_trade_time"), issues=issues, context={"instrument_key": key, "field": "last_trade_time"}),
                ohlc_timestamp=ohlc_ts,
                bid_depth=buy,
                ask_depth=sell,
                number_of_orders=order_count,
                circuit_upper=_decimal(item.get("upper_circuit_limit")),
                circuit_lower=_decimal(item.get("lower_circuit_limit")),
                indicative_equilibrium_price=_decimal(item.get("indicative_equilibrium_price")),
                indicative_equilibrium_quantity=_int(item.get("indicative_equilibrium_quantity")),
                indicative_imbalance_quantity_total=_int(item.get("indicative_imbalance_quantity_total")),
                indicative_imbalance_quantity_market=_int(item.get("indicative_imbalance_quantity_market")),
                reference_price=_decimal(item.get("reference_price")),
                cas_eligible=item.get("cas_eligible") if isinstance(item.get("cas_eligible"), bool) else None,
                raw_quote=item,
                provenance=Provenance(source="upstox", source_type="broker_api", source_dataset="full-market-quote-v3", retrieved_at=now, observed_at=observed),
            ))
        return out

    @staticmethod
    def parse_corporate_actions(payload: dict[str, Any], instrument_id: str, retrieved_at: datetime | None = None) -> list[CorporateAction]:
        now = retrieved_at or datetime.now(timezone.utc)
        out: list[CorporateAction] = []
        rows = payload.get("data") if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            return out

        def parse_date(value: Any):
            if value is None or str(value).strip() in {"", "-", "None", "nan"}:
                return None
            from dateutil.parser import parse
            try:
                return parse(str(value), dayfirst=True).date()
            except Exception:
                return None

        for item in rows:
            if not isinstance(item, dict):
                continue
            details = {
                str(x.get("name")): x.get("value")
                for x in (item.get("event_details") or [])
                if isinstance(x, dict) and x.get("name")
            }
            action_type = str(item.get("name") or "unknown").strip().lower().replace(" ", "_")
            amount = item.get("amount")
            try:
                amount = Decimal(str(amount)) if amount is not None else None
            except Exception:
                amount = None
            out.append(CorporateAction(
                instrument_id=instrument_id,
                action_type=action_type,
                announcement_date=parse_date(details.get("Announcement date")),
                ex_date=parse_date(details.get("Ex dividend date") or details.get("Ex-Date") or item.get("expiry_date")),
                record_date=parse_date(details.get("Record date")),
                amount=amount,
                ratio=str(item["ratio"]) if item.get("ratio") is not None else None,
                details={**item, "event_details_normalized": details},
                provenance=Provenance(
                    source="upstox", source_type="broker_api", source_dataset="corporate-actions", retrieved_at=now,
                ),
            ))
        return out

    def corporate_actions_normalized(self, isin: str, instrument_id: str) -> list[CorporateAction]:
        payload = self.corporate_actions(isin)
        now = datetime.now(timezone.utc)
        out: list[CorporateAction] = []
        for item in payload.get("data", []) if isinstance(payload.get("data"), list) else []:
            details = {
                str(x.get("name")): x.get("value")
                for x in (item.get("event_details") or [])
                if isinstance(x, dict) and x.get("name")
            }

            def date_value(*names: str):
                for name in names:
                    if name in details:
                        return details[name]
                return None

            out.append(CorporateAction(
                instrument_id=instrument_id,
                action_type=str(item.get("name") or "unknown").lower().replace(" ", "_"),
                announcement_date=date_value("Announcement date"),
                ex_date=date_value("Ex dividend date", "Ex-Date", "Ex date", "Ex Date"),
                record_date=date_value("Record date", "Record Date"),
                amount=Decimal(str(item["amount"])) if item.get("amount") is not None else None,
                ratio=str(item["ratio"]) if item.get("ratio") is not None else None,
                details={**item, "event_details_normalized": details},
                provenance=Provenance(source="upstox", source_type="broker_api", source_dataset="corporate-actions", retrieved_at=now),
            ))
        return out
