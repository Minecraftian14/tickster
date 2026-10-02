from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx


class NSEPublicProvider:
    """HTTP adapter for public NSE corporate-information endpoints.

    NSE employs session/cookie checks on several endpoints. The adapter warms a
    session against the relevant page before calling JSON APIs and intentionally
    leaves the raw payload untouched for provenance and re-parsing.
    """

    name = "nse"
    source_type = "primary_exchange"
    base_url = "https://www.nseindia.com"
    shareholding_path = "/api/corporate-share-holdings-master"
    insider_path = "/api/corporates-pit"
    large_deal_path = "/api/snapshot-capital-market-largedeal"

    _headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
        "Referer": "https://www.nseindia.com/",
        "Connection": "keep-alive",
    }

    def __init__(self, *, timeout: float = 20.0):
        self.client = httpx.Client(base_url=self.base_url, timeout=timeout, headers=self._headers)
        self._warmed = False

    def close(self) -> None:
        self.client.close()

    def health(self) -> dict[str, Any]:
        return {"provider": self.name, "configured": True, "session_warmed": self._warmed}

    def _warm(self, referer: str) -> None:
        if self._warmed:
            return
        response = self.client.get(referer)
        response.raise_for_status()
        self._warmed = True

    def _get(self, path: str, *, params: dict[str, Any], referer: str) -> dict[str, Any]:
        self._warm(referer)
        response = self.client.get(path, params=params, headers={"Referer": referer})
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError(f"Expected JSON object from {path}, got {type(payload).__name__}")
        return payload

    def shareholding(self, symbol: str, *, index: str = "equities") -> dict[str, Any]:
        referer = f"/companies-listing/corporate-filings-shareholding-pattern?symbol={quote(symbol)}"
        return self._get(self.shareholding_path, params={"index": index, "symbol": symbol}, referer=referer)

    def insider_trading(self, start: date, end: date, *, symbol: str | None = None, index: str = "equities") -> dict[str, Any]:
        referer = "/companies-listing/corporate-filings-insider-trading"
        params: dict[str, Any] = {
            "index": index,
            "from_date": start.strftime("%d-%m-%Y"),
            "to_date": end.strftime("%d-%m-%Y"),
        }
        if symbol:
            params["symbol"] = symbol
        return self._get(self.insider_path, params=params, referer=referer)

    def large_deals(self, mode: str = "bulk_deals") -> dict[str, Any]:
        if mode not in {"bulk_deals", "block_deals", "short_deals"}:
            raise ValueError("mode must be bulk_deals, block_deals, or short_deals")
        referer = "/report-detail/display-bulk-and-block-deals"
        return self._get(self.large_deal_path, params={"mode": mode}, referer=referer)

    @staticmethod
    def health_timestamp() -> datetime:
        return datetime.now(timezone.utc)
