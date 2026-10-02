from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from typing import Any, Iterable

from ..core.context import EnrichmentContext
from ..market.common import close, prepare_price_records, timestamp


@dataclass(frozen=True)
class AlignedReturn:
    timestamp: datetime
    instrument_return: float
    reference_return: float
    instrument_record_ids: tuple[str, ...]
    reference_record_ids: tuple[str, ...]

    @property
    def excess_return(self) -> float:
        return self.instrument_return - self.reference_return


def records_from_metadata(context: EnrichmentContext, key: str) -> list[Any]:
    value = context.metadata.get(key)
    if value is None:
        return []
    return list(value)


def align_daily_returns(
    instrument_records: Iterable[Any],
    reference_records: Iterable[Any],
) -> list[AlignedReturn]:
    instrument = prepare_price_records_for_reference(instrument_records)
    reference = prepare_price_records_for_reference(reference_records)
    if len(instrument) < 2 or len(reference) < 2:
        return []
    ref_by_day = {ts.date(): (record, price, ts) for ts, record, price in reference}
    inst_prev = None
    aligned: list[AlignedReturn] = []
    for current in instrument:
        if inst_prev is None:
            inst_prev = current
            continue
        current_ref = ref_by_day.get(current[0].date())
        previous_ref = ref_by_day.get(inst_prev[0].date())
        if current_ref is None or previous_ref is None:
            inst_prev = current
            continue
        _, current_ref_price, _ = current_ref
        _, previous_ref_price, _ = previous_ref
        previous_inst_price = inst_prev[2]
        if previous_inst_price <= 0 or previous_ref_price <= 0 or current_ref_price <= 0 or current[2] <= 0:
            inst_prev = current
            continue
        aligned.append(AlignedReturn(
            timestamp=current[0],
            instrument_return=current[2] / previous_inst_price - 1.0,
            reference_return=current_ref_price / previous_ref_price - 1.0,
            instrument_record_ids=tuple(x for x in (EnrichmentContext.record_id(inst_prev[1]), EnrichmentContext.record_id(current[1])) if x),
            reference_record_ids=tuple(x for x in (EnrichmentContext.record_id(previous_ref[0]), EnrichmentContext.record_id(current_ref[0])) if x),
        ))
        inst_prev = current
    return aligned


def prepare_price_records_for_reference(records: Iterable[Any]) -> list[tuple[datetime, Any, float]]:
    prepared = []
    for record in records:
        ts = timestamp(record)
        value = close(record)
        if ts is None or value is None:
            continue
        prepared.append((ts, record, value))
    prepared.sort(key=lambda item: item[0])
    return prepared


def sample_std(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    avg = sum(values) / len(values)
    return sqrt(sum((x - avg) ** 2 for x in values) / (len(values) - 1))


def covariance(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or len(a) < 2:
        return None
    mean_a = sum(a) / len(a)
    mean_b = sum(b) / len(b)
    return sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b)) / (len(a) - 1)


def correlation(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or len(a) < 2:
        return None
    cov = covariance(a, b)
    std_a = sample_std(a)
    std_b = sample_std(b)
    if cov is None or std_a in (None, 0) or std_b in (None, 0):
        return None
    return cov / (std_a * std_b)


def beta(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or len(a) < 2:
        return None
    cov = covariance(a, b)
    var_b = covariance(b, b)
    if cov is None or var_b in (None, 0):
        return None
    return cov / var_b
