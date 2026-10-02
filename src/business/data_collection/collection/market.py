from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Iterable

from data_collection.collection.results import CollectionResult, RawPayload
from data_collection.domains.models import PriceBar
from data_collection.providers.upstox import UpstoxProvider
from data_collection.providers.yfinance import YahooFinanceProvider


class MarketCollector:
    """Provider-neutral market collector.

    Multiple providers can be used for the same domain. We retain all observations
    and provenance here; reconciliation is deliberately deferred to processing.
    """

    domain = "market"

    def __init__(self, *, yfinance: YahooFinanceProvider | None = None, upstox: UpstoxProvider | None = None):
        self.yfinance = yfinance
        self.upstox = upstox

    def daily_sample(
            self,
            symbol: str,
            *,
            instrument_key: str | None = None,
            period: str = "1mo",
            start: date | None = None,
            end: date | None = None,
            sources: Iterable[str] = ("yfinance",),
    ) -> CollectionResult[PriceBar]:
        result: CollectionResult[PriceBar] = CollectionResult(domain=self.domain)
        for source in sources:
            try:
                if source == "yfinance":
                    if self.yfinance is None:
                        raise RuntimeError("yfinance provider is not configured")
                    records = self.yfinance.collect_price_sample(symbol, period=period)
                    result.records.extend(records)
                    result.raw_payloads.append(RawPayload(
                        source="yfinance",
                        domain=self.domain,
                        retrieved_at=datetime.now(timezone.utc),
                        payload=[r.model_dump(mode="json") for r in records],
                        request={"symbol": symbol, "period": period, "interval": "1d"},
                    ))
                elif source == "upstox":
                    if self.upstox is None:
                        raise RuntimeError("upstox provider is not configured")
                    if not instrument_key:
                        raise ValueError("instrument_key is required for Upstox")
                    to_date = end or date.today()
                    from_date = start or date(to_date.year, max(1, to_date.month - 1), 1)
                    payload = self.upstox.historical_candles_v3(
                        instrument_key, "days", 1, to_date, from_date
                    )
                    records = self.upstox.parse_candles(
                        payload, instrument_key, timeframe="1d"
                    )
                    result.records.extend(records)
                    result.raw_payloads.append(RawPayload(
                        source="upstox",
                        domain=self.domain,
                        retrieved_at=datetime.now(timezone.utc),
                        payload=payload,
                        request={
                            "instrument_key": instrument_key,
                            "unit": "days",
                            "interval": 1,
                            "to_date": str(to_date),
                            "from_date": str(from_date),
                        },
                    ))
                else:
                    raise ValueError(f"Unknown market source: {source}")
            except Exception as exc:  # collection should be resilient across sources
                result.errors.append({"source": source, "error": str(exc)})
        return result
