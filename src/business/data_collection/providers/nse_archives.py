from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
from typing import Any

import pandas as pd

from data_collection.domains.models import Instrument, PriceBar, Provenance


class NSEArchivesProvider:
    """Adapter for the optional ``nse-archives`` package."""

    name = "nse"
    source_type = "primary_exchange"

    @staticmethod
    def _nse():
        try:
            from nse_archives import NSEArchive  # type: ignore
        except ImportError as exc:
            raise RuntimeError("nse-archives is not installed. Install with: pip install nse-archives") from exc
        return NSEArchive()

    def health(self) -> dict[str, Any]:
        try:
            nse = self._nse()
            datasets = nse.list_datasets()
            return {"provider": self.name, "installed": True, "datasets": len(datasets)}
        except Exception as exc:
            return {"provider": self.name, "installed": False, "error": str(exc)}

    def daily_equities_with_delivery(self, trading_date: date) -> pd.DataFrame:
        return self._nse().get("capital_market", "equities_sme", "sec_bhavdata_full", trading_date.isoformat())

    def daily_equity_bhavcopy(self, trading_date: date) -> pd.DataFrame:
        return self._nse().get("capital_market", "equities_sme", "bhavcopy_pr", trading_date.isoformat())

    def corporate_actions(self, trading_date: date) -> pd.DataFrame:
        return self._nse().get("capital_market", "equities_sme", "corp_actions", trading_date.isoformat())

    def announcements(self, trading_date: date) -> pd.DataFrame:
        return self._nse().get("capital_market", "equities_sme", "announcements", trading_date.isoformat())

    def board_meetings(self, trading_date: date) -> pd.DataFrame:
        return self._nse().get("capital_market", "equities_sme", "board_meetings", trading_date.isoformat())

    def market_cap(self, trading_date: date) -> pd.DataFrame:
        return self._nse().get("capital_market", "equities_sme", "mcap", trading_date.isoformat())

    def index_daily_close(self, trading_date: date) -> pd.DataFrame:
        return self._nse().get("capital_market", "indices", "ind_close_all", trading_date.isoformat())

    def index_valuation(self, trading_date: date) -> pd.DataFrame:
        return self._nse().get("capital_market", "indices", "pe", trading_date.isoformat())

    def bulk_deals(self, trading_date: date) -> pd.DataFrame:
        return self._nse().get("capital_market", "equities_sme", "bulk_deals", trading_date.isoformat())

    def block_deals(self, trading_date: date) -> pd.DataFrame:
        return self._nse().get("capital_market", "equities_sme", "block_deals", trading_date.isoformat())

    def short_selling(self, trading_date: date) -> pd.DataFrame:
        return self._nse().get("capital_market", "equities_sme", "short_selling", trading_date.isoformat())


    @staticmethod
    def normalize_equity_daily(frame: pd.DataFrame, *, instrument: Instrument | None, symbol: str, instrument_id: str, trading_date: date) -> list[PriceBar]:
        if frame is None or frame.empty:
            return []
        df = frame.copy()
        aliases = {str(c).strip().upper(): c for c in df.columns}

        def col(*names: str):
            for name in names:
                if name.upper() in aliases:
                    return aliases[name.upper()]
            return None

        symbol_col = col("SYMBOL", "SYMBOL_NAME")
        if symbol_col:
            df = df[df[symbol_col].astype(str).str.upper() == symbol.upper()]
        if df.empty:
            return []
        row = df.iloc[0]

        def raw(*names):
            c = col(*names)
            return None if c is None else row[c]

        def decimal(*names):
            value = raw(*names)
            if value is None or pd.isna(value):
                return None
            return Decimal(str(value))

        def integer(*names):
            value = raw(*names)
            if value is None or pd.isna(value):
                return None
            return int(float(value))

        observed = datetime.combine(trading_date, time.min, tzinfo=ZoneInfo("Asia/Kolkata"))
        now = datetime.now(timezone.utc)
        return [PriceBar(
            instrument_id=instrument_id, timestamp=observed, timeframe="1d",
            open=decimal("OPEN_PRICE", "OPEN"), high=decimal("HIGH_PRICE", "HIGH"),
            low=decimal("LOW_PRICE", "LOW"), close=decimal("CLOSE_PRICE", "CLOSE"),
            volume=integer("TTL_TRD_QNTY", "VOLUME"),
            turnover=decimal("TURNOVER_LACS", "TURNOVER"),
            delivery_quantity=integer("DELIV_QTY", "DELIVERY_QUANTITY"),
            delivery_percent=decimal("DELIV_PER", "DELIVERY_PERCENT"),
            provenance=Provenance(source="nse", source_type="primary_exchange", source_dataset="sec_bhavdata_full", retrieved_at=now, observed_at=observed),
        )]
