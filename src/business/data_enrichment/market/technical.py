"""Deterministic technical indicators used by research workflows."""

from __future__ import annotations

from datetime import datetime, timezone

from ..core.context import EnrichmentContext
from ..core.hashing import stable_id
from ..models import DerivedSeries, DerivedSeriesPoint, DerivedSummary, EnrichmentIssue, EnrichmentResult
from .common import prepare_price_records


def _ema(values: list[float], window: int) -> list[float | None]:
    output: list[float | None] = [None] * len(values)
    if len(values) < window:
        return output
    current = sum(values[:window]) / window
    output[window - 1] = current
    multiplier = 2 / (window + 1)
    for index in range(window, len(values)):
        current = (values[index] - current) * multiplier + current
        output[index] = current
    return output


class TechnicalIndicatorEnricher:
    """Produce RSI and MACD from canonical close observations without a vendor API."""

    name = "market.technical_indicators"
    version = "0.1.0"
    requires = frozenset({"price.close"})
    provides = frozenset({"market.technical_indicators"})

    def __init__(self, rsi_window: int = 14, fast: int = 12, slow: int = 26, signal: int = 9) -> None:
        self.rsi_window, self.fast, self.slow, self.signal = rsi_window, fast, slow, signal

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        prepared = prepare_price_records(context)
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        closes = [item[2] for item in prepared]
        if len(closes) < max(self.rsi_window + 1, self.slow):
            result.issues.append(EnrichmentIssue(code="insufficient_observations", severity="warning", message="RSI/MACD require more close observations.", metric="technical_indicators"))
            return result
        now = datetime.now(timezone.utc)
        rsi_values: list[float | None] = [None] * len(closes)
        gains = [max(closes[index] - closes[index - 1], 0.0) for index in range(1, len(closes))]
        losses = [max(closes[index - 1] - closes[index], 0.0) for index in range(1, len(closes))]
        average_gain = sum(gains[:self.rsi_window]) / self.rsi_window
        average_loss = sum(losses[:self.rsi_window]) / self.rsi_window
        rsi_values[self.rsi_window] = 100.0 if average_loss == 0 else 100 - 100 / (1 + average_gain / average_loss)
        for index in range(self.rsi_window + 1, len(closes)):
            average_gain = (average_gain * (self.rsi_window - 1) + gains[index - 1]) / self.rsi_window
            average_loss = (average_loss * (self.rsi_window - 1) + losses[index - 1]) / self.rsi_window
            rsi_values[index] = 100.0 if average_loss == 0 else 100 - 100 / (1 + average_gain / average_loss)
        fast, slow = _ema(closes, self.fast), _ema(closes, self.slow)
        macd_values = [a - b if a is not None and b is not None else None for a, b in zip(fast, slow)]
        macd_ready = [value for value in macd_values if value is not None]
        signal_ready = _ema(macd_ready, self.signal)
        signal_values: list[float | None] = [None] * (len(closes) - len(macd_ready)) + signal_ready
        def series(metric: str, values: list[float | None]) -> None:
            points = [DerivedSeriesPoint(timestamp=prepared[index][0], value=value, source_record_ids=[context.record_id(prepared[index][1])] if context.record_id(prepared[index][1]) else []) for index, value in enumerate(values) if value is not None]
            result.series.append(DerivedSeries(derived_id=stable_id(self.name, context.instrument_id, metric, [(point.timestamp.isoformat(), point.value) for point in points]), instrument_id=context.instrument_id, metric=metric, unit="index" if metric == "rsi_14" else "price", points=points, lineage=context.lineage_for_records([item[1] for item in prepared], algorithm=self.name, algorithm_version=self.version, parameters={"rsi_window": self.rsi_window, "fast": self.fast, "slow": self.slow, "signal": self.signal}, calculated_at=now)))
        series("rsi_14", rsi_values)
        series("macd", macd_values)
        series("macd_signal", signal_values)
        latest_rsi = next((value for value in reversed(rsi_values) if value is not None), None)
        latest_macd = next((value for value in reversed(macd_values) if value is not None), None)
        latest_signal = next((value for value in reversed(signal_values) if value is not None), None)
        result.summaries.append(DerivedSummary(derived_id=stable_id(self.name, context.instrument_id, latest_rsi, latest_macd, latest_signal), instrument_id=context.instrument_id, summary_type="technical_indicators", values={"rsi_14": latest_rsi, "macd": latest_macd, "macd_signal": latest_signal, "macd_histogram": latest_macd - latest_signal if latest_macd is not None and latest_signal is not None else None}, lineage=context.lineage_for_records([item[1] for item in prepared], algorithm=self.name, algorithm_version=self.version, parameters={})))
        return result
