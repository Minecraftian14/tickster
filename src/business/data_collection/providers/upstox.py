from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
import gzip
import json

import httpx

from data_collection.domains.models import CorporateAction, Instrument, MarketQuote, PriceBar, Provenance
from data_collection.processing.instruments import canonical_instrument_id


class UpstoxProvider:
    """Thin REST adapter around documented Upstox APIs."""

    name = "upstox"
    source_type = "broker_api"
    base_url = "https://api.upstox.com"
    instrument_nse_json_url = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"

    def __init__(self, access_token: str, *, timeout: float = 20.0):
        if not access_token:
            raise ValueError("UPSTOX_ACCESS_TOKEN is required")
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
    def parse_candles(payload: dict[str, Any], instrument_id: str, *, timeframe: str, retrieved_at: datetime | None = None) -> list[PriceBar]:
        now = retrieved_at or datetime.now(timezone.utc)
        candles = payload.get("data", {}).get("candles", [])
        out: list[PriceBar] = []
        for c in candles:
            if len(c) < 6:
                continue
            ts = datetime.fromisoformat(str(c[0]).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            out.append(PriceBar(
                instrument_id=instrument_id, timestamp=ts, timeframe=timeframe,
                open=Decimal(str(c[1])) if c[1] is not None else None,
                high=Decimal(str(c[2])) if c[2] is not None else None,
                low=Decimal(str(c[3])) if c[3] is not None else None,
                close=Decimal(str(c[4])) if c[4] is not None else None,
                volume=int(c[5]) if c[5] is not None else None,
                provenance=Provenance(source="upstox", source_type="broker_api", source_dataset="historical-candle-v3", retrieved_at=now, observed_at=ts),
            ))
        return out

    @staticmethod
    def parse_ltp(payload: dict[str, Any], instrument_id_by_key: dict[str, str], retrieved_at: datetime | None = None) -> list[MarketQuote]:
        now = retrieved_at or datetime.now(timezone.utc)
        out: list[MarketQuote] = []
        for key, item in (payload.get("data") or {}).items():
            instrument_id = instrument_id_by_key.get(key, key)
            ltt = item.get("ltt") or item.get("last_trade_time")
            if isinstance(ltt, (int, float)):
                observed = datetime.fromtimestamp(ltt / 1000, tz=timezone.utc)
            elif ltt:
                try:
                    observed = datetime.fromisoformat(str(ltt).replace("Z", "+00:00"))
                    if observed.tzinfo is None:
                        observed = observed.replace(tzinfo=timezone.utc)
                except ValueError:
                    observed = now
            else:
                observed = now
            out.append(MarketQuote(
                instrument_id=instrument_id, timestamp=observed,
                last_price=Decimal(str(item["ltp"])) if item.get("ltp") is not None else None,
                last_trade_quantity=int(item["ltq"]) if item.get("ltq") is not None else None,
                previous_close=Decimal(str(item["cp"])) if item.get("cp") is not None else None,
                volume=int(item["volume"]) if item.get("volume") is not None else None,
                raw_quote=item,
                provenance=Provenance(source="upstox", source_type="broker_api", source_dataset="ltp-v3", retrieved_at=now, observed_at=observed),
            ))
        return out

    @staticmethod
    def parse_full_quotes(payload: dict[str, Any], instrument_id_by_key: dict[str, str], retrieved_at: datetime | None = None) -> list[MarketQuote]:
        now = retrieved_at or datetime.now(timezone.utc)
        out: list[MarketQuote] = []
        for key, item in (payload.get("data") or {}).items():
            instrument_id = instrument_id_by_key.get(key, key)
            ohlc = item.get("live_ohlc") or item.get("ohlc") or {}
            ts = ohlc.get("ts") or item.get("ts")
            if isinstance(ts, (int, float)):
                observed = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            elif ts:
                try:
                    observed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                    if observed.tzinfo is None:
                        observed = observed.replace(tzinfo=timezone.utc)
                except ValueError:
                    observed = now
            else:
                observed = now
            out.append(MarketQuote(
                instrument_id=instrument_id, timestamp=observed,
                last_price=Decimal(str(item["last_price"])) if item.get("last_price") is not None else (Decimal(str(item["ltp"])) if item.get("ltp") is not None else None),
                previous_close=Decimal(str(item["prev_close_price"])) if item.get("prev_close_price") is not None else None,
                day_open=Decimal(str(ohlc["open"])) if ohlc.get("open") is not None else None,
                day_high=Decimal(str(ohlc["high"])) if ohlc.get("high") is not None else None,
                day_low=Decimal(str(ohlc["low"])) if ohlc.get("low") is not None else None,
                volume=int(item["volume"]) if item.get("volume") is not None else (int(ohlc["volume"]) if ohlc.get("volume") is not None else None),
                year_high=Decimal(str(item["year_high"])) if item.get("year_high") is not None else None,
                year_low=Decimal(str(item["year_low"])) if item.get("year_low") is not None else None,
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
