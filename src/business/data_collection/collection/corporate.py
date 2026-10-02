from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Iterable, Any
import hashlib

from data_collection.collection.results import CollectionResult, RawPayload
from data_collection.domains.models import CorporateAction, Instrument, Provenance
from data_collection.domains.events import CompanyEvent
from data_collection.providers.nse_archives import NSEArchivesProvider
from data_collection.providers.upstox import UpstoxProvider


class CorporateActionCollector:
    """Collect corporate actions from Upstox and/or NSE archive data."""

    domain = "corporate_actions"

    def __init__(self, *, upstox: UpstoxProvider | None = None, nse: NSEArchivesProvider | None = None):
        self.upstox = upstox
        self.nse = nse

    def for_instrument(self, instrument: Instrument) -> CollectionResult[CorporateAction]:
        result: CollectionResult[CorporateAction] = CollectionResult(domain=self.domain)
        if not instrument.isin:
            result.errors.append({"source": "upstox", "error": "ISIN is required for Upstox corporate actions"})
            return result
        if self.upstox is None:
            result.errors.append({"source": "upstox", "error": "provider is not configured"})
            return result
        now = datetime.now(timezone.utc)
        try:
            payload = self.upstox.corporate_actions(instrument.isin)
            result.raw_payloads.append(RawPayload(
                source="upstox", domain=self.domain, retrieved_at=now,
                payload=payload, request={"isin": instrument.isin, "endpoint": "corporate-actions"},
            ))
            result.records.extend(self.upstox.parse_corporate_actions(payload, instrument.instrument_id, retrieved_at=now))
        except Exception as exc:
            result.errors.append({"source": "upstox", "endpoint": "corporate-actions", "error": str(exc)})
        return result

    def for_dates(self, start: date, end: date | None = None, *, symbol: str | None = None, instrument: Instrument | None = None) -> CollectionResult[CorporateAction]:
        result: CollectionResult[CorporateAction] = CollectionResult(domain=self.domain)
        if self.nse is None:
            result.errors.append({"source": "nse", "error": "provider is not configured"})
            return result
        end = end or start
        for trading_date in _date_range(start, end):
            now = datetime.now(timezone.utc)
            try:
                payload = self.nse.corporate_actions(trading_date)
                result.raw_payloads.append(RawPayload(
                    source="nse", domain=self.domain, retrieved_at=now,
                    payload=_jsonable_frame(payload),
                    request={"dataset": "corp_actions", "trading_date": str(trading_date)},
                ))
                result.records.extend(_normalize_nse_corporate_actions(
                    payload, instrument=instrument, symbol=symbol,
                    retrieved_at=now, trading_date=trading_date,
                ))
            except Exception as exc:
                result.errors.append({"source": "nse", "dataset": "corp_actions", "trading_date": str(trading_date), "error": str(exc)})
        return result


class CompanyEventCollector:
    """Collect NSE announcements and board-meeting records as canonical events."""

    domain = "company_events"

    def __init__(self, *, nse: NSEArchivesProvider | None = None):
        self.nse = nse

    def announcements(self, start: date, end: date | None = None, *, symbol: str | None = None, instrument: Instrument | None = None) -> CollectionResult[CompanyEvent]:
        return self._daily("announcements", self.nse.announcements if self.nse else None, start, end, symbol=symbol, instrument=instrument)

    def board_meetings(self, start: date, end: date | None = None, *, symbol: str | None = None, instrument: Instrument | None = None) -> CollectionResult[CompanyEvent]:
        return self._daily("board_meetings", self.nse.board_meetings if self.nse else None, start, end, symbol=symbol, instrument=instrument)

    def _daily(self, dataset: str, loader, start: date, end: date | None, *, symbol: str | None, instrument: Instrument | None) -> CollectionResult[CompanyEvent]:
        result: CollectionResult[CompanyEvent] = CollectionResult(domain=self.domain)
        if loader is None:
            result.errors.append({"source": "nse", "error": "provider is not configured"})
            return result
        end = end or start
        for trading_date in _date_range(start, end):
            now = datetime.now(timezone.utc)
            try:
                frame = loader(trading_date)
                result.raw_payloads.append(RawPayload(
                    source="nse", domain=self.domain, retrieved_at=now,
                    payload=_jsonable_frame(frame),
                    request={"dataset": dataset, "trading_date": str(trading_date)},
                ))
                result.records.extend(_normalize_nse_events(
                    frame, event_type="announcement" if dataset == "announcements" else "board_meeting",
                    instrument=instrument, symbol=symbol, retrieved_at=now,
                    observed_date=trading_date,
                ))
            except Exception as exc:
                result.errors.append({"source": "nse", "dataset": dataset, "trading_date": str(trading_date), "error": str(exc)})
        return result


def _date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _jsonable_frame(frame: Any):
    if hasattr(frame, "where"):
        frame = frame.where(frame.notna(), None)
    if hasattr(frame, "to_dict"):
        return frame.to_dict(orient="records")
    return frame


def _lookup_columns(frame, names: Iterable[str]):
    aliases = {str(c).strip().upper(): c for c in frame.columns}
    for name in names:
        if name.upper() in aliases:
            return aliases[name.upper()]
    return None


