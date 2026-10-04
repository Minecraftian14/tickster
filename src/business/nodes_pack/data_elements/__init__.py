"""
Practical examples for indian-equity-data-enrichment 1.0.0.

Assumptions
-----------
1. data_collection 1.1.0 has already collected source data.
2. data_foundation 1.0.0 has persisted that data.
3. The foundation store is available at ./data/foundation.
4. The target instrument is represented by its canonical instrument_id/ISIN.

The examples deliberately keep source-specific API calls out of this file.
The collection/foundation layers are responsible for producing canonical
records; this file shows how an application consumes those records.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from data_enrichment import (
    # Core framework
    EnrichmentContext,
    # Smallest example
    # Built-in profiles
    # Context packs
    # Optional backends
)
from data_foundation import FoundationStore

FOUNDATION_ROOT = Path("data/foundation")
TARGET = "INE002A01018"  # Example ISIN; replace with your target.
BENCHMARK_ID = "NIFTY_50"
AS_OF = datetime(2026, 9, 30, 15, 30, tzinfo=ZoneInfo("Asia/Kolkata"))


def load_foundation() -> tuple[list[Any], list[Any]]:
    """Load canonical records and evidence from the stable foundation store."""
    store = FoundationStore(str(FOUNDATION_ROOT))
    canonical, observations, _raw = store.load_bundle()
    return canonical, observations


def records_for_instrument(records: list[Any], instrument_id: str) -> list[Any]:
    """Application-level helper for target-company filtering."""
    result: list[Any] = []
    for record in records:
        payload = getattr(record, "payload", {}) or {}
        candidate = getattr(record, "instrument_id", None) or payload.get("instrument_id")
        instrument_ids = getattr(record, "instrument_ids", None) or payload.get("instrument_ids", [])
        if candidate == instrument_id or instrument_id in instrument_ids:
            result.append(record)
    return result


def build_context(
        canonical_records: list[Any],
        source_observations: list[Any],
        *,
        instrument_id: str = TARGET,
        as_of: datetime | None = AS_OF,
        benchmark_records: list[Any] | None = None,
        peer_records: dict[str, list[Any]] | None = None,
        event_records: list[Any] | None = None,
        insider_records: list[Any] | None = None,
        large_deal_records: list[Any] | None = None,
) -> EnrichmentContext:
    """Build the enrichment context.

    The application supplies cross-instrument datasets (benchmark/peers) and
    event-domain overrides in metadata because those datasets are not naturally
    part of the target instrument's own record set.
    """
    target_records = records_for_instrument(canonical_records, instrument_id)

    metadata = {
        "benchmark_id": BENCHMARK_ID,
        "benchmark_records": list(benchmark_records or []),
        "peer_records": peer_records or {},
        "event_records": list(event_records or []),
        "insider_records": list(insider_records or []),
        "large_deal_records": list(large_deal_records or []),
    }

    return EnrichmentContext(
        records=target_records,
        source_observations=source_observations,
        instrument_id=instrument_id,
        as_of=as_of,
        metadata=metadata,
    )


def print_result(result: Any, label: str) -> None:
    print(f"\n=== {label} ===")
    print("enricher:", result.enricher)
    print("version:", result.enricher_version)
    print("observations:", len(result.observations))
    print("series:", len(result.series))
    print("summaries:", len(result.summaries))
    print("issues:", len(result.issues))
    if result.summaries:
        for summary in result.summaries[:3]:
            print("  summary:", summary.summary_type)
            print("  values:", summary.values)
