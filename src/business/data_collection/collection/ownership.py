from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
from typing import Any, Iterable

from data_collection.collection.results import CollectionResult, RawPayload
from data_collection.domains.models import Instrument, Provenance, ShareholdingSnapshot
from data_collection.domains.ownership import InsiderTransaction, LargeDeal
from data_collection.providers.nse_public import NSEPublicProvider
from data_collection.providers.nse_archives import NSEArchivesProvider


class OwnershipCollector:
    """Collect shareholding and insider disclosures from NSE."""

    shareholding_domain = "shareholding"
    insider_domain = "insider_transactions"

    def __init__(self, *, nse: NSEPublicProvider | None = None):
        self.nse = nse

    def shareholding(self, symbol: str, *, instrument: Instrument | None = None) -> CollectionResult[ShareholdingSnapshot]:
        result: CollectionResult[ShareholdingSnapshot] = CollectionResult(domain=self.shareholding_domain)
        if self.nse is None:
            result.errors.append({"source": "nse", "error": "provider is not configured"})
            return result
        now = datetime.now(timezone.utc)
        try:
            payload = self.nse.shareholding(symbol)
            result.raw_payloads.append(RawPayload(
                source="nse", domain=self.shareholding_domain, retrieved_at=now,
                payload=payload, request={"endpoint": "corporate-share-holdings-master", "symbol": symbol},
            ))
            result.records.extend(parse_shareholding(payload, instrument=instrument, symbol=symbol, retrieved_at=now))
        except Exception as exc:
            result.errors.append({"source": "nse", "endpoint": "corporate-share-holdings-master", "symbol": symbol, "error": str(exc)})
        return result

    def insider_transactions(
        self, start: date, end: date | None = None, *, symbol: str | None = None,
        instrument: Instrument | None = None,
    ) -> CollectionResult[InsiderTransaction]:
        result: CollectionResult[InsiderTransaction] = CollectionResult(domain=self.insider_domain)
        if self.nse is None:
            result.errors.append({"source": "nse", "error": "provider is not configured"})
            return result
        end = end or start
        now = datetime.now(timezone.utc)
        try:
            payload = self.nse.insider_trading(start, end, symbol=symbol)
            result.raw_payloads.append(RawPayload(
                source="nse", domain=self.insider_domain, retrieved_at=now,
                payload=payload, request={
                    "endpoint": "corporates-pit", "symbol": symbol,
                    "from_date": start.isoformat(), "to_date": end.isoformat(),
                },
            ))
            result.records.extend(parse_insider_transactions(payload, instrument=instrument, symbol=symbol, retrieved_at=now))
        except Exception as exc:
            result.errors.append({"source": "nse", "endpoint": "corporates-pit", "symbol": symbol, "error": str(exc)})
        return result


class MarketEventsCollector:
    """Collect NSE large-deal disclosures (bulk/block/short selling)."""

    domain = "market_events"

    def __init__(self, *, nse: NSEPublicProvider | None = None, nse_archives: NSEArchivesProvider | None = None):
        self.nse = nse
        self.nse_archives = nse_archives

    def large_deals(self, mode: str = "bulk_deals", *, symbol: str | None = None) -> CollectionResult[LargeDeal]:
        result: CollectionResult[LargeDeal] = CollectionResult(domain=self.domain)
        if self.nse is not None:
            now = datetime.now(timezone.utc)
            try:
                payload = self.nse.large_deals(mode)
                result.raw_payloads.append(RawPayload(
                    source="nse", domain=self.domain, retrieved_at=now,
                    payload=payload, request={"endpoint": "snapshot-capital-market-largedeal", "mode": mode},
                ))
                result.records.extend(parse_large_deals(payload, mode=mode, symbol=symbol, retrieved_at=now))
                return result
            except Exception as exc:
                result.errors.append({"source": "nse", "endpoint": "snapshot-capital-market-largedeal", "mode": mode, "error": str(exc)})
        if self.nse_archives is None:
            result.errors.append({"source": "nse", "error": "no configured provider for large deals"})
            return result
        # Archive provider requires an explicit date; keep this path available
        # for callers that want authoritative historical report downloads.
        result.errors.append({"source": "nse_archives", "error": "use archive_daily() for dated bulk/block/short reports"})
        return result

    def archive_daily(self, trading_date: date, mode: str = "bulk_deals", *, symbol: str | None = None) -> CollectionResult[LargeDeal]:
        result: CollectionResult[LargeDeal] = CollectionResult(domain=self.domain)
        if self.nse_archives is None:
            result.errors.append({"source": "nse_archives", "error": "provider is not configured"})
            return result
        now = datetime.now(timezone.utc)
        try:
            if mode == "bulk_deals":
                frame = self.nse_archives.bulk_deals(trading_date)
            elif mode == "block_deals":
                frame = self.nse_archives.block_deals(trading_date)
            elif mode == "short_deals":
                frame = self.nse_archives.short_selling(trading_date)
            else:
                raise ValueError("mode must be bulk_deals, block_deals, or short_deals")
            payload = frame.where(frame.notna(), None).to_dict(orient="records")
            result.raw_payloads.append(RawPayload(
                source="nse", domain=self.domain, retrieved_at=now,
                payload=payload, request={"dataset": mode, "trading_date": trading_date.isoformat()},
            ))
            result.records.extend(parse_large_deal_rows(payload, mode=mode, symbol=symbol, retrieved_at=now))
        except Exception as exc:
            result.errors.append({"source": "nse_archives", "dataset": mode, "trading_date": trading_date.isoformat(), "error": str(exc)})
        return result


