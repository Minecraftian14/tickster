from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
import mimetypes
import re

from data_collection.collection.results import CollectionResult, RawPayload
from data_collection.domains.filings import DocumentAsset, Filing
from data_collection.domains.models import Instrument, Provenance
from data_collection.providers.nse_filings import NSEFilingsProvider


def _records_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "results", "records", "Table", "table", "rows", "filings"):
        value = payload.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    # Some endpoints wrap the actual list one level deeper.
    for value in payload.values():
        if isinstance(value, list) and (not value or isinstance(value[0], dict)):
            return value
        if isinstance(value, dict):
            nested = _records_from_payload(value)
            if nested:
                return nested
    return []


def _first(row: dict[str, Any], *names: str) -> Any:
    normalized = {re.sub(r"[^a-z0-9]+", "", str(k).lower()): k for k in row}
    for name in names:
        key = normalized.get(re.sub(r"[^a-z0-9]+", "", name.lower()))
        if key is not None:
            return row[key]
    return None


def _date(value: Any) -> date | None:
    if value in (None, "", "-", "None", "nan", "NaT"):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    from dateutil.parser import parse
    try:
        return parse(str(value), dayfirst=True, fuzzy=True).date()
    except Exception:
        return None


def _datetime(value: Any) -> datetime | None:
    if value in (None, "", "-", "None", "nan", "NaT"):
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        from dateutil.parser import parse
        try:
            parsed = parse(str(value), dayfirst=True, fuzzy=True)
        except Exception:
            return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _bool(value: Any) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"audited", "yes", "true", "y", "1"}:
        return True
    if text in {"unaudited", "no", "false", "n", "0"}:
        return False
    return None


def _absolute_url(url: str | None) -> str | None:
    if not url:
        return None
    return str(url)


def _asset_candidates(row: dict[str, Any]) -> list[tuple[str, str | None]]:
    candidates: list[tuple[str, str | None]] = []
    for key, value in row.items():
        if value is None:
            continue
        if not isinstance(value, str):
            continue
        value = value.strip()
        if not value:
            continue
        key_l = str(key).lower()
        # Avoid treating every URL field as a document. Links named after
        # attachments/XBRL/details are strong indicators.
        if "xbrl" in key_l or "attach" in key_l or "detail" in key_l or "file" in key_l or "document" in key_l:
            if value.startswith(("http://", "https://", "/")):
                candidates.append((value, str(key)))
    # Also catch explicit URLs nested in a free-text details field.
    for value in row.values():
        if isinstance(value, str):
            for match in re.findall(r'https?://[^\s<>"]+', value):
                if any(ext in match.lower() for ext in (".pdf", ".xml", ".xlsx", ".zip")):
                    candidates.append((match.rstrip(".,);]"), None))
    seen: set[str] = set()
    result: list[tuple[str, str | None]] = []
    for url, label in candidates:
        if url not in seen:
            seen.add(url)
            result.append((url, label))
    return result


def _filing_id(row: dict[str, Any], category: str) -> str:
    symbol = str(_first(row, "symbol", "sm_symbol", "nse_symbol") or "").upper()
    period = str(_first(row, "toDate", "to_date", "quarterEndDate", "quarter_end_date", "fromYear", "from_year") or "")
    published = str(_first(row, "filingDate", "filing_date", "broadcastDateTime", "broadcast_date_time", "sort_date") or "")
    urls = "|".join(url for url, _ in _asset_candidates(row))
    digest = sha256(f"nse|{category}|{symbol}|{period}|{published}|{urls}|{sorted(row.items())}".encode("utf-8")).hexdigest()
    return f"nse:{category}:{digest[:32]}"


