from __future__ import annotations

import sys
import types

import pytest

from data_enrichment import (
    BackendComputation,
    BackendRegistry,
    BackendUnavailableError,
    FinanceToolkitBackend,
    PandasTABackend,
    QuantStatsBackend,
    default_backend_registry,
)


def test_backend_metadata_and_default_registry():
    registry = default_backend_registry()
    assert registry.names() == ("financetoolkit", "pandas-ta-classic", "quantstats")
    assert registry.get("financetoolkit").dependency_version == "2.2.1"
    assert registry.get("quantstats").dependency_version == "0.0.86"
    assert registry.get("pandas-ta-classic").dependency_version == "0.8.32"
    descriptions = [registry.get(name).describe() for name in registry.names()]
    assert all("available" in item for item in descriptions)


def test_backend_registry_prefers_explicit_backend():
    registry = BackendRegistry()
    registry.register(PandasTABackend())
    with pytest.raises(ValueError):
        registry.for_capability("risk", preferred="pandas-ta-classic")


def test_financetoolkit_requires_caller_supplied_datasets():
    backend = FinanceToolkitBackend()
    if backend.available():
        pytest.skip("Optional backend installed in test environment")
    with pytest.raises(BackendUnavailableError):
        backend.compute("ratios", {"tickers": ["REL"], "balance": None, "income": None, "cash": None})


def test_financetoolkit_executes_against_custom_data(monkeypatch):
    fake = types.ModuleType("financetoolkit")

    class FakeRatios:
        def collect_all_ratios(self, **kwargs):
            return {"ratio": 1, "kwargs": kwargs}

        def collect_profitability_ratios(self, **kwargs):
            return {"roe": 0.2}

        def collect_solvency_ratios(self, **kwargs):
            return {"debt_to_equity": 0.5}

        def collect_efficiency_ratios(self, **kwargs):
            return {"asset_turnover": 1.2}

        def collect_liquidity_ratios(self, **kwargs):
            return {"current_ratio": 2.0}

        def collect_valuation_ratios(self, **kwargs):
            return {"pe": 18.0}

    class FakeToolkit:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.ratios = FakeRatios()

    fake.Toolkit = FakeToolkit
    monkeypatch.setitem(sys.modules, "financetoolkit", fake)

    data = {"tickers": ["REL"], "balance": "BAL", "income": "INC", "cash": "CASH"}
    backend = FinanceToolkitBackend()
    result = backend.compute("profitability", data)
    assert isinstance(result, BackendComputation)
    assert backend.describe()["available"] is True
    assert result.value == {"roe": 0.2}
    assert result.metadata["data_source_policy"] == "caller_supplied_only"


def test_quantstats_executes_expected_metrics(monkeypatch):
    fake = types.ModuleType("quantstats")

    class FakeStats:
        def cagr(self, returns, rf=0.0):
            return 0.11

        def sharpe(self, returns, rf=0.0, periods=252):
            return 1.5

        def sortino(self, returns, rf=0.0, periods=252):
            return 2.0

        def calmar(self, returns, periods=252):
            return 0.8

        def volatility(self, returns, periods=252):
            return 0.2

        def max_drawdown(self, returns):
            return -0.25

        def skew(self, returns):
            return 0.3

        def kurtosis(self, returns):
            return 4.0

        def value_at_risk(self, returns):
            return -0.03

        def conditional_value_at_risk(self, returns):
            return -0.05

        def ulcer_index(self, returns):
            return 0.1

        def to_drawdown_series(self, returns):
            return returns * 0 - 0.1

        def information_ratio(self, returns, benchmark, prepare_returns=False):
            return 0.4

        def r_squared(self, returns, benchmark, prepare_returns=False):
            return 0.6

        def greeks(self, returns, benchmark, prepare_returns=False):
            return {"beta": 1.1}

    fake.stats = FakeStats()
    monkeypatch.setitem(sys.modules, "quantstats", fake)

    import pandas as pd

    returns = pd.Series([0.01, -0.02, 0.03], index=pd.date_range("2026-01-01", periods=3))
    performance = QuantStatsBackend().compute("performance", returns)
    assert performance.value["sharpe"] == 1.5

    risk = QuantStatsBackend().compute("risk", returns)
    assert risk.value["conditional_value_at_risk"] == -0.05

    benchmark = pd.Series([0.01, -0.01, 0.02], index=returns.index)
    comparison = QuantStatsBackend().compute("benchmark", {"returns": returns, "benchmark": benchmark})
    assert comparison.value["beta"] == 1.1


def test_pandas_ta_classic_executes_indicators(monkeypatch):
    fake = types.ModuleType("pandas_ta_classic")

    def rsi(close, **kwargs):
        return close.rolling(kwargs.get("length", 14)).mean()

    def sma(close, **kwargs):
        return close.rolling(kwargs.get("length", 20)).mean()

    def ema(close, **kwargs):
        return close.ewm(span=kwargs.get("length", 20), adjust=False).mean()

    def macd(close, **kwargs):
        import pandas as pd
        return pd.DataFrame({"MACD": close.diff(), "SIGNAL": close.diff().rolling(2).mean()})

    def bbands(close, **kwargs):
        import pandas as pd
        mid = close.rolling(kwargs.get("length", 20)).mean()
        return pd.DataFrame({"BBL": mid - 1, "BBM": mid, "BBU": mid + 1})

    def atr(high, low, close, **kwargs):
        return (high - low).rolling(kwargs.get("length", 14)).mean()

    def adx(high, low, close, **kwargs):
        import pandas as pd
        return pd.DataFrame({"ADX": (high - low).rolling(kwargs.get("length", 14)).mean()})

    def obv(close, volume, **kwargs):
        return volume.cumsum()

    def stoch(high, low, close, **kwargs):
        import pandas as pd
        return pd.DataFrame({"STOCH": close})

    def willr(high, low, close, **kwargs):
        return -((high - close) / (high - low) * 100)

    def cdl_pattern(**kwargs):
        import pandas as pd
        close = kwargs["close"]
        return pd.DataFrame({"CDL_DOJI": 0}, index=close.index)

    fake.rsi = rsi
    fake.sma = sma
    fake.ema = ema
    fake.macd = macd
    fake.bbands = bbands
    fake.atr = atr
    fake.adx = adx
    fake.obv = obv
    fake.stoch = stoch
    fake.willr = willr
    fake.cdl_pattern = cdl_pattern
    fake.__name__ = "pandas_ta_classic"
    monkeypatch.setitem(sys.modules, "pandas_ta_classic", fake)

    import pandas as pd

    idx = pd.date_range("2026-01-01", periods=5)
    df = pd.DataFrame(
        {
            "open": [9, 10, 11, 12, 13],
            "high": [11, 12, 13, 14, 15],
            "low": [8, 9, 10, 11, 12],
            "close": [10, 11, 12, 13, 14],
            "volume": [100, 110, 120, 130, 140],
        },
        index=idx,
    )
    backend = PandasTABackend()
    assert backend.compute("sma", df, length=3).value.iloc[-1] == pytest.approx(13.0)
    assert list(backend.compute("macd", df).value.columns) == ["MACD", "SIGNAL"]
    assert list(backend.compute("bollinger", df).value.columns) == ["BBL", "BBM", "BBU"]


def test_backend_adapter_delegates_without_changing_contract():
    from data_enrichment import BackendAdapter

    backend = PandasTABackend()
    adapter = BackendAdapter(backend)
    assert adapter.name == backend.name
    assert adapter.available() is False