def _first(row: dict[str, Any], *names: str) -> Any:
    normalized = {str(k).strip().lower().replace(" ", ""): k for k in row}
    for name in names:
        key = normalized.get(name.lower().replace(" ", ""))
        if key is not None:
            return row[key]
    return None


def _number(value: Any) -> Decimal | None:
    if value in (None, "", "-", "None", "nan"):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except Exception:
        return None


def _date(value: Any) -> date | None:
    if value in (None, "", "-", "None", "nan"):
        return None
    from dateutil.parser import parse
    try:
        return parse(str(value), dayfirst=True, fuzzy=True).date()
    except Exception:
        return None


def _datetime(value: Any) -> datetime | None:
    if value in (None, "", "-", "None", "nan"):
        return None
    from dateutil.parser import parse
    try:
        parsed = parse(str(value), dayfirst=True, fuzzy=True)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


def _records_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    for key, value in payload.items():
        if key.lower() in {"data", "rows", "result", "records"} and isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    # Some NSE endpoints return a map whose second/top-level value is the data list.
    for value in payload.values():
        if isinstance(value, list) and (not value or isinstance(value[0], dict)):
            return value
    return []


def parse_shareholding(payload: dict[str, Any], *, instrument: Instrument | None, symbol: str, retrieved_at: datetime) -> list[ShareholdingSnapshot]:
    rows = _records_from_payload(payload)
    out: list[ShareholdingSnapshot] = []
    instrument_id = instrument.instrument_id if instrument else f"NSE:{symbol.upper()}"
    for row in rows:
        period_end = _date(_first(row, "date", "as on", "as_on_date", "period"))
        details = dict(row)
        holders = {
            "promoter_and_promoter_group": _number(_first(row, "pr_and_prgrp", "promoter", "promoter_and_promoter_group")),
            "public": _number(_first(row, "public_val", "public", "public_shareholding")),
            "employee_trusts": _number(_first(row, "employeeTrusts", "employee_trusts")),
            "raw": details,
        }
        source_id = str(_first(row, "recordId", "record_id", "xbrl", "date") or row)
        out.append(ShareholdingSnapshot(
            instrument_id=instrument_id,
            period_end=period_end,
            holders=holders,
            provenance=Provenance(
                source="nse", source_type="primary_exchange", source_dataset="corporate-share-holdings-master",
                source_url=f"https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern?symbol={symbol}",
                retrieved_at=retrieved_at,
                published_at=_datetime(_first(row, "broadcastDateTime", "broadcast_date_time", "submissionDate", "submission_date")),
                raw_ref=hashlib.sha256(source_id.encode()).hexdigest(),
            ),
        ))
    return out