def _normalize_filing(
    row: dict[str, Any],
    *,
    category: str,
    instrument: Instrument | None,
    symbol: str | None,
    retrieved_at: datetime,
    assets: list[DocumentAsset],
    filing_id: str | None = None,
) -> Filing:
    raw_symbol = str(_first(row, "symbol", "sm_symbol", "nse_symbol") or symbol or "").strip().upper() or None
    instrument_id = instrument.instrument_id if instrument else (f"NSE:{raw_symbol}" if raw_symbol else None)
    filing_type = str(
        _first(row, "filingType", "filing_type", "type", "desc", "subject", "purpose", "reportType")
        or category
    ).strip()
    period_end = _date(_first(row, "toDate", "to_date", "quarterEndDate", "quarter_end_date", "periodEndDate", "period_end"))
    period_start = _date(_first(row, "fromDate", "from_date", "periodStartDate", "period_start"))
    published_at = _datetime(_first(row, "an_dt", "announcementDateTime", "announcement_datetime", "broadcastDateTime", "broadcast_date_time", "filingDate", "filing_date", "sort_date", "submissionDate", "submission_date"))
    received_at = _datetime(_first(row, "exchangeReceivedTime", "exchange_received_time", "receivedTime", "received_time"))
    revised_at = _datetime(_first(row, "revisedDateTime", "revised_date_time", "revisedDate", "revised_date"))
    statement_type = _first(row, "consolidated", "consolidatedStandalone", "statementType", "statement_type")
    audited = _bool(_first(row, "audited", "auditedUnaudited", "auditStatus"))
    title = str(_first(row, "title", "subject", "attchmntText", "desc", "reportType", "type") or filing_type)
    subcategory = _first(row, "desc", "subject", "reportType", "type")

    details_url = _first(row, "details", "detailsUrl", "details_url", "detailUrl", "link")
    if isinstance(details_url, str) and not details_url.startswith(("http://", "https://")):
        details_url = None

    filing_id = filing_id or _filing_id(row, category)
    filing_assets = [a.asset_id for a in assets]
    return Filing(
        filing_id=filing_id,
        instrument_id=instrument_id,
        symbol=raw_symbol,
        company_name=_first(row, "companyName", "company_name", "sm_name", "issuer"),
        filing_type=filing_type,
        category=category,
        subcategory=str(subcategory) if subcategory is not None else None,
        period_start=period_start,
        period_end=period_end,
        financial_year=_first(row, "financialYear", "financial_year", "fromYear", "from_year"),
        statement_type=str(statement_type) if statement_type is not None else None,
        submission_type=str(_first(row, "typeOfSubmission", "type_of_submission", "submissionType", "submission_type") or "") or None,
        audited=audited,
        published_at=published_at,
        received_at=received_at,
        revised_at=revised_at,
        revision_remarks=_first(row, "revisionRemarks", "revision_remarks"),
        details_url=details_url,
        assets=filing_assets,
        metadata={"raw": row, "asset_count": len(assets), "title": title},
        provenance=Provenance(
            source="nse",
            source_type="primary_exchange",
            source_dataset=category,
            source_url=f"https://www.nseindia.com/companies-listing/{category}",
            retrieved_at=retrieved_at,
            published_at=published_at,
        ),
    )


