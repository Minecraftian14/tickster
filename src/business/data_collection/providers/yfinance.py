from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Any

import pandas as pd

from data_collection.domains import Instrument
from data_collection.domains.models import CorporateAction, NewsItem, PriceBar, Provenance


def _require_yfinance():
    try:
        import yfinance as yf  # type: ignore
    except ImportError as exc:
        raise RuntimeError("yfinance is not installed. Install with: pip install yfinance") from exc
    return yf


class YahooFinanceProvider:
    name = "yfinance"
    source_type = "aggregator"

    @staticmethod
    def _ticker(symbol: str):
        yf = _require_yfinance()
        return yf.Ticker(symbol if "." in symbol else f"{symbol}.NS")

    def health(self) -> dict:
        try:
            _require_yfinance()
            return {"provider": self.name, "installed": True}
        except RuntimeError as exc:
            return {"provider": self.name, "installed": False, "error": str(exc)}

    def quote_history(self, symbol: str, period: str = "1mo", interval: str = "1d", *, start=None, end=None) -> pd.DataFrame:
        kwargs = {"interval": interval, "auto_adjust": False, "actions": True}
        if start is not None or end is not None:
            kwargs["start"] = start
            kwargs["end"] = end
        else:
            kwargs["period"] = period
        return self._ticker(symbol).history(**kwargs)

    def collect_history(self, symbol: str, *, instrument_id: str, period: str = "1mo", interval: str = "1d", start=None, end=None) -> list[PriceBar]:
        df = self.quote_history(symbol, period=period, interval=interval, start=start, end=end)
        return self.parse_history_frame(df, symbol=symbol, instrument_id=instrument_id, interval=interval)

    @staticmethod
    def parse_history_frame(df: pd.DataFrame, *, symbol: str, instrument_id: str, interval: str, source_dataset: str = "Yahoo Finance chart history") -> list[PriceBar]:
        now = datetime.now(timezone.utc)
        if df is None or df.empty:
            return []
        out: list[PriceBar] = []
        required = {"Open", "High", "Low", "Close", "Volume"}
        missing = required.difference(df.columns)
        if missing:
            raise ValueError(f"Yahoo Finance history missing columns: {sorted(missing)}")
        for ts, row in df.iterrows():
            observed = pd.Timestamp(ts).to_pydatetime()
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            else:
                observed = observed.astimezone(timezone.utc)
            out.append(PriceBar(
                instrument_id=instrument_id, timestamp=observed, timeframe=interval,
                open=Decimal(str(row["Open"])) if pd.notna(row["Open"]) else None,
                high=Decimal(str(row["High"])) if pd.notna(row["High"]) else None,
                low=Decimal(str(row["Low"])) if pd.notna(row["Low"]) else None,
                close=Decimal(str(row["Close"])) if pd.notna(row["Close"]) else None,
                volume=int(row["Volume"]) if pd.notna(row["Volume"]) else None,
                provenance=Provenance(source="yfinance", source_type="aggregator", source_dataset=source_dataset, retrieved_at=now, observed_at=observed),
            ))
        return out

    def collect_price_sample(self, symbol: str, period: str = "5d", *, instrument_id: str | None = None) -> list[PriceBar]:
        df = self.quote_history(symbol, period=period, interval="1d")
        now = datetime.now(timezone.utc)
        instrument_id = instrument_id or (symbol if symbol.endswith(".NS") else f"{symbol}.NS")
        out: list[PriceBar] = []
        for ts, row in df.head(5).iterrows():
            observed = pd.Timestamp(ts).to_pydatetime()
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            else:
                observed = observed.astimezone(timezone.utc)
            out.append(PriceBar(
                instrument_id=instrument_id, timestamp=observed, timeframe="1d",
                open=Decimal(str(row["Open"])) if pd.notna(row["Open"]) else None,
                high=Decimal(str(row["High"])) if pd.notna(row["High"]) else None,
                low=Decimal(str(row["Low"])) if pd.notna(row["Low"]) else None,
                close=Decimal(str(row["Close"])) if pd.notna(row["Close"]) else None,
                volume=int(row["Volume"]) if pd.notna(row["Volume"]) else None,
                provenance=Provenance(source="yfinance", source_type="aggregator", source_dataset="Yahoo Finance chart history", retrieved_at=now, observed_at=observed),
            ))
        return out

    def collect_corporate_actions(self, symbol: str, *, instrument_id: str | None = None) -> list[CorporateAction]:
        actions = self._ticker(symbol).actions
        now = datetime.now(timezone.utc)
        instrument_id = instrument_id or (symbol if symbol.endswith(".NS") else f"{symbol}.NS")
        if actions is None or actions.empty:
            return []
        out: list[CorporateAction] = []
        for ts, row in actions.iterrows():
            if "Dividends" in row and pd.notna(row["Dividends"]) and float(row["Dividends"]) != 0:
                out.append(CorporateAction(instrument_id=instrument_id, action_type="dividend", ex_date=ts.date(), amount=Decimal(str(row["Dividends"])),
                                           provenance=Provenance(source="yfinance", source_type="aggregator", source_dataset="Yahoo Finance actions", retrieved_at=now, observed_at=ts.to_pydatetime())))
            if "Stock Splits" in row and pd.notna(row["Stock Splits"]) and float(row["Stock Splits"]) != 0:
                out.append(CorporateAction(instrument_id=instrument_id, action_type="stock_split", ex_date=ts.date(), ratio=str(row["Stock Splits"]),
                                           provenance=Provenance(source="yfinance", source_type="aggregator", source_dataset="Yahoo Finance actions", retrieved_at=now, observed_at=ts.to_pydatetime())))
        return out

    def get_news_raw(self, symbol: str, *, count: int = 10, tab: str = "news") -> list[dict[str, Any]]:
        ticker = self._ticker(symbol)
        return ticker.get_news(count=count, tab=tab) or []

    def search_news_raw(self, query: str, *, news_count: int = 10) -> list[dict[str, Any]]:
        yf = _require_yfinance()
        return yf.Search(query, news_count=news_count).news or []

    def fundamentals_sample(self, symbol: str) -> dict[str, Any]:
        ticker = self._ticker(symbol)
        return {"info": ticker.info, "income_statement": ticker.income_stmt.head(10).to_dict(), "balance_sheet": ticker.balance_sheet.head(10).to_dict(), "cashflow": ticker.cashflow.head(10).to_dict()}

    def news_sample(self, symbol: str, *, instrument_id: str | None = None) -> list[NewsItem]:
        instrument_id = instrument_id or (symbol if symbol.endswith(".NS") else f"{symbol}.NS")
        now = datetime.now(timezone.utc)
        return [
            item for item in (
                parse_yfinance_news_item(raw, instrument_ids=[instrument_id], retrieved_at=now)
                for raw in self.get_news_raw(symbol, count=5)
            )
            if item is not None
        ]

    def extract_identifier(self, instrument: Instrument):
        isin = instrument.isin
        yf = _require_yfinance()
        data = yf.Lookup(isin).all
        if len(data) < 1: raise ValueError(f"No ticker with isin {isin} found!")
        if len(data) > 1: print(f"WARNING: Multiple results found for isin {isin}.")
        return data.index[0]


