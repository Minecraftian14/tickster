from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pandas as pd


class NSEArchivesProvider:
    """Adapter for the nse-archives package (public NSE archive datasets)."""

    name = "nse-archives"
    source_type = "open_source_exchange_archive_wrapper"

    @staticmethod
    def _nse():
        try:
            from nsedata import nse  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "nse-archives is not installed. Install with: pip install -e '.[nse]'"
            ) from exc
        return nse

    def health(self) -> dict[str, Any]:
        try:
            nse = self._nse()
            return {"provider": self.name, "installed": True, "datasets": len(nse.list_datasets())}
        except Exception as exc:
            return {"provider": self.name, "installed": False, "error": str(exc)}

    def daily_equities_with_delivery(self, trading_date: date) -> pd.DataFrame:
        nse = self._nse()
        return nse.get(
            "capital_market", "equities_sme", "sec_bhavdata_full", trading_date.isoformat()
        )

    def daily_equity_bhavcopy(self, trading_date: date) -> pd.DataFrame:
        nse = self._nse()
        return nse.get(
            "capital_market", "equities_sme", "bhavcopy_pr", trading_date.isoformat()
        )

    def corporate_actions(self, trading_date: date) -> pd.DataFrame:
        nse = self._nse()
        return nse.get(
            "capital_market", "equities_sme", "corp_actions", trading_date.isoformat()
        )

    def announcements(self, trading_date: date) -> pd.DataFrame:
        nse = self._nse()
        return nse.get(
            "capital_market", "equities_sme", "announcements", trading_date.isoformat()
        )

    def board_meetings(self, trading_date: date) -> pd.DataFrame:
        nse = self._nse()
        return nse.get(
            "capital_market", "equities_sme", "board_meetings", trading_date.isoformat()
        )

    def market_cap(self, trading_date: date) -> pd.DataFrame:
        nse = self._nse()
        return nse.get(
            "capital_market", "equities_sme", "mcap", trading_date.isoformat()
        )

    def security_master(self) -> pd.DataFrame:
        nse = self._nse()
        # Dataset availability/name is intentionally discovered through the library catalog
        # rather than hard-coded here until our source-lab confirms the stable dataset key.
        datasets = nse.list_datasets()
        if hasattr(datasets, "to_dict"):
            rows = datasets.to_dict("records")
        else:
            rows = list(datasets)
        candidates = [
            r for r in rows
            if "security" in str(r).lower() and "master" in str(r).lower()
        ]
        raise NotImplementedError(
            "Security-master dataset key should be selected from nse.list_datasets() in the source laboratory. "
            f"Candidates found: {candidates[:5]}"
        )

    @staticmethod
    def _retrieved_at() -> datetime:
        return datetime.now(timezone.utc)
