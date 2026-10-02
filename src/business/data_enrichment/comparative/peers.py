from __future__ import annotations

from datetime import datetime, timezone
from math import sqrt
from typing import Any, Mapping

from ..core.hashing import stable_id
from ..core.context import EnrichmentContext
from ..market.common import prepare_price_records
from ..models import DerivedSummary, EnrichmentIssue, EnrichmentResult


class PeerReturnComparisonEnricher:
    """Compare the instrument's return horizons with a supplied peer set."""

    name = "comparative.peer_returns"
    version = "0.4.0"
    requires = frozenset({"price.close", "peer.close"})
    provides = frozenset({"comparative.peer_performance"})

    def __init__(self, *, horizons: tuple[int, ...] = (21, 63, 126, 252)) -> None:
        self.horizons = horizons

    def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        peers = _normalize_peer_records(context.metadata.get("peer_records"))
        result = EnrichmentResult(enricher=self.name, enricher_version=self.version)
        target = prepare_price_records(context)
        if len(target) < 2:
            result.issues.append(EnrichmentIssue(code="insufficient_target_history", severity="warning", message="At least two target closes are required for peer return comparison."))
            return result
        peer_returns: dict[str, dict[int, float]] = {}
        peer_source_records: list[Any] = []
        for peer_id, records in peers.items():
            prepared = prepare_price_records_for_peer(records)
            peer_source_records.extend(r for _, r, _ in prepared)
            if len(prepared) < 2:
                continue
            peer_returns[peer_id] = {}
            for horizon in self.horizons:
                if len(prepared) > horizon and prepared[-1][2] > 0 and prepared[-1 - horizon][2] > 0:
                    peer_returns[peer_id][horizon] = prepared[-1][2] / prepared[-1 - horizon][2] - 1.0
        if not peer_returns:
            result.issues.append(EnrichmentIssue(code="no_peer_history", severity="warning", message="No peer has enough price history for comparison."))
            return result

        target_values: dict[str, Any] = {"peer_count": len(peer_returns)}
        for horizon in self.horizons:
            if len(target) > horizon and target[-1][2] > 0 and target[-1 - horizon][2] > 0:
                target_return = target[-1][2] / target[-1 - horizon][2] - 1.0
            else:
                target_return = None
            peers_h = [metrics[horizon] for metrics in peer_returns.values() if horizon in metrics]
            target_values[f"target_return_{horizon}p"] = target_return
            target_values[f"peer_observations_{horizon}p"] = len(peers_h)
            if target_return is None or not peers_h:
                target_values[f"peer_mean_{horizon}p"] = None
                target_values[f"peer_median_{horizon}p"] = None
                target_values[f"peer_min_{horizon}p"] = None
                target_values[f"peer_max_{horizon}p"] = None
                target_values[f"target_percentile_{horizon}p"] = None
                target_values[f"excess_vs_peer_median_{horizon}p"] = None
                target_values[f"peer_zscore_{horizon}p"] = None
                continue
            sorted_values = sorted(peers_h)
            mean = sum(sorted_values) / len(sorted_values)
            median = _median(sorted_values)
            std = _sample_std(sorted_values)
            less_equal = sum(1 for value in sorted_values if value <= target_return)
            target_values[f"peer_mean_{horizon}p"] = mean
            target_values[f"peer_median_{horizon}p"] = median
            target_values[f"peer_min_{horizon}p"] = sorted_values[0]
            target_values[f"peer_max_{horizon}p"] = sorted_values[-1]
            target_values[f"target_percentile_{horizon}p"] = less_equal / len(sorted_values)
            target_values[f"excess_vs_peer_median_{horizon}p"] = target_return - median
            target_values[f"peer_zscore_{horizon}p"] = (target_return - mean) / std if std not in (None, 0) else None

        source_records = [x[1] for x in target] + peer_source_records
        result.summaries.append(DerivedSummary(
            derived_id=stable_id(self.name, context.instrument_id, target_values),
            instrument_id=context.instrument_id,
            summary_type="peer_return_comparison",
            values=target_values,
            lineage=context.lineage_for_records(source_records, algorithm=self.name, algorithm_version=self.version, parameters={"peer_ids": sorted(peer_returns), "horizons": self.horizons}, calculated_at=datetime.now(timezone.utc)),
            metadata={"peer_ids": sorted(peer_returns)},
        ))
        return result


def _normalize_peer_records(value: Any) -> dict[str, list[Any]]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return {str(peer_id): list(records) for peer_id, records in value.items()}
    result: dict[str, list[Any]] = {}
    for item in value:
        if isinstance(item, tuple) and len(item) == 2:
            peer_id, records = item
            result[str(peer_id)] = list(records)
        elif isinstance(item, Mapping) and "instrument_id" in item and "records" in item:
            result[str(item["instrument_id"])] = list(item["records"])
    return result


def prepare_price_records_for_peer(records: list[Any]):
    prepared = []
    for record in records:
        rid = EnrichmentContext.instrument_id(record)
        if rid is None:
            # A peer payload can still omit instrument_id; peer_id is the grouping key.
            pass
        from ..market.common import timestamp, close
        ts = timestamp(record)
        value = close(record)
        if ts is not None and value is not None:
            prepared.append((ts, record, value))
    prepared.sort(key=lambda item: item[0])
    return prepared


def _median(values: list[float]) -> float:
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2.0


def _sample_std(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    return sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))
