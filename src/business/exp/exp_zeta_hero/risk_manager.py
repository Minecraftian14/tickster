from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf

from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState, history_item


PRICE_COLUMNS = ["open", "close", "high", "low", "volume", "time"]


def get_prices(
        ticker: yf.Ticker,
        start_date: str,
        end_date: str,
) -> pd.DataFrame:
    empty = pd.DataFrame(columns=PRICE_COLUMNS)

    try:
        end_dt = dt.datetime.strptime(end_date, "%Y-%m-%d") + dt.timedelta(days=1)
        history = ticker.history(
            start=start_date,
            end=end_dt.strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=False,
        )
        if history.empty:
            return empty

        prices = pd.DataFrame(index=history.index)
        prices["open"] = pd.to_numeric(history["Open"], errors="coerce")
        prices["close"] = pd.to_numeric(history["Close"], errors="coerce")
        prices["high"] = pd.to_numeric(history["High"], errors="coerce")
        prices["low"] = pd.to_numeric(history["Low"], errors="coerce")
        prices["volume"] = pd.to_numeric(history["Volume"], errors="coerce")

        # Keep the output timestamp format consistent and avoid timezone issues.
        prices["time"] = [
            pd.Timestamp(index).strftime("%Y-%m-%dT00:00:00Z")
            for index in prices.index
        ]
        prices = prices[PRICE_COLUMNS].dropna(subset=["close"]).reset_index(drop=True)
        if prices.empty:
            return empty
        prices["volume"] = prices["volume"].fillna(0).astype("int64")
        return prices
    except Exception:
        # Return a consistent schema on invalid dates, provider errors, or
        # missing columns. The caller will mark the ticker as having no data.
        return empty


def calculate_volatility_metrics(
        prices_df: pd.DataFrame,
        lookback_days: int = 60,
) -> dict[str, Any]:
    close = pd.to_numeric(prices_df.get("close", pd.Series(dtype=float)), errors="coerce")
    daily_returns = close.pct_change().replace([np.inf, -np.inf], np.nan).dropna()

    if daily_returns.empty:
        return {
            "daily_volatility": None,
            "annualized_volatility": None,
            "volatility_percentile": None,
            "data_points": 0,
            "lookback_days": 0,
        }

    recent_returns = daily_returns.tail(min(lookback_days, len(daily_returns)))
    daily_vol = float(recent_returns.std(ddof=1)) if len(recent_returns) >= 2 else None
    annualized_vol = (
        float(daily_vol * np.sqrt(252)) if daily_vol is not None else None
    )

    # Compare the latest lookback volatility with the distribution of historical
    # 30-session rolling volatilities. A percentile is only meaningful with
    # enough observations to form a rolling distribution.
    percentile = None
    if len(daily_returns) >= 30 and daily_vol is not None:
        rolling_vol = daily_returns.rolling(window=30).std().dropna()
        if not rolling_vol.empty:
            percentile = float((rolling_vol <= daily_vol).mean() * 100)

    return {
        "daily_volatility": daily_vol,
        "annualized_volatility": annualized_vol,
        "volatility_percentile": percentile,
        "data_points": int(len(recent_returns)),
        "lookback_days": int(min(lookback_days, len(daily_returns))),
    }


def calculate_volatility_adjusted_limit(annualized_volatility: float) -> float:
    base_limit = 0.20

    if annualized_volatility < 0.15:
        multiplier = 1.25
    elif annualized_volatility < 0.30:
        multiplier = 1.0 - (annualized_volatility - 0.15) * 0.5
    elif annualized_volatility < 0.50:
        multiplier = 0.75 - (annualized_volatility - 0.30) * 0.5
    else:
        multiplier = 0.50

    multiplier = max(0.25, min(1.25, multiplier))
    return float(base_limit * multiplier)


def calculate_correlation_multiplier(avg_correlation: float) -> float:
    if avg_correlation >= 0.80:
        return 0.70
    if avg_correlation >= 0.60:
        return 0.85
    if avg_correlation >= 0.40:
        return 1.00
    if avg_correlation >= 0.20:
        return 1.05
    return 1.10


