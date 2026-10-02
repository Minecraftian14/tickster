from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
from urllib.parse import urljoin
from typing import Any, Iterable

import httpx
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date


SEBI_BASE = "https://www.sebi.gov.in"


@dataclass(frozen=True)
class SEBIListingSpec:
    name: str
    path: str
    source_type: str = "regulator"


LISTINGS: dict[str, SEBIListingSpec] = {
    "legal": SEBIListingSpec("legal", "/sebiweb/home/HomeAction.do?doListing=yes&sid=1"),
    "regulations": SEBIListingSpec("regulations", "/sebiweb/home/HomeAction.do?doListingLegal=yes&sid=1&ssid=3"),
    "circulars": SEBIListingSpec("circulars", "/sebiweb/home/HomeAction.do?doListing=yes&sid=1&smid=&ssid=7"),
    "master_circulars": SEBIListingSpec("master_circulars", "/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=6"),
    "informal_guidance": SEBIListingSpec("informal_guidance", "/sebiweb/home/HomeAction.do?doListing=yes&sid=2&smid=0&ssid=10"),
    "orders": SEBIListingSpec("orders", "/sebiweb/home/HomeAction.do?doListing=yes&sid=2&ssid=9"),
    "press_releases": SEBIListingSpec("press_releases", "/sebiweb/home/HomeAction.do?doListing=yes&sid=6&ssid=23"),
    "news_listing": SEBIListingSpec("news_listing", "/sebiweb/home/HomeAction.do?doListingAll=yes&search=Listing"),
}


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, "", "-", "None"):
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = parse_date(str(value), dayfirst=True, fuzzy=True)
        except Exception:
            return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _clean_text(value: str | None) -> str | None:
    if not value:
        return None
    text = " ".join(value.split())
    return text or None


def _is_date_text(text: str) -> bool:
    try:
        parse_date(text, dayfirst=True, fuzzy=True)
        return any(ch.isdigit() for ch in text)
    except Exception:
        return False


def _record_rows(soup: BeautifulSoup) -> list[Any]:
    rows = []
    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        anchors = row.find_all("a", href=True)
        if anchors:
            rows.append(row)
    return rows


def parse_listing_html(html: str | bytes, *, category: str, page_url: str) -> list[dict[str, Any]]:
    """Parse current SEBI listing pages into loss-minimizing records.

    The parser deliberately keeps the rendered row text and every link found in
    the row. SEBI's older listing pages have slightly different table columns by
    category, so the output is intentionally schema-light.
    """

    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []
    for row in _record_rows(soup):
        cells = [" ".join(c.stripped_strings) for c in row.find_all(["td", "th"])]
        anchors = row.find_all("a", href=True)
        if not anchors:
            continue

        title_anchor = None
        for anchor in anchors:
            text = _clean_text(anchor.get_text(" ", strip=True))
            if text and text not in {"1", "2", "3", "4", "5", "6", "Next", "Last", "Previous"}:
                title_anchor = anchor
                break
        if title_anchor is None:
            continue

        title = _clean_text(title_anchor.get_text(" ", strip=True)) or ""
        detail_url = urljoin(page_url, title_anchor.get("href"))

        published_at = None
        date_text = None
        for cell in cells[:2]:
            if _is_date_text(cell):
                date_text = cell
                published_at = _parse_datetime(cell)
                break

        links = [urljoin(page_url, a.get("href")) for a in anchors if a.get("href")]
        record = {
            "category": category,
            "title": title,
            "published_at": published_at,
            "date_text": date_text,
            "detail_url": detail_url,
            "links": list(dict.fromkeys(links)),
            "cells": cells,
        }
        # Press-release pages have an explicit PR number; preserve it when the
        # listing exposes one in the row text.
        if len(cells) >= 2 and cells[0] and "/" in cells[1]:
            record["reference_number"] = cells[1]
        records.append(record)
    return records


def next_page_url(html: str | bytes, *, page_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for anchor in soup.find_all("a", href=True):
        text = _clean_text(anchor.get_text(" ", strip=True))
        if text and text.lower() in {"next", "next ›", "next >", "next "}:
            return urljoin(page_url, anchor.get("href"))
    return None


def parse_detail_html(html: str | bytes, *, detail_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    title = None
    h1 = soup.find("h1")
    if h1:
        title = _clean_text(h1.get_text(" ", strip=True))
    if not title:
        title = _clean_text(soup.title.get_text(" ", strip=True)) if soup.title else None

    links = []
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")
        text = _clean_text(anchor.get_text(" ", strip=True))
        if not href:
            continue
        absolute = urljoin(detail_url, href)
        suffix = absolute.lower().split("?", 1)[0]
        if any(token in suffix for token in (".pdf", ".xml", ".xlsx", ".xls", ".zip", ".csv")):
            links.append({"url": absolute, "text": text})

    return {
        "title": title,
        "detail_url": detail_url,
        "document_links": list({item["url"]: item for item in links}.values()),
        "text": " ".join(soup.stripped_strings),
    }


class SEBIProvider:
    name = "sebi"

    def __init__(self, *, base_url: str = SEBI_BASE, timeout: float = 20.0, client: httpx.Client | None = None):
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": "IndianEquityDataPlatform/0.10"})
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def health(self) -> dict[str, Any]:
        return {"provider": self.name, "configured": True, "base_url": self.base_url}

    def listing_html(self, category: str, *, page_url: str | None = None) -> tuple[str, dict[str, Any]]:
        spec = LISTINGS[category]
        url = page_url or urljoin(self.base_url, spec.path)
        response = self.client.get(url)
        response.raise_for_status()
        return response.text, {
            "url": str(response.url),
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
        }

    def listing(self, category: str, *, max_pages: int = 1) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if category not in LISTINGS:
            raise KeyError(f"Unknown SEBI listing category: {category}")
        records: list[dict[str, Any]] = []
        requests: list[dict[str, Any]] = []
        current_url: str | None = None
        seen_pages: set[str] = set()
        for _ in range(max_pages):
            html, meta = self.listing_html(category, page_url=current_url)
            page_url = meta["url"]
            if page_url in seen_pages:
                break
            seen_pages.add(page_url)
            records.extend(parse_listing_html(html, category=category, page_url=page_url))
            requests.append(meta)
            current_url = next_page_url(html, page_url=page_url)
            if not current_url:
                break
        return records, requests

    def detail(self, detail_url: str) -> tuple[dict[str, Any], dict[str, Any]]:
        response = self.client.get(detail_url)
        response.raise_for_status()
        return parse_detail_html(response.text, detail_url=str(response.url)), {
            "url": str(response.url),
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
        }

    def download(self, url: str) -> tuple[bytes, dict[str, Any]]:
        response = self.client.get(url)
        response.raise_for_status()
        body = response.content
        return body, {
            "url": str(response.url),
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "sha256": sha256(body).hexdigest(),
            "byte_size": len(body),
        }
