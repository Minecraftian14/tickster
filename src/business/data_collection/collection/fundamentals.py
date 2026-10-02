from __future__ import annotations

from datetime import datetime, timezone

from data_collection.collection.results import CollectionResult, RawPayload
from data_collection.domains.models import FundamentalSnapshot, ShareholdingSnapshot, Provenance
from data_collection.providers.upstox import UpstoxProvider


class FundamentalsCollector:
    domain = "fundamentals"

    def __init__(self, *, upstox: UpstoxProvider | None = None):
        self.upstox = upstox

    def company_snapshot(self, isin: str, instrument_id: str) -> CollectionResult[FundamentalSnapshot]:
        result: CollectionResult[FundamentalSnapshot] = CollectionResult(domain=self.domain)
        if self.upstox is None:
            result.errors.append({"source": "upstox", "error": "provider is not configured"})
            return result

        now = datetime.now(timezone.utc)
        endpoints = {
            "profile": self.upstox.company_profile,
            "income_statement": lambda x: self.upstox.income_statement(x, full_statement=True),
            "balance_sheet": lambda x: self.upstox.balance_sheet(x, full_statement=True),
            "cash_flow": lambda x: self.upstox.cash_flow(x, full_statement=True),
            "key_ratios": self.upstox.key_ratios,
        }
        for name, fn in endpoints.items():
            try:
                payload = fn(isin)
                result.raw_payloads.append(RawPayload(
                    source="upstox", domain=self.domain, retrieved_at=now,
                    payload=payload, request={"isin": isin, "endpoint": name}
                ))
                result.records.append(FundamentalSnapshot(
                    instrument_id=instrument_id,
                    metrics={name: payload},
                    provenance=Provenance(
                        source="upstox",
                        source_type="broker_api",
                        source_dataset=name,
                        retrieved_at=now,
                    ),
                ))
            except Exception as exc:
                result.errors.append({"source": "upstox", "endpoint": name, "error": str(exc)})
        return result


class ShareholdingCollector:
    domain = "shareholding"

    def __init__(self, *, upstox: UpstoxProvider | None = None):
        self.upstox = upstox

    def sample(self, isin: str, instrument_id: str) -> CollectionResult[ShareholdingSnapshot]:
        result: CollectionResult[ShareholdingSnapshot] = CollectionResult(domain=self.domain)
        if self.upstox is None:
            result.errors.append({"source": "upstox", "error": "provider is not configured"})
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
            result.errors.append({"source": "upstox", "endpoint": "share-holdings", "error": str(exc)})
        return result