class FilingCollector:
    """Collect filing catalogs and their referenced document assets from NSE."""

    domain = "filings"

    def __init__(self, *, nse: NSEFilingsProvider | None = None):
        self.nse = nse

    def _collect_payload(
        self,
        category: str,
        payload: Any,
        *,
        instrument: Instrument | None,
        symbol: str | None,
        request: dict[str, Any],
    ) -> CollectionResult[Filing]:
        result: CollectionResult[Filing] = CollectionResult(domain=self.domain)
        now = datetime.now(timezone.utc)
        result.raw_payloads.append(RawPayload(
            source="nse", domain=self.domain, retrieved_at=now, payload=payload, request=request
        ))
        for row in _records_from_payload(payload):
            filing_id = _filing_id(row, category)
            assets: list[DocumentAsset] = []
            for url, label in _asset_candidates(row):
                assets.append(NSEFilingsProvider.asset_from_url(
                    url,
                    title=label,
                    filing_id=filing_id,
                    instrument=instrument,
                    retrieved_at=now,
                ))
            result.related_records.extend(assets)
            result.records.append(_normalize_filing(
                row,
                category=category,
                instrument=instrument,
                symbol=symbol,
                retrieved_at=now,
                assets=assets,
                filing_id=filing_id,
            ))
        return result

    def corporate_announcements(
        self,
        *,
        symbol: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        subject: str | None = None,
        instrument: Instrument | None = None,
    ) -> CollectionResult[Filing]:
        result = CollectionResult[Filing](domain=self.domain)
        if self.nse is None:
            result.errors.append({"source": "nse", "error": "provider is not configured"})
            return result
        try:
            payload = self.nse.corporate_announcements(
                symbol=symbol, from_date=from_date, to_date=to_date, subject=subject
            )
            return self._collect_payload(
                "corporate_announcements", payload, instrument=instrument, symbol=symbol,
                request={
                    "endpoint": "corporate-announcements", "symbol": symbol,
                    "from_date": from_date.isoformat() if from_date else None,
                    "to_date": to_date.isoformat() if to_date else None,
                    "subject": subject,
                },
            )
        except Exception as exc:
            result.errors.append({"source": "nse", "endpoint": "corporate-announcements", "symbol": symbol, "error": str(exc)})
            return result

    def financial_results(
        self,
        *,
        symbol: str | None = None,
        period: str = "Quarterly",
        instrument: Instrument | None = None,
    ) -> CollectionResult[Filing]:
        result = CollectionResult[Filing](domain=self.domain)
        if self.nse is None:
            result.errors.append({"source": "nse", "error": "provider is not configured"})
            return result
        try:
            payload = self.nse.financial_results(symbol=symbol, period=period)
            return self._collect_payload(
                "financial_results_legacy", payload, instrument=instrument, symbol=symbol,
                request={"endpoint": "corporates-financial-results", "symbol": symbol, "period": period},
            )
        except Exception as exc:
            result.errors.append({"source": "nse", "endpoint": "corporates-financial-results", "error": str(exc)})
            return result

    def integrated_financials(
        self,
        *,
        symbol: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        instrument: Instrument | None = None,
        page: int = 1,
        size: int = 50,
    ) -> CollectionResult[Filing]:
        result = CollectionResult[Filing](domain=self.domain)
        if self.nse is None:
            result.errors.append({"source": "nse", "error": "provider is not configured"})
            return result
        try:
            payload = self.nse.integrated_filing_results(
                symbol=symbol, from_date=from_date, to_date=to_date,
                page=page, size=size,
            )
            return self._collect_payload(
                "integrated_filing_financials", payload, instrument=instrument, symbol=symbol,
                request={"endpoint": "integrated-filing-results", "symbol": symbol, "page": page, "size": size},
            )
        except Exception as exc:
            result.errors.append({"source": "nse", "endpoint": "integrated-filing-results", "error": str(exc)})
            return result

    def annual_reports(
        self,
        *,
        symbol: str | None = None,
        instrument: Instrument | None = None,
    ) -> CollectionResult[Filing]:
        result = CollectionResult[Filing](domain=self.domain)
        if self.nse is None:
            result.errors.append({"source": "nse", "error": "provider is not configured"})
            return result
        try:
            payload = self.nse.annual_reports(symbol=symbol)
            return self._collect_payload(
                "annual_reports", payload, instrument=instrument, symbol=symbol,
                request={"endpoint": "annual-reports", "symbol": symbol},
            )
        except Exception as exc:
            result.errors.append({"source": "nse", "endpoint": "annual-reports", "error": str(exc)})
            return result

    def announcement_xbrl(
        self,
        *,
        symbol: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        instrument: Instrument | None = None,
        page: int = 1,
        size: int = 50,
    ) -> CollectionResult[Filing]:
        result = CollectionResult[Filing](domain=self.domain)
        if self.nse is None:
            result.errors.append({"source": "nse", "error": "provider is not configured"})
            return result
        try:
            payload = self.nse.announcement_xbrl(
                symbol=symbol, from_date=from_date, to_date=to_date,
                page=page, size=size,
            )
            return self._collect_payload(
                "announcement_xbrl", payload, instrument=instrument, symbol=symbol,
                request={"endpoint": "corporates-announcements-xbrl", "symbol": symbol},
            )
        except Exception as exc:
            result.errors.append({"source": "nse", "endpoint": "corporates-announcements-xbrl", "error": str(exc)})
            return result

    def secretarial_compliance(
        self,
        *,
        symbol: str | None = None,
        instrument: Instrument | None = None,
        page: int = 1,
        size: int = 50,
    ) -> CollectionResult[Filing]:
        result = CollectionResult[Filing](domain=self.domain)
        if self.nse is None:
            result.errors.append({"source": "nse", "error": "provider is not configured"})
            return result
        try:
            payload = self.nse.secretarial_compliance(symbol=symbol, page=page, size=size)
            return self._collect_payload(
                "secretarial_compliance", payload, instrument=instrument, symbol=symbol,
                request={"endpoint": "corporate-secretarial-compliance", "symbol": symbol},
            )
        except Exception as exc:
            result.errors.append({"source": "nse", "endpoint": "corporate-secretarial-compliance", "error": str(exc)})
            return result

    def download_assets(
        self,
        filings: Iterable[Filing],
        *,
        root: str | Path,
    ) -> list[DocumentAsset]:
        """Download all referenced assets into a content-addressable local tree."""
        if self.nse is None:
            raise RuntimeError("NSE filing provider is not configured")
        root = Path(root)
        output: list[DocumentAsset] = []
        for filing in filings:
            # Filing objects store asset IDs; caller can reconstruct asset URLs
            # from the corresponding metadata for now. This helper is intentionally
            # conservative and expects provider assets to be supplied separately.
            raw_rows = [filing.metadata.get("raw", {})]
            urls: list[str] = []
            for row in raw_rows:
                urls.extend([url for url, _ in _asset_candidates(row)])
            for url in dict.fromkeys(urls):
                body, info = self.nse.download(url)
                suffix = mimetypes.guess_extension(info.get("content_type", "").split(";", 1)[0]) or Path(url.split("?", 1)[0]).suffix or ".bin"
                digest = info["sha256"]
                target = root / digest[:2] / digest[2:4] / f"{digest}{suffix}"
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    target.write_bytes(body)
                asset = NSEFilingsProvider.asset_from_url(
                    url,
                    filing_id=filing.filing_id,
                    instrument_id=filing.instrument_id,
                    retrieved_at=datetime.now(timezone.utc),
                    mime_type=info.get("content_type"),
                )
                # Pydantic copy to avoid coupling this helper to URL parser internals.
                asset.byte_size = info["byte_size"]
                asset.sha256 = digest
                asset.local_path = str(target)
                output.append(asset)
        return output