def _cell(row, col):
    if col is None:
        return None
    value = row[col]
    try:
        import pandas as pd
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def _normalize_nse_corporate_actions(frame, *, instrument: Instrument | None, symbol: str | None, retrieved_at: datetime, trading_date: date) -> list[CorporateAction]:
    if frame is None or getattr(frame, "empty", False):
        return []
    symbol_col = _lookup_columns(frame, ("SYMBOL", "SYMBOL_NAME", "SECURITY_SYMBOL"))
    purpose_col = _lookup_columns(frame, ("PURPOSE", "ACTION", "CORPORATE_ACTION"))
    series_col = _lookup_columns(frame, ("SERIES",))
    company_col = _lookup_columns(frame, ("COMPANY NAME", "COMPANY_NAME", "SECURITY_NAME"))
    ex_col = _lookup_columns(frame, ("EX-DATE", "EX DATE", "EX_DATE"))
    record_col = _lookup_columns(frame, ("RECORD DATE", "RECORD_DATE"))
    book_start_col = _lookup_columns(frame, ("BOOK CLOSURE START DATE", "BOOK_CLOSURE_START_DATE"))
    book_end_col = _lookup_columns(frame, ("BOOK CLOSURE END DATE", "BOOK_CLOSURE_END_DATE"))
    face_col = _lookup_columns(frame, ("FACE VALUE", "FACE_VALUE"))
    out: list[CorporateAction] = []
    for _, row in frame.iterrows():
        raw_symbol = str(_cell(row, symbol_col) or "").strip()
        if symbol and raw_symbol.upper() != symbol.upper():
            continue
        action = str(_cell(row, purpose_col) or "unknown").strip()
        action_type = action.lower().replace(" ", "_").replace("/", "_")
        details = {str(c): _cell(row, c) for c in frame.columns}
        instrument_id = instrument.instrument_id if instrument else (raw_symbol or "UNKNOWN")
        key_material = f"nse|{instrument_id}|{trading_date}|{raw_symbol}|{action}|{details}"
        out.append(CorporateAction(
            instrument_id=instrument_id,
            action_type=action_type,
            announcement_date=trading_date,
            ex_date=_parse_date(_cell(row, ex_col)),
            record_date=_parse_date(_cell(row, record_col)),
            details=details,
            provenance=Provenance(
                source="nse", source_type="primary_exchange", source_dataset="corp_actions",
                retrieved_at=retrieved_at, published_at=datetime.combine(trading_date, datetime.min.time(), tzinfo=timezone.utc),
            ),
            face_value=str(_cell(row, face_col)) if face_col else None,
            company_name=str(_cell(row, company_col)) if company_col else None,
            series=str(_cell(row, series_col)) if series_col else None,
            book_closure_start=_parse_date(_cell(row, book_start_col)),
            book_closure_end=_parse_date(_cell(row, book_end_col)),
        ))
    return out


def _normalize_nse_events(frame, *, event_type: str, instrument: Instrument | None, symbol: str | None, retrieved_at: datetime, observed_date: date) -> list[CompanyEvent]:
    if frame is None or getattr(frame, "empty", False):
        return []
    symbol_col = _lookup_columns(frame, ("SYMBOL", "SYMBOL_NAME", "SECURITY_SYMBOL"))
    subject_col = _lookup_columns(frame, ("SUBJECT", "PURPOSE", "DESCRIPTION", "TITLE"))
    details_col = _lookup_columns(frame, ("DETAILS", "DESCRIPTION", "TEXT", "REMARKS"))
    company_col = _lookup_columns(frame, ("COMPANY NAME", "COMPANY_NAME", "SECURITY_NAME"))
    url_col = _lookup_columns(frame, ("URL", "ATTACHMENT", "FILE", "LINK"))
    out: list[CompanyEvent] = []
    for _, row in frame.iterrows():
        raw_symbol = str(_cell(row, symbol_col) or "").strip()
        if symbol and raw_symbol.upper() != symbol.upper():
            continue
        instrument_id = instrument.instrument_id if instrument else (raw_symbol or None)
        subject = str(_cell(row, subject_col) or "").strip() or None
        description = str(_cell(row, details_col) or "").strip() or None
        details = {str(c): _cell(row, c) for c in frame.columns}
        key = f"{event_type}|{instrument_id}|{observed_date}|{raw_symbol}|{subject}|{description}"
        event_id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        url = str(_cell(row, url_col)) if url_col and _cell(row, url_col) else None
        out.append(CompanyEvent(
            event_id=event_id,
            instrument_id=instrument_id,
            event_type=event_type,
            subject=subject,
            event_date=observed_date,
            announcement_date=observed_date,
            description=description,
            url=url,
            details={**details, "company_name": _cell(row, company_col)},
            provenance=Provenance(
                source="nse", source_type="primary_exchange", source_dataset=event_type,
                retrieved_at=retrieved_at, published_at=datetime.combine(observed_date, datetime.min.time(), tzinfo=timezone.utc),
            ),
        ))
    return out


def _parse_date(value):
    if value is None or value == "" or str(value).strip() in {"-", "nan", "NaT"}:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    from dateutil.parser import parse
    try:
        return parse(str(value), dayfirst=True).date()
    except Exception:
        return None
