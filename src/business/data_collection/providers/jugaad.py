from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd


class JugaadDataProvider:
    """Adapter for the jugaad-data NSE/RBI Python library."""

    name = "jugaad-data"
    source_type = "open_source_exchange_wrapper"

    @staticmethod
    def _nse_module():
        try:
            from jugaad_data import nse  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "jugaad-data is not installed. Install with: pip install jugaad-data"
            ) from exc
        return nse

    def health(self) -> dict[str, Any]:
        try:
            self._nse_module()
            return {"provider": self.name, "installed": True}
        except Exception as exc:
            return {"provider": self.name, "installed": False, "error": str(exc)}

    def stock_history(self, symbol: str, start: date, end: date, series: str = "EQ") -> pd.DataFrame:
        nse = self._nse_module()
        return nse.stock_df(symbol=symbol, from_date=start, to_date=end, series=series)

    def bhavcopy(self, trading_date: date) -> Any:
        nse = self._nse_module()
        return nse.bhavcopy_save(trading_date, ".")
