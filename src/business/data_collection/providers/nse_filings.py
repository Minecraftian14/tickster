from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
from typing import Any
from urllib.parse import urljoin, quote

import httpx

from data_collection.domains.filings import Filing, DocumentAsset
from data_collection.domains.models import Instrument, Provenance


class NSEFilingsProvider:
    """Session-aware adapter for NSE corporate-filing catalogs and assets.

    The provider exposes catalog methods plus raw asset downloads. Parsing and
    canonicalization stay in the collection/processing layers.
    """

    name = "nse_filings"
    source_type = "primary_exchange"
    base_url = "https://www.nseindia.com"

    _headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
        "Referer": "https://www.nseindia.com/",
        "Connection": "keep-alive",
    }

    def __init__(self, *, timeout: float = 30.0):
        self.client = httpx.Client(base_url=self.base_url, timeout=timeout, headers=self._headers)
        self._warmed = False

    def close(self) -> None:
        self.client.close()

    def health(self) -> dict[str, Any]:
        return {"provider": self.name, "configured": True, "session_warmed": self._warmed}

    def _warm(self, referer: str) -> None:
        response = self.client.get(referer)
        response.raise_for_status()
        self._warmed = True

    def _get_json(self, path: str, *, params: dict[str, Any], referer: str) -> Any:
        self._warm(referer)
        response = self.client.get(path, params=params, headers={"Referer": referer})
        response.raise_for_status()
        return response.json()

    def _get_bytes(self, url: str) -> httpx.Response:
        absolute = urljoin(self.base_url, url)
        # Asset URLs may live under nsearchives.nseindia.com / archives.nseindia.com.
        client = self.client if absolute.startswith(self.base_url) else httpx.Client(timeout=self.client.timeout, headers=self._headers)
        try:
            response = client.get(absolute, follow_redirects=True)
            response.raise_for_status()
            return response
        finally:
            if client is not self.client:
                client.close()

    def corporate_announcements(
        self,
        *,
        symbol: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        index: str = "equities",
        subject: str | None = None,
    ) -> Any:
        """Return NSE corporate announcements over a date range.

        This is the broad disclosure feed: unlike specialized filing pages, the
        response carries the announcement category/description plus attachment
        and XBRL links when available. It is therefore an important catch-all
        source for the document/event corpus.
        """
        if from_date or to_date:
            if not (from_date and to_date):
                raise ValueError("from_date and to_date must be provided together")
        params: dict[str, Any] = {"index": index}
        if symbol:
            params["symbol"] = symbol
        if from_date and to_date:
            params["from_date"] = from_date.strftime("%d-%m-%Y")
            params["to_date"] = to_date.strftime("%d-%m-%Y")
        if subject:
            params["subject"] = subject
        referer = "/companies-listing/corporate-filings-announcements"
        return self._get_json("/api/corporate-announcements", params=params, referer=referer)

    def financial_results(
        self,
        *,
        symbol: str | None = None,
        period: str = "Quarterly",
        index: str = "equities",
    ) -> Any:
        params: dict[str, Any] = {"index": index, "period": period}
        if symbol:
            params["symbol"] = symbol
        referer = "/companies-listing/corporate-filings-financial-results"
        return self._get_json("/api/corporates-financial-results", params=params, referer=referer)

    def integrated_filing_results(
        self,
        *,
        symbol: str | None = None,
        issuer: str | None = None,
        index: str = "equities",
        period_ended: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        filing_type: str = "Integrated Filing- Financials",
        page: int = 1,
        size: int = 20,
    ) -> Any:
        params: dict[str, Any] = {
            "type": filing_type,
            "page": page,
            "size": size,
            "index": index,
        }
        if symbol:
            params["symbol"] = symbol
        if issuer:
            params["issuer"] = issuer
        if period_ended:
            params["period_ended"] = period_ended
        if from_date or to_date:
            if not (from_date and to_date):
                raise ValueError("from_date and to_date must be provided together")
            params["from_date"] = from_date.strftime("%d-%m-%Y")
            params["to_date"] = to_date.strftime("%d-%m-%Y")
        referer = "/companies-listing/corporate-integrated-filing"
        return self._get_json("/api/integrated-filing-results", params=params, referer=referer)

    def annual_reports(self, *, symbol: str | None = None, index: str = "equities") -> Any:
        params: dict[str, Any] = {"index": index}
        if symbol:
            params["symbol"] = symbol
        referer = "/companies-listing/corporate-filings-annual-reports"
        return self._get_json("/api/annual-reports", params=params, referer=referer)

    def announcement_xbrl(
        self,
        *,
        symbol: str | None = None,
        index: str = "equities",
        from_date: date | None = None,
        to_date: date | None = None,
        page: int = 1,
        size: int = 50,
    ) -> Any:
        params: dict[str, Any] = {"index": index, "page": page, "size": size}
        if symbol:
            params["symbol"] = symbol
        if from_date or to_date:
            if not (from_date and to_date):
                raise ValueError("from_date and to_date must be provided together")
            params["from_date"] = from_date.strftime("%d-%m-%Y")
            params["to_date"] = to_date.strftime("%d-%m-%Y")
        referer = "/companies-listing/corporate-filings-announcements-xbrl"
        return self._get_json("/api/corporates-announcements-xbrl", params=params, referer=referer)

    def secretarial_compliance(
        self,
        *,
        symbol: str | None = None,
        index: str = "equities",
        page: int = 1,
        size: int = 50,
    ) -> Any:
        params: dict[str, Any] = {"index": index, "page": page, "size": size}
        if symbol:
            params["symbol"] = symbol
        referer = "/companies-listing/corporate-filings-secretarial-compliance-report"
        return self._get_json("/api/corporate-secretarial-compliance", params=params, referer=referer)

    def download(self, url: str) -> tuple[bytes, dict[str, Any]]:
        response = self._get_bytes(url)
        body = response.content
        headers = {k.lower(): v for k, v in response.headers.items()}
        return body, {
            "url": str(response.url),
            "status_code": response.status_code,
            "content_type": headers.get("content-type"),
            "content_disposition": headers.get("content-disposition"),
            "sha256": sha256(body).hexdigest(),
            "byte_size": len(body),
        }

    @staticmethod
    def asset_from_url(
        url: str,
        *,
        title: str | None = None,
        filing_id: str | None = None,
        instrument: Instrument | None = None,
        instrument_id: str | None = None,
        retrieved_at: datetime | None = None,
        mime_type: str | None = None,
    ) -> DocumentAsset:
        now = retrieved_at or datetime.now(timezone.utc)
        clean = url.strip()
        suffix = clean.lower().split("?", 1)[0].rsplit(".", 1)[-1] if "." in clean.rsplit("/", 1)[-1] else ""
        mapping = {
            "pdf": "pdf", "xml": "xbrl_xml", "xbrl": "xbrl_xml",
            "xlsx": "xlsx", "xls": "xlsx", "csv": "csv",
            "zip": "zip", "html": "html", "htm": "html", "txt": "text",
        }
        kind = mapping.get(suffix, "unknown")
        asset_id = sha256(clean.encode("utf-8")).hexdigest()
        return DocumentAsset(
            asset_id=f"nse:{asset_id}",
            filing_id=filing_id,
            instrument_id=instrument.instrument_id if instrument else instrument_id,
            document_type=kind,
            title=title,
            url=clean,
            mime_type=mime_type,
            provenance=Provenance(
                source="nse",
                source_type="primary_exchange",
                source_dataset="filing_asset",
                source_url=clean,
                retrieved_at=now,
            ),
        )
