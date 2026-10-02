from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Iterable

import pandas as pd

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

    def daily_history(
        self,
        instrument: Instrument | None = None,
        *,
        symbol: str | None = None,
        instrument_key: str | None = None,
        period: str = "1mo",
        start: date | None = None,
        end: date | None = None,
        sources: Iterable[str] = ("yfinance",),
    ) -> CollectionResult[PriceBar]:
        symbol = symbol or (instrument.symbol if instrument else None)
        if not symbol:
            raise ValueError("symbol or instrument is required")
        canonical_id = instrument.instrument_id if instrument else symbol.upper()
        result: CollectionResult[PriceBar] = CollectionResult(domain=self.domain)
        instrument_key = instrument_key or (instrument.instrument_key if instrument else None)

        for source in sources:
            try:
                if source == "yfinance":
                    if self.yfinance is None:
                        raise RuntimeError("yfinance provider is not configured")
                    if hasattr(self.yfinance, "quote_history") and hasattr(self.yfinance, "parse_history_frame"):
                        frame = self.yfinance.quote_history(symbol, period=period, interval="1d", start=start, end=end)
                        records = self.yfinance.parse_history_frame(
                            frame,
                            symbol=symbol,
                            instrument_id=canonical_id,
                            interval="1d",
                            source_dataset="Yahoo Finance chart history",
                        )
                        raw_payload = _jsonable_frame(frame)
                        raw_metadata = {"representation": "provider_dataframe"}
                    else:
                        # Keep lightweight test doubles/custom providers usable.
                        records = self.yfinance.collect_history(
                            symbol, instrument_id=canonical_id, period=period, interval="1d", start=start, end=end
                        )
                        raw_payload = [r.model_dump(mode="json") for r in records]
                        raw_metadata = {"representation": "canonical_fallback"}
                    result.records.extend(records)
                    result.raw_payloads.append(RawPayload(
                        source="yfinance", domain=self.domain, retrieved_at=datetime.now(timezone.utc),
                        payload=raw_payload,
                        request={"symbol": symbol, "period": period, "interval": "1d", "start": str(start) if start else None, "end": str(end) if end else None},
                        metadata=raw_metadata,
                    ))
                elif source == "upstox":
                    if self.upstox is None:
                        raise RuntimeError("upstox provider is not configured")
                    if not instrument_key:
                        raise ValueError("instrument_key is required for Upstox")
                    to_date = end or date.today()
                    from_date = start or (to_date - timedelta(days=30))
                    for chunk_start, chunk_end in _date_chunks(from_date, to_date, max_days=3653):
                        now = datetime.now(timezone.utc)
                        payload = self.upstox.historical_candles_v3(instrument_key, "days", 1, chunk_end, chunk_start)
                        records = self.upstox.parse_candles(
                            payload,
                            canonical_id,
                            timeframe="1d",
                            retrieved_at=now,
                            issues=result.issues,
                        )
                        result.records.extend(records)
                        result.raw_payloads.append(RawPayload(
                            source="upstox", domain=self.domain, retrieved_at=now,
                            payload=payload,
                            request={"instrument_key": instrument_key, "unit": "days", "interval": 1, "to_date": str(chunk_end), "from_date": str(chunk_start)},
                        ))
                elif source == "nse":
                    if self.nse is None:
                        raise RuntimeError("NSE archive provider is not configured")
                    if start is None:
                        raise ValueError("start is required for NSE archive collection")
                    for trading_date in _date_range(start, end or start):
                        now = datetime.now(timezone.utc)
                        payload = self.nse.daily_equities_with_delivery(trading_date)
                        records = self.nse.normalize_equity_daily(payload, instrument=instrument, symbol=symbol, instrument_id=canonical_id, trading_date=trading_date)
                        result.records.extend(records)
                        result.raw_payloads.append(RawPayload(source="nse", domain=self.domain, retrieved_at=now, payload=_jsonable_frame(payload), request={"dataset": "sec_bhavdata_full", "trading_date": str(trading_date)}))
                else:
                    raise ValueError(f"Unknown market source: {source}")
            except Exception as exc:
                result.add_error(source=source, operation="daily_history", exc=exc, symbol=symbol)
        return result

    def daily_sample(self, *args, **kwargs) -> CollectionResult[PriceBar]:
        result = self.daily_history(*args, **kwargs)
        result.records = result.records[:5]
        return result

    def eod_statistics(self, trading_date: date, *, source: str = "nse") -> CollectionResult[PriceBar]:
        """Collect an exchange-wide equity EOD dataset efficiently in one archive fetch."""
        result: CollectionResult[PriceBar] = CollectionResult(domain=self.domain)
        if source != "nse":
            result.add_error(source=source, operation="eod_statistics", exc=ValueError("eod_statistics currently supports source='nse'"), trading_date=trading_date.isoformat())
            return result
        if self.nse is None:
            result.add_error(source="nse", operation="eod_statistics", exc=RuntimeError("NSE archive provider is not configured"), trading_date=trading_date.isoformat())
            return result
        now = datetime.now(timezone.utc)
        try:
            frame = self.nse.daily_equities_with_delivery(trading_date)
            records = self.nse.normalize_equity_universe_daily(frame, trading_date=trading_date)
            result.records.extend(records)
            result.raw_payloads.append(RawPayload(source="nse", domain=self.domain, retrieved_at=now, payload=_jsonable_frame(frame), request={"dataset": "sec_bhavdata_full", "trading_date": trading_date.isoformat()}))
        except Exception as exc:
            result.add_error(source="nse", operation="eod_statistics", exc=exc, trading_date=trading_date.isoformat())
        return result

    def intraday(self, instrument: Instrument, *, unit: str = "minutes", interval: int = 1) -> CollectionResult[PriceBar]:
        if self.upstox is None:
            return CollectionResult(domain=self.domain, errors=[{"source": "upstox", "error": "provider is not configured"}])
        if not instrument.instrument_key:
            raise ValueError("instrument.instrument_key is required")
        now = datetime.now(timezone.utc)
        payload = self.upstox.intraday_candles_v3(instrument.instrument_key, unit, interval)
        issues: list[dict] = []
        records = self.upstox.parse_candles(payload, instrument.instrument_id, timeframe=f"{interval}{unit[0]}", retrieved_at=now, issues=issues)
        return CollectionResult(
            domain=self.domain,
            records=records,
            raw_payloads=[RawPayload(source="upstox", domain=self.domain, retrieved_at=now, payload=payload, request={"instrument_key": instrument.instrument_key, "unit": unit, "interval": interval})],
            issues=issues,
        )

    def full_quote(self, instrument: Instrument) -> CollectionResult[MarketQuote]:
        if self.upstox is None:
            return CollectionResult(domain=self.domain, errors=[{"source": "upstox", "error": "provider is not configured"}])
        if not instrument.instrument_key:
            raise ValueError("instrument.instrument_key is required")
        now = datetime.now(timezone.utc)
        payload = self.upstox.full_quotes_v3([instrument.instrument_key])
        issues: list[dict] = []
        records = self.upstox.parse_full_quotes(payload, {instrument.instrument_key: instrument.instrument_id}, retrieved_at=now, issues=issues)
        return CollectionResult(
            domain=self.domain,
            records=records,
            raw_payloads=[RawPayload(source="upstox", domain=self.domain, retrieved_at=now, payload=payload, request={"instrument_key": instrument.instrument_key})],
            issues=issues,
        )

    def quote(self, instrument: Instrument) -> CollectionResult[MarketQuote]:
        if self.upstox is None:
            return CollectionResult(domain=self.domain, errors=[{"source": "upstox", "error": "provider is not configured"}])
        if not instrument.instrument_key:
            raise ValueError("instrument.instrument_key is required")
        now = datetime.now(timezone.utc)
        payload = self.upstox.ltp_v3([instrument.instrument_key])
        issues: list[dict] = []
        records = self.upstox.parse_ltp(payload, {instrument.instrument_key: instrument.instrument_id}, retrieved_at=now, issues=issues)
        return CollectionResult(
            domain=self.domain,
            records=records,
            raw_payloads=[RawPayload(source="upstox", domain=self.domain, retrieved_at=now, payload=payload, request={"instrument_key": instrument.instrument_key})],
            issues=issues,
        )


def _date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _date_chunks(start: date, end: date, *, max_days: int):
    current = start
    while current <= end:
        chunk_end = min(end, current + timedelta(days=max_days - 1))
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


def _jsonable_frame(frame: pd.DataFrame):
    if frame is None:
        return None
    safe = frame.copy()
    safe.index = [str(x) for x in safe.index]
    safe = safe.where(pd.notna(safe), None)
    return safe.reset_index(names="timestamp").to_dict(orient="records")
