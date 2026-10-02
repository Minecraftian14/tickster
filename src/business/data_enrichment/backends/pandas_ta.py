from __future__ import annotations

from typing import Any

from .base import BackendComputation, BackendUnavailableError, OptionalBackend


class PandasTABackend(OptionalBackend):
    """Execute pandas-ta-classic indicators on caller-supplied OHLCV data."""

    name = "pandas-ta-classic"
    version = "0.7.0"
    dependency_name = "pandas-ta-classic"
    dependency_version = "0.8.32"
    capabilities = frozenset({
        "sma", "ema", "rsi", "macd", "bollinger", "atr", "adx", "obv", "stoch", "willr", "candles", "strategy",
    })

    def _module(self):
        try:
            import pandas_ta_classic as ta  # type: ignore
            return ta
        except ImportError:
            try:
                import pandas_ta as ta  # type: ignore
                return ta
            except ImportError as exc:
                raise BackendUnavailableError(
                    "pandas-ta-classic is not installed; install the optional 'pandas-ta' extra."
                ) from exc

    def available(self) -> bool:
        try:
            self._module()
        except BackendUnavailableError:
            return False
        return True

    @staticmethod
    def _frame(data: Any):
        try:
            import pandas as pd  # type: ignore
        except ImportError as exc:
            raise BackendUnavailableError("pandas-ta-classic backend requires pandas.") from exc
        if isinstance(data, pd.DataFrame):
            frame = data.copy()
        elif isinstance(data, dict):
            frame = pd.DataFrame(data)
        else:
            raise TypeError("pandas-ta-classic calculations require a pandas DataFrame or a column mapping.")
        frame.columns = [str(col).lower() for col in frame.columns]
        return frame

    def compute(self, capability: str, data: Any, **kwargs: Any) -> BackendComputation:
        if capability not in self.capabilities:
            raise ValueError(f"Unsupported pandas-ta-classic capability: {capability}")
        ta = self._module()
        frame = self._frame(data)
        params = dict(kwargs)

        close = frame.get("close")
        high = frame.get("high")
        low = frame.get("low")
        volume = frame.get("volume")
        if capability in {"sma", "ema", "rsi", "macd", "bollinger", "stoch", "willr"} and close is None:
            raise ValueError(f"{capability} requires a 'close' column.")
        if capability in {"atr", "adx"} and any(x is None for x in (high, low, close)):
            raise ValueError(f"{capability} requires 'high', 'low', and 'close' columns.")
        if capability == "obv" and any(x is None for x in (close, volume)):
            raise ValueError("obv requires 'close' and 'volume' columns.")
        if capability == "candles" and any(x is None for x in (frame.get("open"), high, low, close)):
            raise ValueError("candles requires 'open', 'high', 'low', and 'close' columns.")

        if capability == "sma":
            value = ta.sma(close, **params)
        elif capability == "ema":
            value = ta.ema(close, **params)
        elif capability == "rsi":
            value = ta.rsi(close, **params)
        elif capability == "macd":
            value = ta.macd(close, **params)
        elif capability == "bollinger":
            value = ta.bbands(close, **params)
        elif capability == "atr":
            value = ta.atr(high=high, low=low, close=close, **params)
        elif capability == "adx":
            value = ta.adx(high=high, low=low, close=close, **params)
        elif capability == "obv":
            value = ta.obv(close=close, volume=volume, **params)
        elif capability == "stoch":
            value = ta.stoch(high=high, low=low, close=close, **params)
        elif capability == "willr":
            value = ta.willr(high=high, low=low, close=close, **params)
        elif capability == "candles":
            names = params.pop("name", "all")
            value = ta.cdl_pattern(open_=frame.get("open"), high=high, low=low, close=close, name=names, **params)
        else:
            strategy = params.pop("strategy")
            value = frame.ta.strategy(strategy, **params)

        return BackendComputation(
            backend=self.name,
            capability=capability,
            value=value,
            backend_version=self.dependency_version,
            parameters=kwargs,
            metadata={"input": "caller_supplied_ohlcv", "backend_module": getattr(ta, "__name__", self.name)},
        )
