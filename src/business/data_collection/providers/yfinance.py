from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pandas as pd

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
        now = datetime.now(timezone.utc)
        out: list[PriceBar] = []
        for ts, row in df.iterrows():
            observed = pd.Timestamp(ts).to_pydatetime()
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            out.append(PriceBar(
                instrument_id=instrument_id, timestamp=observed, timeframe=interval,
                open=Decimal(str(row["Open"])) if pd.notna(row["Open"]) else None,
                high=Decimal(str(row["High"])) if pd.notna(row["High"]) else None,
                low=Decimal(str(row["Low"])) if pd.notna(row["Low"]) else None,
                close=Decimal(str(row["Close"])) if pd.notna(row["Close"]) else None,
                volume=int(row["Volume"]) if pd.notna(row["Volume"]) else None,
                provenance=Provenance(source="yfinance", source_type="aggregator", source_dataset="Yahoo Finance chart history", retrieved_at=now, observed_at=observed),
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
                out.append(CorporateAction(instrument_id=instrument_id, action_type="dividend", ex_date=ts.date(), amount=Decimal(str(row["Dividends"])), provenance=Provenance(source="yfinance", source_type="aggregator", source_dataset="Yahoo Finance actions", retrieved_at=now, observed_at=ts.to_pydatetime())))
            if "Stock Splits" in row and pd.notna(row["Stock Splits"]) and float(row["Stock Splits"]) != 0:
                out.append(CorporateAction(instrument_id=instrument_id, action_type="stock_split", ex_date=ts.date(), ratio=str(row["Stock Splits"]), provenance=Provenance(source="yfinance", source_type="aggregator", source_dataset="Yahoo Finance actions", retrieved_at=now, observed_at=ts.to_pydatetime())))
        return out

    def fundamentals_sample(self, symbol: str) -> dict[str, Any]:
        ticker = self._ticker(symbol)
        return {"info": ticker.info, "income_statement": ticker.income_stmt.head(10).to_dict(), "balance_sheet": ticker.balance_sheet.head(10).to_dict(), "cashflow": ticker.cashflow.head(10).to_dict()}

    def news_sample(self, symbol: str, *, instrument_id: str | None = None) -> list[NewsItem]:
        ticker = self._ticker(symbol)
        now = datetime.now(timezone.utc)
        instrument_id = instrument_id or (symbol if symbol.endswith(".NS") else f"{symbol}.NS")
        items: list[NewsItem] = []
        for item in (ticker.news or [])[:5]:
            content = item.get("content", item)
            title = content.get("title", "") if isinstance(content, dict) else str(content)
            url = None
            if isinstance(content, dict):
                canonical = content.get("canonicalUrl") or {}
                url = canonical.get("url") if isinstance(canonical, dict) else None
            items.append(NewsItem(news_id=f"yfinance:{instrument_id}:{hash(str(item))}", instrument_ids=[instrument_id], title=title, url=url, source_name="Yahoo Finance", metadata=item, provenance=Provenance(source="yfinance", source_type="aggregator", source_dataset="Yahoo Finance news", retrieved_at=now)))
        return items
