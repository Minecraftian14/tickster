from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from data_collection.collection.results import CollectionResult, RawPayload
from data_collection.domains.models import CompanyPeer, FundamentalSnapshot, ShareholdingSnapshot, Provenance
from data_collection.providers.upstox import UpstoxProvider


class FundamentalsCollector:
    domain = "fundamentals"

    def __init__(self, *, upstox: UpstoxProvider | None = None):
        self.upstox = upstox

    def company_snapshot(
        self,
        isin: str,
        instrument_id: str,
        *,
        frequency: str = "yearly",
        statement_type: str = "consolidated",
    ) -> CollectionResult[FundamentalSnapshot]:
        """Collect period-aware financial records plus profile/ratio snapshots."""
        result: CollectionResult[FundamentalSnapshot] = CollectionResult(domain=self.domain)
        if self.upstox is None:
            result.add_error(source="upstox", operation="company_snapshot", exc=RuntimeError("provider is not configured"), isin=isin)
            return result

        now = datetime.now(timezone.utc)
        scalar_endpoints = {
            "profile": self.upstox.company_profile,
            "key_ratios": self.upstox.key_ratios,
        }
        for name, fn in scalar_endpoints.items():
            try:
                payload = fn(isin)
                result.raw_payloads.append(RawPayload(source="upstox", domain=self.domain, retrieved_at=now, payload=payload, request={"isin": isin, "endpoint": name}))
                data = payload.get("data") if isinstance(payload, dict) else payload
                result.records.append(FundamentalSnapshot(
                    instrument_id=instrument_id,
                    statement_name=name,
                    metrics=data if isinstance(data, dict) else {"value": data},
                    provenance=Provenance(source="upstox", source_type="broker_api", source_dataset=name, retrieved_at=now),
                ))
            except Exception as exc:
                result.add_error(source="upstox", operation=name, exc=exc, isin=isin)

        statement_endpoints = {
            "income_statement": lambda x: self.upstox.income_statement(x, statement_type=statement_type, time_period=frequency, full_statement=True),
            "balance_sheet": lambda x: self.upstox.balance_sheet(x, statement_type=statement_type, full_statement=True),
            "cash_flow": lambda x: self.upstox.cash_flow(x, statement_type=statement_type, full_statement=True),
        }
        for name, fn in statement_endpoints.items():
            try:
                payload = fn(isin)
                result.raw_payloads.append(RawPayload(source="upstox", domain=self.domain, retrieved_at=now, payload=payload, request={"isin": isin, "endpoint": name, "frequency": frequency, "statement_type": statement_type}))
                result.records.extend(statement_snapshots_from_payload(payload, instrument_id=instrument_id, statement_name=name, retrieved_at=now))
            except Exception as exc:
                result.add_error(source="upstox", operation=name, exc=exc, isin=isin)
        return result

    def company_peers(self, isin: str, instrument_id: str) -> CollectionResult[CompanyPeer]:
        result: CollectionResult[CompanyPeer] = CollectionResult(domain=self.domain)
        if self.upstox is None:
            result.add_error(source="upstox", operation="competitors", exc=RuntimeError("provider is not configured"), isin=isin)
            return result
        now = datetime.now(timezone.utc)
        try:
            payload = self.upstox.competitors(isin)
            result.raw_payloads.append(RawPayload(source="upstox", domain=self.domain, retrieved_at=now, payload=payload, request={"isin": isin, "endpoint": "competitors"}))
            for item in (payload.get("data") if isinstance(payload, dict) else []) or []:
                if not isinstance(item, dict):
                    result.add_error(source="upstox", operation="competitors.parse", exc=ValueError("competitor entry is not an object"), raw=item)
                    continue
                sector_inr = item.get("sector_market_cap_inr") or {}
                sector_usd = item.get("sector_market_cap_usd") or {}
                peer_key = str(item.get("instrument_key") or item.get("isin") or item.get("company_profile") or "")
                peer_isin = peer_key.split("|", 1)[1] if "|" in peer_key else item.get("isin")
                result.records.append(CompanyPeer(
                    instrument_id=instrument_id,
                    peer_instrument_key=item.get("instrument_key"),
                    peer_isin=peer_isin,
                    peer_name=item.get("company_name") or item.get("name"),
                    sector=item.get("sector"),
                    description=item.get("company_profile"),
                    sector_market_cap_inr=_decimal(sector_inr.get("value")),
                    sector_market_cap_usd=_decimal(sector_usd.get("value")),
                    metadata={"raw": item},
                    provenance=Provenance(source="upstox", source_type="broker_api", source_dataset="competitors", retrieved_at=now),
                ))
        except Exception as exc:
            result.add_error(source="upstox", operation="competitors", exc=exc, isin=isin)
        return result


