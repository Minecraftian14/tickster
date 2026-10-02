from __future__ import annotations

from typing import Any

from .base import BackendComputation, BackendUnavailableError, OptionalBackend


class QuantStatsBackend(OptionalBackend):
    """Execute QuantStats return-series analytics on caller-supplied returns."""

    name = "quantstats"
    version = "0.7.0"
    dependency_name = "quantstats"
    dependency_version = "0.0.86"
    capabilities = frozenset({"performance", "risk", "drawdown", "benchmark"})

    def _module(self):
        try:
            import quantstats  # type: ignore
        except ImportError as exc:
            raise BackendUnavailableError(
                "QuantStats is not installed; install the optional 'quantstats' extra."
            ) from exc
        return quantstats

    def available(self) -> bool:
        try:
            self._module()
        except BackendUnavailableError:
            return False
        return True

    @staticmethod
    def _returns(data: Any):
        try:
            import pandas as pd  # type: ignore
        except ImportError as exc:
            raise BackendUnavailableError("QuantStats backend requires pandas.") from exc
        if isinstance(data, pd.Series):
            returns = data
        elif isinstance(data, dict) and "returns" in data:
            returns = data["returns"]
        else:
            raise TypeError("QuantStats calculations require a pandas Series or {'returns': Series}.")
        if not isinstance(returns, pd.Series):
            returns = pd.Series(returns)
        return returns.dropna()

    def compute(self, capability: str, data: Any, **kwargs: Any) -> BackendComputation:
        if capability not in self.capabilities:
            raise ValueError(f"Unsupported QuantStats capability: {capability}")
        qs = self._module()
        returns = self._returns(data)
        periods = int(kwargs.pop("periods", 252))
        rf = float(kwargs.pop("rf", 0.0))
        stats = qs.stats

        if capability == "performance":
            value = {
                "cagr": stats.cagr(returns, rf=rf),
                "sharpe": stats.sharpe(returns, rf=rf, periods=periods),
                "sortino": stats.sortino(returns, rf=rf, periods=periods),
                "calmar": stats.calmar(returns, periods=periods),
                "volatility": stats.volatility(returns, periods=periods),
                "max_drawdown": stats.max_drawdown(returns),
                "skew": stats.skew(returns),
                "kurtosis": stats.kurtosis(returns),
            }
        elif capability == "risk":
            value = {
                "volatility": stats.volatility(returns, periods=periods),
                "value_at_risk": stats.value_at_risk(returns),
                "conditional_value_at_risk": stats.conditional_value_at_risk(returns),
                "ulcer_index": stats.ulcer_index(returns),
            }
        elif capability == "drawdown":
            value = stats.to_drawdown_series(returns)
        else:
            if not isinstance(data, dict) or "benchmark" not in data:
                raise ValueError("QuantStats benchmark capability requires {'returns': ..., 'benchmark': ...}.")
            benchmark = data["benchmark"]
            greeks = stats.greeks(returns, benchmark, prepare_returns=False)
            if hasattr(greeks, "get"):
                beta = greeks.get("beta")
            elif hasattr(greeks, "loc") and "beta" in getattr(greeks, "index", []):
                beta = greeks.loc["beta"]
            else:
                beta = None
            value = {
                "information_ratio": stats.information_ratio(returns, benchmark, prepare_returns=False),
                "r_squared": stats.r_squared(returns, benchmark, prepare_returns=False),
                "beta": beta,
            }

        parameters = {"periods": periods, "rf": rf, **kwargs}
        return BackendComputation(
            backend=self.name,
            capability=capability,
            value=value,
            backend_version=self.dependency_version,
            parameters=parameters,
            metadata={"input": "caller_supplied_returns"},
        )