@workflow_node
def risk_manager(state: WorkflowState) -> WorkflowState:
    assert "message" in state and "reference" in state

    tickers: yf.Tickers = state["reference"]["output"]
    start_date = state["message"]["start_date"]
    end_date = state["message"]["end_date"]

    risk_analysis: dict[str, dict[str, Any]] = {}
    current_prices: dict[str, float] = {}
    volatility_data: dict[str, dict[str, Any]] = {}
    returns_by_ticker: dict[str, pd.Series] = {}

    for ticker_name in tickers.symbols:
        ticker = tickers.tickers[ticker_name]
        prices = get_prices(ticker, start_date, end_date)

        if prices.empty:
            risk_analysis[ticker_name] = {
                "status": "insufficient_data",
                "current_price": None,
                "volatility_metrics": {
                    "daily_volatility": None,
                    "annualized_volatility": None,
                    "volatility_percentile": None,
                    "data_points": 0,
                    "lookback_days": 0,
                },
                "correlation_metrics": {
                    "average_correlation": None,
                    "maximum_correlation": None,
                    "top_correlated_tickers": [],
                },
                "reasoning": {
                    "error": "No price history returned by yfinance for the requested dates."
                },
            }
            continue

        current_price = float(prices["close"].iloc[-1])
        current_prices[ticker_name] = current_price
        vol_metrics = calculate_volatility_metrics(prices)
        volatility_data[ticker_name] = vol_metrics

        daily_returns = prices["close"].pct_change().replace(
            [np.inf, -np.inf], np.nan
        ).dropna()
        if not daily_returns.empty:
            times = pd.to_datetime(prices.loc[daily_returns.index, "time"], errors="coerce")
            daily_returns.index = times
            returns_by_ticker[ticker_name] = daily_returns

        annualized_vol = vol_metrics["annualized_volatility"]
        indicative_limit_pct = (
            calculate_volatility_adjusted_limit(annualized_vol)
            if annualized_vol is not None
            else None
        )

        risk_analysis[ticker_name] = {
            "status": "ok" if annualized_vol is not None else "insufficient_data",
            "current_price": current_price,
            "volatility_metrics": vol_metrics,
            "correlation_metrics": {
                "average_correlation": None,
                "maximum_correlation": None,
                "top_correlated_tickers": [],
            },
            "risk_metrics": {
                "volatility_adjusted_allocation_pct": indicative_limit_pct,
                "correlation_multiplier": 1.0,
                "combined_relative_allocation_pct": indicative_limit_pct,
            },
            "reasoning": {
                "price_observation_count": int(len(prices)),
                "return_observation_count": int(len(daily_returns)),
                "period_start": start_date,
                "period_end": end_date,
                "method": (
                    "Historical close-to-close returns; daily volatility is sample "
                    "standard deviation; annualized volatility uses sqrt(252)."
                ),
            },
        }

    correlation_matrix = None
    if len(returns_by_ticker) >= 2:
        returns_df = pd.concat(returns_by_ticker, axis=1, join="inner").dropna(how="any")
        if returns_df.shape[1] >= 2 and returns_df.shape[0] >= 5:
            correlation_matrix = returns_df.corr()

    if correlation_matrix is not None:
        for ticker_name in correlation_matrix.columns:
            others = correlation_matrix.loc[ticker_name].drop(labels=[ticker_name]).dropna()
            if others.empty or ticker_name not in risk_analysis:
                continue

            avg_corr = float(others.mean())
            max_corr = float(others.max())
            top_correlated = [
                {"ticker": str(name), "correlation": float(value)}
                for name, value in others.sort_values(ascending=False).head(3).items()
            ]
            corr_multiplier = calculate_correlation_multiplier(avg_corr)

            risk_metrics = risk_analysis[ticker_name].get("risk_metrics", {})
            base_pct = risk_metrics.get("volatility_adjusted_allocation_pct")
            combined_pct = (
                float(base_pct * corr_multiplier) if base_pct is not None else None
            )

            risk_analysis[ticker_name]["correlation_metrics"] = {
                "average_correlation": avg_corr,
                "maximum_correlation": max_corr,
                "top_correlated_tickers": top_correlated,
            }
            risk_analysis[ticker_name]["risk_metrics"] = {
                **risk_metrics,
                "correlation_multiplier": corr_multiplier,
                "combined_relative_allocation_pct": combined_pct,
            }

    result = {
        "risk_analysis": risk_analysis,
        "current_prices": current_prices,
        "volatility_data": volatility_data,
        "correlation_matrix": (
            correlation_matrix.to_dict()
            if correlation_matrix is not None
            else None
        ),
    }

    return history_item('risk_manager', result)
