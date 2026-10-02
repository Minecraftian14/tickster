from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from data_collection.collection.results import CollectionResult, RawPayload
from data_collection.domains.models import Instrument, Provenance
from data_collection.providers.upstox import UpstoxProvider


class InstrumentCollector:
    """Collect the canonical identity spine for NSE equities."""

    domain = "instruments"

    def __init__(self, *, upstox: UpstoxProvider | None = None):
        self.upstox = upstox

    def search_equities(self, query: str) -> CollectionResult[Instrument]:
        result: CollectionResult[Instrument] = CollectionResult(domain=self.domain)
        if self.upstox is None:
            result.errors.append({"source": "upstox", "error": "provider is not configured"})
            return result

        now = datetime.now(timezone.utc)
        try:
            payload = self.upstox.search_instruments(query, exchanges="NSE", segments="EQ")
            result.raw_payloads.append(RawPayload(
                source="upstox",
                domain=self.domain,
                retrieved_at=now,
                payload=payload,
                request={"query": query, "exchanges": "NSE", "segments": "EQ"},
            ))
            for item in payload.get("data", []):
                if item.get("exchange") != "NSE" or item.get("instrument_type") != "EQ":
                    continue
                result.records.append(Instrument(
                    instrument_id=item.get("instrument_key") or item.get("isin") or item["trading_symbol"],
                    isin=item.get("isin"),
                    symbol=item.get("trading_symbol") or item.get("short_name") or query.upper(),
                    exchange="NSE",
                    instrument_key=item.get("instrument_key"),
                    exchange_token=item.get("exchange_token"),
                    name=item.get("name"),
                    series=item.get("series"),
                    currency="INR",
                    active=True,
                    tick_size=Decimal(str(item["tick_size"])) if item.get("tick_size") is not None else None,
                    lot_size=int(item["lot_size"]) if item.get("lot_size") is not None else None,
                    provenance=Provenance(
                        source="upstox",
                        source_type="broker_api",
                        source_dataset="instrument-search",
                        retrieved_at=now,
                    ),
                ))
        except Exception as exc:
            result.errors.append({"source": "upstox", "endpoint": "instrument-search", "error": str(exc)})
        return result