def parse_insider_transactions(payload: dict[str, Any], *, instrument: Instrument | None, symbol: str | None, retrieved_at: datetime) -> list[InsiderTransaction]:
    rows = _records_from_payload(payload)
    out: list[InsiderTransaction] = []
    for row in rows:
        raw_symbol = str(_first(row, "symbol") or symbol or "").upper() or None
        if symbol and raw_symbol and raw_symbol != symbol.upper():
            continue
        instrument_id = instrument.instrument_id if instrument else (f"NSE:{raw_symbol}" if raw_symbol else None)
        digest = hashlib.sha256(repr(sorted(row.items())).encode()).hexdigest()
        out.append(InsiderTransaction(
            event_id=f"nse:insider:{digest}", instrument_id=instrument_id, symbol=raw_symbol,
            company_name=_first(row, "company"), regulation=_first(row, "anex", "regulation"),
            person_name=_first(row, "acqName", "name of the acquirer/disposer"),
            person_category=_first(row, "personCategory", "category of person"),
            security_type_prior=_first(row, "secType", "type of security (prior)"),
            securities_prior=_number(_first(row, "befAcqSharesNo", "no. of security (prior)")),
            holding_percent_prior=_number(_first(row, "befAcqSharesPer", "% shareholding (prior)")),
            security_type_acquired=_first(row, "tkdAcqm", "type of security (acquired/dispclosed)"),
            securities_acquired=_number(_first(row, "secAcq", "no. of securities (acquired/dispclosed)")),
            transaction_value=_number(_first(row, "secVal", "value of security (acquired/dispclosed)")),
            transaction_type=_first(row, "tdpTransactionType", "acquisition/disposal transaction type"),
            security_type_post=_first(row, "securitiesTypePost", "type of security (post)"),
            securities_post=_number(_first(row, "afterAcqSharesNo", "no. of security (post)")),
            holding_percent_post=_number(_first(row, "afterAcqSharesPer", "% post")),
            acquisition_from=_date(_first(row, "acqfromDt", "date of allotment/acquisition from")),
            acquisition_to=_date(_first(row, "acqtoDt", "date of allotment/acquisition to")),
            intimation_date=_datetime(_first(row, "intimDt", "date of initmation to company")),
            mode=_first(row, "acqMode", "mode of acquisition"),
            derivative_type=_first(row, "derivativeType", "derivative type security"),
            derivative_contract_type=_first(row, "tdpDerivativeContractType", "derivative contract specification"),
            buy_value=_number(_first(row, "buyValue", "notional value(buy)")),
            buy_quantity=_number(_first(row, "buyQuantity", "number of units/contract lot size (buy)")),
            sell_value=_number(_first(row, "sellValue", "notional value(sell)")),
            sell_quantity=_number(_first(row, "sellquantity", "number of units/contract lot size (sell)")),
            exchange=_first(row, "exchange"), remarks=_first(row, "remarks", "remark"),
            xbrl_url=_first(row, "xbrl"),
            broadcast_at=_datetime(_first(row, "date", "broadcast date and time")),
            details=dict(row),
            provenance=Provenance(
                source="nse", source_type="primary_exchange", source_dataset="corporates-pit",
                source_url="https://www.nseindia.com/companies-listing/corporate-filings-insider-trading",
                retrieved_at=retrieved_at,
            ),
        ))
    return out


def parse_large_deals(payload: dict[str, Any], *, mode: str, symbol: str | None, retrieved_at: datetime) -> list[LargeDeal]:
    if mode == "bulk_deals":
        rows = payload.get("BULK_DEALS_DATA", [])
    elif mode == "block_deals":
        rows = payload.get("BLOCK_DEALS_DATA", [])
    else:
        rows = payload.get("SHORT_DEALS_DATA", [])
    return parse_large_deal_rows(rows, mode=mode, symbol=symbol, retrieved_at=retrieved_at)


def parse_large_deal_rows(rows: Iterable[dict[str, Any]], *, mode: str, symbol: str | None, retrieved_at: datetime) -> list[LargeDeal]:
    out: list[LargeDeal] = []
    for row in rows:
        raw_symbol = str(_first(row, "symbol") or "").upper()
        if symbol and raw_symbol != symbol.upper():
            continue
        digest = hashlib.sha256(repr(sorted(row.items())).encode()).hexdigest()
        out.append(LargeDeal(
            event_id=f"nse:{mode}:{digest}", symbol=raw_symbol,
            company_name=_first(row, "name", "company"), deal_type=mode,
            trade_date=_date(_first(row, "date", "trade_date")),
            client_name=_first(row, "clientName", "client_name"),
            side=_first(row, "buySell", "buy_sell", "side"),
            quantity=_number(_first(row, "qty", "quantity")),
            weighted_average_price=_number(_first(row, "watp", "weighted_average_price")),
            remarks=_first(row, "remarks", "remark"), details=dict(row),
            provenance=Provenance(
                source="nse", source_type="primary_exchange", source_dataset="snapshot-capital-market-largedeal",
                source_url="https://www.nseindia.com/report-detail/display-bulk-and-block-deals",
                retrieved_at=retrieved_at,
            ),
        ))
    return out