def parse_yfinance_news_item(item: dict[str, Any], *, instrument_ids: list[str], retrieved_at: datetime) -> NewsItem | None:
    if not isinstance(item, dict):
        return None
    content = item.get("content", item)
    if not isinstance(content, dict):
        content = {"title": str(content)}
    title = content.get("title") or item.get("title") or ""
    canonical = content.get("canonicalUrl") or content.get("clickThroughUrl") or {}
    if isinstance(canonical, dict):
        url = canonical.get("url")
    else:
        url = str(canonical) if canonical else item.get("link")
    pub_value = (content.get("pubDate") or content.get("displayTime") or item.get("providerPublishTime"))
    published_at = None
    if isinstance(pub_value, (int, float)):
        published_at = datetime.fromtimestamp(pub_value, tz=timezone.utc)
    elif pub_value:
        try:
            from dateutil.parser import parse
            parsed = parse(str(pub_value))
            published_at = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            published_at = None
    fingerprint = item.get("id") or content.get("id") or url or f"{title}|{published_at}"
    news_id = f"yfinance:{sha256(str(fingerprint).encode('utf-8')).hexdigest()[:32]}"
    provider = content.get("provider") or {}
    source_name = provider.get("displayName") if isinstance(provider, dict) else None
    summary = content.get("summary") or content.get("description") or item.get("summary")
    return NewsItem(
        news_id=news_id,
        instrument_ids=list(instrument_ids),
        title=str(title),
        published_at=published_at,
        url=url,
        text=str(summary) if summary else None,
        source_name=source_name or "Yahoo Finance",
        metadata={"raw": item, "content_type": content.get("contentType"), "provider": provider},
        provenance=Provenance(
            source="yfinance",
            source_type="aggregator",
            source_dataset="Yahoo Finance news",
            retrieved_at=retrieved_at,
            published_at=published_at,
        ),
    )