class ShareholdingCollector:
    domain = "shareholding"

    def __init__(self, *, upstox: UpstoxProvider | None = None):
        self.upstox = upstox

    def sample(self, isin: str, instrument_id: str) -> CollectionResult[ShareholdingSnapshot]:
        result: CollectionResult[ShareholdingSnapshot] = CollectionResult(domain=self.domain)
        if self.upstox is None:
            result.add_error(source="upstox", operation="share_holdings", exc=RuntimeError("provider is not configured"), isin=isin)
            return result
        now = datetime.now(timezone.utc)
        try:
            payload = self.upstox.share_holdings(isin)
            result.raw_payloads.append(RawPayload(
                source="upstox", domain=self.domain, retrieved_at=now,
                payload=payload, request={"isin": isin}
            ))
            result.records.append(ShareholdingSnapshot(
                instrument_id=instrument_id,
                holders={"raw": payload},
                provenance=Provenance(
                    source="upstox", source_type="broker_api",
                    source_dataset="share-holdings", retrieved_at=now,
                ),
            ))
        except Exception as exc:
            result.add_error(source="upstox", operation="share-holdings", exc=exc, isin=isin)
        return result


def statement_snapshots_from_payload(payload: dict[str, Any], *, instrument_id: str, statement_name: str, retrieved_at: datetime) -> list[FundamentalSnapshot]:
    data = payload.get("data") if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        return []
    statement_type = data.get("type")
    period_type = data.get("time_period") or "yearly"
    units_in = data.get("units_in")
    history_groups: dict[str, dict[str, Any]] = {}

    summary_key = statement_name if statement_name in data else ("history" if "history" in data else None)
    entries = data.get(summary_key) if summary_key else None
    if isinstance(entries, list):
        if summary_key == "history":
            # Balance-sheet style payloads expose one period row directly.
            for point in entries:
                if not isinstance(point, dict) or point.get("period") is None:
                    continue
                period = str(point["period"])
                bucket = history_groups.setdefault(period, {"period": period, "summary": {}, "full_statement": {}})
                bucket["summary"].update({str(k): v for k, v in point.items() if k != "period"})
        else:
            for group in entries:
                if not isinstance(group, dict):
                    continue
                label_key = group.get("category") or group.get("particular") or "value"
                for point in group.get("history") or []:
                    if not isinstance(point, dict) or point.get("period") is None:
                        continue
                    period = str(point["period"])
                    bucket = history_groups.setdefault(period, {"period": period, "summary": {}, "full_statement": {}})
                    bucket["summary"][str(label_key)] = {
                        "value": point.get("value"),
                        "change": point.get("change"),
                    }

    for group in data.get("full_statement") or []:
        if not isinstance(group, dict):
            continue
        label_key = group.get("particular") or group.get("category")
        if not label_key:
            continue
        for point in group.get("history") or []:
            if not isinstance(point, dict) or point.get("period") is None:
                continue
            period = str(point["period"])
            bucket = history_groups.setdefault(period, {"period": period, "summary": {}, "full_statement": {}})
            bucket["full_statement"][str(label_key)] = point.get("value")

    snapshots: list[FundamentalSnapshot] = []
    for bucket in history_groups.values():
        period_end = parse_period_end(bucket["period"])
        snapshots.append(FundamentalSnapshot(
            instrument_id=instrument_id,
            period_end=period_end,
            period_type=period_type,
            statement_type=str(statement_type) if statement_type is not None else None,
            statement_name=statement_name,
            units_in=str(units_in) if units_in is not None else None,
            metrics={"summary": bucket["summary"], "full_statement": bucket["full_statement"], "period_label": bucket["period"]},
            provenance=Provenance(source="upstox", source_type="broker_api", source_dataset=statement_name, retrieved_at=retrieved_at),
        ))
    return snapshots


def parse_period_end(label: str) -> date | None:
    text = label.strip()
    try:
        from dateutil.parser import parse
        parsed = parse(text, default=datetime(2000, 1, 1), fuzzy=True)
        last_day = monthrange(parsed.year, parsed.month)[1]
        return date(parsed.year, parsed.month, last_day)
    except Exception:
        return None


def _decimal(value: Any) -> Decimal | None:
    if value in (None, "", "-", "None", "nan"):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except Exception:
        return None
