from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from data_collection.domains.models import CorporateAction, PriceBar, Provenance


class UpstoxProvider:
    """Thin REST adapter; deliberately independent of the Upstox generated SDK."""

    name = "upstox"
    source_type = "broker_api"
    base_url = "https://api.upstox.com"

    def __init__(self, access_token: str, *, timeout: float = 20.0):
        if not access_token:
            raise ValueError("UPSTOX_ACCESS_TOKEN is required")
        self.access_token = access_token
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
        )

    def health(self) -> dict:
        return {"provider": self.name, "configured": bool(self.access_token)}

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def search_instruments(
            self,
            query: str,
            *,
            exchanges: str = "NSE",
            segments: str = "EQ",
            page_number: int = 1,
            records: int = 30,
    ) -> dict[str, Any]:
        return self._get(
            "/v2/instruments/search",
            params={
                "query": query,
                "exchanges": exchanges,
                "segments": segments,
                "page_number": page_number,
                "records": records,
            },
        )

    def historical_candles_v3(
            self,
            instrument_key: str,
            unit: str,
            interval: int,
            to_date: date,
            from_date: date,
    ) -> dict[str, Any]:
        # V3 path: /v3/historical-candle/{instrument}/{unit}/{interval}/{to}/{from}
        path = (
            f"/v3/historical-candle/{instrument_key}/"
            f"{unit}/{interval}/{to_date.isoformat()}/{from_date.isoformat()}"
        )
        return self._get(path)

    def income_statement(self, isin: str, *, statement_type: str = "consolidated", time_period: str = "yearly", full_statement: bool = False) -> dict[str, Any]:
        return self._get(
            f"/v2/fundamentals/{isin}/income-statement",
            params={"type": statement_type, "time_period": time_period, "fs": "true" if full_statement else "false"},
        )

    def cash_flow(self, isin: str, *, statement_type: str = "consolidated", full_statement: bool = False) -> dict[str, Any]:
        return self._get(
            f"/v2/fundamentals/{isin}/cash-flow",
            params={"type": statement_type, "fs": "true" if full_statement else "false"},
        )

    def key_ratios(self, isin: str) -> dict[str, Any]:
        return self._get(f"/v2/fundamentals/{isin}/key-ratios")

    def share_holdings(self, isin: str) -> dict[str, Any]:
        return self._get(f"/v2/fundamentals/{isin}/share-holdings")

    def corporate_actions(self, isin: str) -> dict[str, Any]:
        return self._get(f"/v2/fundamentals/{isin}/corporate-actions")

    def company_profile(self, isin: str) -> dict[str, Any]:
        return self._get(f"/v2/fundamentals/{isin}/profile")

    def balance_sheet(self, isin: str, *, full_statement: bool = False) -> dict[str, Any]:
        return self._get(
            f"/v2/fundamentals/{isin}/balance-sheet",
            params={"fs": "true" if full_statement else "false"},
        )

    @staticmethod
    def parse_candles(
            payload: dict[str, Any],
            instrument_id: str,
            *,
            timeframe: str,
            retrieved_at: datetime | None = None,
    ) -> list[PriceBar]:
        now = retrieved_at or datetime.now(timezone.utc)
        # Upstox candle arrays are documented as [timestamp, open, high, low, close, volume, OI]
        candles = payload.get("data", {}).get("candles", [])
        out: list[PriceBar] = []
        for c in candles:
            ts = datetime.fromisoformat(str(c[0]).replace("Z", "+00:00"))
            out.append(PriceBar(
                instrument_id=instrument_id,
                timestamp=ts,
                timeframe=timeframe,
                open=Decimal(str(c[1])),
                high=Decimal(str(c[2])),
                low=Decimal(str(c[3])),
                close=Decimal(str(c[4])),
                volume=int(c[5]) if c[5] is not None else None,
                provenance=Provenance(
                    source="upstox",
                    source_type="broker_api",
                    source_dataset="historical-candle-v3",
                    retrieved_at=now,
                    observed_at=ts,
                ),
            ))
        return out

    def corporate_actions_normalized(self, isin: str, instrument_id: str) -> list[CorporateAction]:
        payload = self.corporate_actions(isin)
        now = datetime.now(timezone.utc)
        out: list[CorporateAction] = []
        for item in payload.get("data", []) if isinstance(payload.get("data"), list) else []:
            out.append(CorporateAction(
                instrument_id=instrument_id,
                action_type=str(item.get("action_type") or item.get("type") or "unknown").lower(),
                announcement_date=item.get("announcement_date"),
                ex_date=item.get("ex_date"),
                record_date=item.get("record_date"),
                amount=Decimal(str(item["amount"])) if item.get("amount") is not None else None,
                ratio=str(item.get("ratio")) if item.get("ratio") is not None else None,
                details=item,
                provenance=Provenance(
                    source="upstox",
                    source_type="broker_api",
                    source_dataset="corporate-actions",
                    retrieved_at=now,
                ),
            ))
        return out
