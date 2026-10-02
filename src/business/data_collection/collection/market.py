from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from data_collection.collection.results import CollectionResult, RawPayload
from data_collection.domains.models import Instrument, MarketQuote, PriceBar
from data_collection.providers.nse_archives import NSEArchivesProvider
from data_collection.providers.upstox import UpstoxProvider
from data_collection.providers.yfinance import YahooFinanceProvider


class MarketCollector:
    """Provider-neutral collector for Indian cash-equity market data."""

    domain = "market"

    def __init__(self, *, yfinance: YahooFinanceProvider | None = None, upstox: UpstoxProvider | None = None, nse: NSEArchivesProvider | None = None):
        self.yfinance = yfinance
        self.upstox = upstox
        self.nse = nse

    def daily_history(self, instrument: Instrument | None = None, *, symbol: str | None = None, instrument_key: str | None = None, period: str = "1mo", start: date | None = None, end: date | None = None, sources: Iterable[str] = ("yfinance",)) -> CollectionResult[PriceBar]:
        symbol = symbol or (instrument.symbol if instrument else None)
        if not symbol:
            raise ValueError("symbol or instrument is required")
        canonical_id = instrument.instrument_id if instrument else symbol.upper()
        result: CollectionResult[PriceBar] = CollectionResult(domain=self.domain)
        for source in sources:
            try:
                if source == "yfinance":
                    if self.yfinance is None:
                        raise RuntimeError("yfinance provider is not configured")
                    records = self.yfinance.collect_history(symbol, period=period, interval="1d", start=start, end=end, instrument_id=canonical_id)
                    result.records.extend(records)
                    result.raw_payloads.append(RawPayload(source="yfinance", domain=self.domain, retrieved_at=datetime.now(timezone.utc), payload=[r.model_dump(mode="json") for r in records], request={"symbol": symbol, "period": period, "interval": "1d"}))
                elif source == "upstox":
                    if self.upstox is None:
                        raise RuntimeError("upstox provider is not configured")
                    instrument_key = instrument_key or (instrument.instrument_key if instrument else None)
                    if not instrument_key:
                        raise ValueError("instrument_key is required for Upstox")
                    to_date = end or date.today()
                    from_date = start or (to_date - timedelta(days=30))
                    payload = self.upstox.historical_candles_v3(instrument_key, "days", 1, to_date, from_date)
                    records = self.upstox.parse_candles(payload, canonical_id, timeframe="1d")
                    result.records.extend(records)
                    result.raw_payloads.append(RawPayload(source="upstox", domain=self.domain, retrieved_at=datetime.now(timezone.utc), payload=payload, request={"instrument_key": instrument_key, "unit": "days", "interval": 1, "to_date": str(to_date), "from_date": str(from_date)}))
                elif source == "nse":
                    if self.nse is None:
                        raise RuntimeError("NSE archive provider is not configured")
                    if start is None:
                        raise ValueError("start is required for NSE archive collection")
                    for trading_date in _date_range(start, end or start):
                        payload = self.nse.daily_equities_with_delivery(trading_date)
                        records = self.nse.normalize_equity_daily(payload, instrument=instrument, symbol=symbol, instrument_id=canonical_id, trading_date=trading_date)
                        result.records.extend(records)
                        result.raw_payloads.append(RawPayload(source="nse", domain=self.domain, retrieved_at=datetime.now(timezone.utc), payload=_jsonable_frame(payload), request={"dataset": "sec_bhavdata_full", "trading_date": str(trading_date)}))
                else:
                    raise ValueError(f"Unknown market source: {source}")
            except Exception as exc:
                result.errors.append({"source": source, "error": str(exc)})
        return result

    def daily_sample(self, *args, **kwargs) -> CollectionResult[PriceBar]:
        result = self.daily_history(*args, **kwargs)
        result.records = result.records[:5]
        return result

    def intraday(self, instrument: Instrument, *, unit: str = "minutes", interval: int = 1) -> CollectionResult[PriceBar]:
        if self.upstox is None:
            return CollectionResult(domain=self.domain, errors=[{"source": "upstox", "error": "provider is not configured"}])
        if not instrument.instrument_key:
            raise ValueError("instrument.instrument_key is required")
        now = datetime.now(timezone.utc)
        payload = self.upstox.intraday_candles_v3(instrument.instrument_key, unit, interval)
        records = self.upstox.parse_candles(payload, instrument.instrument_id, timeframe=f"{interval}{unit[0]}", retrieved_at=now)
        return CollectionResult(domain=self.domain, records=records, raw_payloads=[RawPayload(source="upstox", domain=self.domain, retrieved_at=now, payload=payload, request={"instrument_key": instrument.instrument_key, "unit": unit, "interval": interval})])

    def full_quote(self, instrument: Instrument) -> CollectionResult[MarketQuote]:
        if self.upstox is None:
            return CollectionResult(domain=self.domain, errors=[{"source": "upstox", "error": "provider is not configured"}])
        if not instrument.instrument_key:
            raise ValueError("instrument.instrument_key is required")
        now = datetime.now(timezone.utc)
        payload = self.upstox.full_quotes_v3([instrument.instrument_key])
        records = self.upstox.parse_full_quotes(payload, {instrument.instrument_key: instrument.instrument_id}, retrieved_at=now)
        return CollectionResult(domain=self.domain, records=records, raw_payloads=[RawPayload(source="upstox", domain=self.domain, retrieved_at=now, payload=payload, request={"instrument_key": instrument.instrument_key})])

    def quote(self, instrument: Instrument) -> CollectionResult[MarketQuote]:
        if self.upstox is None:
            return CollectionResult(domain=self.domain, errors=[{"source": "upstox", "error": "provider is not configured"}])
        if not instrument.instrument_key:
            raise ValueError("instrument.instrument_key is required")
        now = datetime.now(timezone.utc)
        payload = self.upstox.ltp_v3([instrument.instrument_key])
        records = self.upstox.parse_ltp(payload, {instrument.instrument_key: instrument.instrument_id}, retrieved_at=now)
        return CollectionResult(domain=self.domain, records=records, raw_payloads=[RawPayload(source="upstox", domain=self.domain, retrieved_at=now, payload=payload, request={"instrument_key": instrument.instrument_key})])


def _date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _jsonable_frame(frame):
    if hasattr(frame, "where"):
        frame = frame.where(frame.notna(), None)
    return frame.to_dict(orient="records") if hasattr(frame, "to_dict") else frame
