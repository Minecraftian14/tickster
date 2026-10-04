from __future__ import annotations

from datetime import datetime, timezone

from data_collection.collection.results import CollectionResult, RawPayload
from data_collection.domains.models import Instrument
from data_collection.processing.instruments import deduplicate_instruments
from data_collection.providers.upstox import UpstoxProvider
from data_collection.providers.yfinance import YahooFinanceProvider


class InstrumentCollector:
    """Collect and normalize the NSE cash-equity identity universe."""

    domain = "instruments"

    def __init__(self, *, upstox: UpstoxProvider = None, yfinance: YahooFinanceProvider = None):
        self.upstox = upstox
        self.yfinance = yfinance

    def search_equities(self, query: str) -> CollectionResult[Instrument]:
        result: CollectionResult[Instrument] = CollectionResult(domain=self.domain)
        if self.upstox is None:
            result.errors.append({"source": "upstox", "error": "provider is not configured"})
            return result
        now = datetime.now(timezone.utc)
        try:
            payload = self.upstox.search_instruments(query, exchanges="NSE", segments="EQ")
            result.raw_payloads.append(RawPayload(source="upstox", domain=self.domain, retrieved_at=now, payload=payload, request={"query": query, "exchanges": "NSE", "segments": "EQ"}))
            for item in payload.get("data", []):
                if item.get("exchange") == "NSE" and item.get("instrument_type") == "EQ":
                    instrument = UpstoxProvider.normalize_instrument(item, retrieved_at=now)
                    if self.yfinance is not None:
                        instrument.provider_identifiers['yfinance'] = self.yfinance.extract_identifier(instrument)
                    # TODO: Add NSE identifier as well
                    result.records.append(instrument)
            result.records = deduplicate_instruments(result.records)
        except Exception as exc:
            result.errors.append({"source": "upstox", "endpoint": "instrument-search", "error": str(exc)})
        return result

    def search_all_pages(self, query: str, *, records: int = 30) -> CollectionResult[Instrument]:
        result: CollectionResult[Instrument] = CollectionResult(domain=self.domain)
        if self.upstox is None:
            result.errors.append({"source": "upstox", "error": "provider is not configured"})
            return result
        page = 1
        while True:
            now = datetime.now(timezone.utc)
            try:
                payload = self.upstox.search_instruments(query, exchanges="NSE", segments="EQ", page_number=page, records=records)
                result.raw_payloads.append(RawPayload(source="upstox", domain=self.domain, retrieved_at=now, payload=payload, request={"query": query, "page_number": page, "records": records}))
                for item in payload.get("data", []):
                    if item.get("exchange") == "NSE" and item.get("instrument_type") == "EQ":
                        result.records.append(UpstoxProvider.normalize_instrument(item, retrieved_at=now))
                meta = payload.get("meta_data", {}).get("page", {})
                total_pages = int(meta.get("total_pages", page))
                if page >= total_pages:
                    break
                page += 1
            except Exception as exc:
                result.errors.append({"source": "upstox", "endpoint": "instrument-search", "page": page, "error": str(exc)})
                break
        result.records = deduplicate_instruments(result.records)
        return result
