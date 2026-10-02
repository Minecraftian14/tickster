from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSeries, DerivedSeriesPoint, DerivedSummary, EnrichmentIssue, EnrichmentResult
from ..market.common import as_float, prepare_price_records


def _percentile(values: list[float], current: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return 50.0
    below = sum(1 for value in ordered if value < current)
    equal = sum(1 for value in ordered if value == current)
    return 100.0 * (below + 0.5 * equal) / len(ordered)


def _sample_std(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    avg = sum(values) / len(values)
    return math.sqrt(sum((value - avg) ** 2 for value in values) / (len(values) - 1))


def _returns(prepared: list[tuple[datetime, Any, float]]) -> tuple[list[float], list[Any]]:
    values: list[float] = []
    records: list[Any] = []
    for previous, current in zip(prepared, prepared[1:]):
        if previous[2] <= 0 or current[2] <= 0:
            continue
        values.append(current[2] / previous[2] - 1.0)
        records.append(current[1])
    return values, records


def _sma(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _slope(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    return (values[-1] - values[0]) / (len(values) - 1)


def _maximum_drawdown(values: list[float]) -> float | None:
    if not values:
        return None
    peak = values[0]
    minimum = 0.0
    for value in values:
        if value > peak:
            peak = value
        if peak > 0:
            minimum = min(minimum, value / peak - 1.0)
    return minimum


class HistoricalStateSummaryEnricher:
    """Compress long price histories into descriptive, multi-horizon state summaries."""

    name = "regime.historical_state"
    version = "0.6.0"
    requires = frozenset({"price.close"})
    provides = frozenset({"regime.historical_state"})

    def __init__(self, horizons: tuple[tuple[str, int], ...] = (("1y", 252), ("3y", 756), ("5y", 1260), ("10y", 2520))) -> None:
        self.horizons = tuple(horizons)

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        prepared = prepare_price_records(context)
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if len(prepared) < 2:
            result.issues.append(EnrichmentIssue(code="insufficient_observations", severity="warning", message="At least two closes are required."))
            return result

        closes = [item[2] for item in prepared]
        returns, _ = _returns(prepared)
        calculated_at = datetime.now(timezone.utc)
        for label, lookback in self.horizons:
            window = prepared[-lookback:] if len(prepared) > lookback else prepared
            window_closes = [item[2] for item in window]
            window_returns, _ = _returns(window)
            if len(window_closes) < 2:
                continue
            span_days = max((window[-1][0] - window[0][0]).days, 0)
            start = window_closes[0]
            end = window_closes[-1]
            cumulative = end / start - 1.0 if start > 0 else None
            cagr = None
            if cumulative is not None and start > 0 and end > 0 and span_days >= 365:
                years = span_days / 365.2425
                cagr = (end / start) ** (1.0 / years) - 1.0
            vol = None
            sample_vol = _sample_std(window_returns)
            if sample_vol is not None:
                vol = sample_vol * math.sqrt(252)
            values = {
                "observations": len(window_closes),
                "calendar_span_days": span_days,
                "start_close": start,
                "end_close": end,
                "cumulative_return": cumulative,
                "annualized_return": cagr,
                "annualized_volatility": vol,
                "positive_return_fraction": (sum(1 for value in window_returns if value > 0) / len(window_returns)) if window_returns else None,
                "best_period_return": max(window_returns) if window_returns else None,
                "worst_period_return": min(window_returns) if window_returns else None,
                "maximum_drawdown": _maximum_drawdown(window_closes),
            }
            result.summaries.append(DerivedSummary(
                derived_id=stable_id(self.name, context.instrument_id, label, values),
                instrument_id=context.instrument_id,
                summary_type=f"historical_state_{label}",
                values=values,
                lineage=context.lineage_for_records([item[1] for item in window], algorithm=self.name, algorithm_version=self.version, parameters={"horizon": label, "observations": lookback}, calculated_at=calculated_at),
                metadata={"horizon": label, "uses_all_available_when_shorter": True},
            ))

        latest = prepared[-1]
        price_percentile_1y = _percentile(closes[-min(len(closes), 252):], latest[2])
        if returns:
            latest_return = returns[-1]
            return_1y = returns[-min(len(returns), 252):]
            return_pct = _percentile(return_1y, latest_return)
        else:
            return_pct = None
        result.summaries.append(DerivedSummary(
            derived_id=stable_id(self.name, context.instrument_id, "percentiles", price_percentile_1y, return_pct),
            instrument_id=context.instrument_id,
            summary_type="historical_percentiles",
            values={
                "current_close": latest[2],
                "close_percentile_1y": price_percentile_1y,
                "latest_return_1p": returns[-1] if returns else None,
                "latest_return_percentile_1y": return_pct,
            },
            lineage=context.lineage_for_records([item[1] for item in prepared], algorithm=self.name, algorithm_version=self.version, parameters={"percentile_window": 252}, calculated_at=calculated_at),
            metadata={"percentile_definition": "midrank_percentile"},
        ))
        return result


class TrendRegimeEnricher:
    """Describe the current price trend using moving-average relationships and slopes."""

    name = "regime.trend_state"
    version = "0.6.0"
    requires = frozenset({"price.close"})
    provides = frozenset({"regime.trend_state"})

    def __init__(self, short_window: int = 20, medium_window: int = 50, long_window: int = 200, slope_window: int = 20) -> None:
        if min(short_window, medium_window, long_window, slope_window) <= 0:
            raise ValueError("all windows must be positive")
        self.short_window = short_window
        self.medium_window = medium_window
        self.long_window = long_window
        self.slope_window = slope_window

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        prepared = prepare_price_records(context)
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if not prepared:
            result.issues.append(EnrichmentIssue(code="no_observations", severity="warning", message="No valid closes are available."))
            return result
        closes = [item[2] for item in prepared]
        current = closes[-1]
        sma_short = _sma(closes[-self.short_window:]) if len(closes) >= self.short_window else None
        sma_medium = _sma(closes[-self.medium_window:]) if len(closes) >= self.medium_window else None
        sma_long = _sma(closes[-self.long_window:]) if len(closes) >= self.long_window else None
        short_slope = _slope(closes[-self.slope_window:]) if len(closes) >= self.slope_window else None
        long_slope = _slope(closes[-min(self.long_window, len(closes)):]) if len(closes) >= self.long_window else None

        state = "insufficient_history"
        if sma_medium is not None and short_slope is not None:
            if sma_long is not None and long_slope is not None and current > sma_medium > sma_long and short_slope > 0 and long_slope >= 0:
                state = "strong_up"
            elif current > sma_medium and short_slope > 0:
                state = "up"
            elif sma_long is not None and long_slope is not None and current < sma_medium < sma_long and short_slope < 0 and long_slope <= 0:
                state = "strong_down"
            elif current < sma_medium and short_slope < 0:
                state = "down"
            else:
                state = "neutral"

        values = {
            "state": state,
            "current_close": current,
            "sma_short": sma_short,
            "sma_medium": sma_medium,
            "sma_long": sma_long,
            "short_slope_per_observation": short_slope,
            "long_slope_per_observation": long_slope,
            "above_short": current > sma_short if sma_short is not None else None,
            "above_medium": current > sma_medium if sma_medium is not None else None,
            "above_long": current > sma_long if sma_long is not None else None,
        }
        result.summaries.append(DerivedSummary(
            derived_id=stable_id(self.name, context.instrument_id, values),
            instrument_id=context.instrument_id,
            summary_type="trend_state",
            values=values,
            lineage=context.lineage_for_records([item[1] for item in prepared], algorithm=self.name, algorithm_version=self.version, parameters={"short_window": self.short_window, "medium_window": self.medium_window, "long_window": self.long_window, "slope_window": self.slope_window}),
            metadata={"classification_is_descriptive": True, "state_definitions": {"strong_up": "close > medium SMA > long SMA with positive short and non-negative long slope", "up": "close > medium SMA with positive short slope", "neutral": "does not satisfy up/down conditions", "down": "close < medium SMA with negative short slope", "strong_down": "close < medium SMA < long SMA with negative short and non-positive long slope"}},
        ))
        return result


class VolatilityRegimeEnricher:
    """Characterize current realized volatility relative to the security's own history."""

    name = "regime.volatility_state"
    version = "0.6.0"
    requires = frozenset({"price.close"})
    provides = frozenset({"regime.volatility_state"})

    def __init__(self, volatility_window: int = 20, history_window: int = 252) -> None:
        if volatility_window <= 1 or history_window <= volatility_window:
            raise ValueError("history_window must exceed volatility_window > 1")
        self.volatility_window = volatility_window
        self.history_window = history_window

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        prepared = prepare_price_records(context)
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if len(prepared) < self.volatility_window + 1:
            result.issues.append(EnrichmentIssue(code="insufficient_observations", severity="warning", message="Not enough closes for the requested volatility window."))
            return result
        returns, return_records = _returns(prepared)
        history: list[float] = []
        points: list[DerivedSeriesPoint] = []
        for index in range(self.volatility_window, len(returns) + 1):
            window_returns = returns[index - self.volatility_window:index]
            vol = _sample_std(window_returns)
            if vol is None:
                continue
            annualized = vol * math.sqrt(252)
            history.append(annualized)
            points.append(DerivedSeriesPoint(timestamp=prepared[index][0], value=annualized, source_record_ids=[context.record_id(return_records[index - 1])] if context.record_id(return_records[index - 1]) else []))
        if not history:
            result.issues.append(EnrichmentIssue(code="no_valid_volatility", severity="warning", message="No valid realized-volatility observations could be calculated."))
            return result
        current = history[-1]
        comparison = history[-min(len(history), self.history_window):]
        percentile = _percentile(comparison, current)
        if percentile is None:
            state = "unknown"
        elif percentile < 20:
            state = "low"
        elif percentile > 80:
            state = "high"
        else:
            state = "normal"
        series_lineage_records = [record for _, record, _ in prepared]
        result.series.append(DerivedSeries(
            derived_id=stable_id(self.name, context.instrument_id, self.volatility_window, [(p.timestamp.isoformat(), p.value) for p in points]),
            instrument_id=context.instrument_id,
            metric=f"realized_volatility_{self.volatility_window}p_regime", 
            unit="annualized-fraction",
            points=points,
            lineage=context.lineage_for_records(series_lineage_records, algorithm=self.name, algorithm_version=self.version, parameters={"volatility_window": self.volatility_window, "history_window": self.history_window}),
            metadata={"classification_is_relative": True},
        ))
        result.summaries.append(DerivedSummary(
            derived_id=stable_id(self.name, context.instrument_id, current, percentile, state),
            instrument_id=context.instrument_id,
            summary_type="volatility_state",
            values={"current_annualized_volatility": current, "historical_percentile": percentile, "state": state, "history_observations": len(comparison)},
            lineage=context.lineage_for_records(series_lineage_records, algorithm=self.name, algorithm_version=self.version, parameters={"volatility_window": self.volatility_window, "history_window": self.history_window}),
            metadata={"state_thresholds": {"low": "<20th percentile", "normal": "20th-80th percentile", "high": ">80th percentile"}},
        ))
        return result


class ExtremesRegimeEnricher:
    """Describe current distance from historical extremes and elapsed time since them."""

    name = "regime.extremes"
    version = "0.6.0"
    requires = frozenset({"price.close"})
    provides = frozenset({"regime.extremes"})

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        prepared = prepare_price_records(context)
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if not prepared:
            result.issues.append(EnrichmentIssue(code="no_observations", severity="warning", message="No valid closes are available."))
            return result
        peak = max(prepared, key=lambda item: item[2])
        trough = min(prepared, key=lambda item: item[2])
        current = prepared[-1]
        peak_distance = current[2] / peak[2] - 1.0 if peak[2] > 0 else None
        trough_distance = current[2] / trough[2] - 1.0 if trough[2] > 0 else None
        values = {
            "current_close": current[2],
            "all_time_high": peak[2],
            "all_time_high_timestamp": peak[0],
            "distance_from_all_time_high": peak_distance,
            "time_since_all_time_high_days": max((current[0] - peak[0]).days, 0),
            "all_time_low": trough[2],
            "all_time_low_timestamp": trough[0],
            "distance_from_all_time_low": trough_distance,
            "time_since_all_time_low_days": max((current[0] - trough[0]).days, 0),
        }
        result.summaries.append(DerivedSummary(
            derived_id=stable_id(self.name, context.instrument_id, values),
            instrument_id=context.instrument_id,
            summary_type="historical_extremes",
            values=values,
            lineage=context.lineage_for_records([item[1] for item in prepared], algorithm=self.name, algorithm_version=self.version, parameters={}),
        ))
        return result


class PersistenceRegimeEnricher:
    """Describe persistence of positive returns and moving-average/trend states."""

    name = "regime.persistence"
    version = "0.6.0"
    requires = frozenset({"price.close"})
    provides = frozenset({"regime.persistence"})

    def __init__(self, ma_window: int = 200) -> None:
        if ma_window <= 1:
            raise ValueError("ma_window must be greater than 1")
        self.ma_window = ma_window

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        prepared = prepare_price_records(context)
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        if len(prepared) < 2:
            result.issues.append(EnrichmentIssue(code="insufficient_observations", severity="warning", message="At least two closes are required."))
            return result
        closes = [item[2] for item in prepared]
        returns, _ = _returns(prepared)
        positive_days = sum(1 for value in returns if value > 0)
        negative_days = sum(1 for value in returns if value < 0)

        current_positive_streak = 0
        for value in reversed(returns):
            if value > 0:
                current_positive_streak += 1
            else:
                break
        current_negative_streak = 0
        for value in reversed(returns):
            if value < 0:
                current_negative_streak += 1
            else:
                break

        def max_streak(predicate) -> int:
            best = run = 0
            for value in returns:
                if predicate(value):
                    run += 1
                    best = max(best, run)
                else:
                    run = 0
            return best

        ma_points = []
        if len(closes) >= self.ma_window:
            for idx in range(self.ma_window - 1, len(closes)):
                avg = _sma(closes[idx + 1 - self.ma_window:idx + 1])
                ma_points.append(current := (closes[idx] > avg if avg else False))
        values = {
            "positive_return_fraction": positive_days / len(returns) if returns else None,
            "negative_return_fraction": negative_days / len(returns) if returns else None,
            "current_positive_streak": current_positive_streak,
            "current_negative_streak": current_negative_streak,
            "maximum_positive_streak": max_streak(lambda value: value > 0),
            "maximum_negative_streak": max_streak(lambda value: value < 0),
            "fraction_above_ma": sum(1 for item in ma_points if item) / len(ma_points) if ma_points else None,
            "current_above_ma": ma_points[-1] if ma_points else None,
            "ma_window": self.ma_window,
        }
        result.summaries.append(DerivedSummary(
            derived_id=stable_id(self.name, context.instrument_id, values),
            instrument_id=context.instrument_id,
            summary_type="historical_persistence",
            values=values,
            lineage=context.lineage_for_records([item[1] for item in prepared], algorithm=self.name, algorithm_version=self.version, parameters={"ma_window": self.ma_window}),
        ))
        return result
