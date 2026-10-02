from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from data_collection.collection.results import CollectionResult
from data_collection.domains.models import Instrument

from .identity import merge_identities
from .models import CanonicalBundle, DataQuality, Relationship
from .persistence import canonicalize_record, observation_set_for_records
from .relationships import make_relationship


def _records(result: CollectionResult[Any]) -> Iterable[Any]:
    yield from result.records
    yield from result.related_records


def ingest_collection_results(results: Iterable[CollectionResult[Any]]) -> CanonicalBundle:
    """Turn one or more collection results into a queryable foundation bundle.

    Collection remains responsible for fetching/source-specific parsing. This
    function only indexes the resulting canonical records and raw references.
    """
    results = list(results)

    records: list[Any] = []
    instruments: list[Instrument] = []
    raw_refs: list[str] = []
    quality: list[DataQuality] = []
    relationships: list[Relationship] = []
    canonical_records = []
    source_observations = []

    for result in results:
        result_records = list(_records(result))
        records.extend(result_records)
        result_observations = observation_set_for_records(result_records, domain=result.domain)
        source_observations.extend(result_observations)
        observations_by_record = {}
        for observation in result_observations:
            observations_by_record.setdefault(observation.canonical_record_id, []).append(observation.observation_id)
        for item in result_records:
            if isinstance(item, Instrument):
                instruments.append(item)
            provenance = getattr(item, "provenance", None)
            if provenance and provenance.raw_ref:
                raw_refs.append(provenance.raw_ref)
            instrument_id = getattr(item, "instrument_id", None)
            record_id = next((getattr(item, key, None) for key in ("event_id", "filing_id", "document_id", "news_id") if getattr(item, key, None)), None)
            if instrument_id and record_id:
                relationships.append(make_relationship(record_id, "relates_to_instrument", instrument_id, source=getattr(provenance, "source", None), evidence_ids=[getattr(provenance, "raw_ref")] if getattr(provenance, "raw_ref", None) else []))
            canonical_records.append(canonicalize_record(item, domain=result.domain, source_observation_ids=observations_by_record.get(canonicalize_record(item, domain=result.domain).record_id, [])))
        for payload in result.raw_payloads:
            raw_refs.append(payload.stable_id())
        for issue in result.issues:
            quality.append(DataQuality(status="parse_failed", message=issue.get("message"), source=issue.get("source"), field=issue.get("operation")))
        for error in result.errors:
            quality.append(DataQuality(status="source_unavailable", message=error.get("error"), source=error.get("source"), field=error.get("operation")))

    identities = merge_identities(instruments)
    return CanonicalBundle(
        instruments=instruments,
        records=records,
        raw_refs=sorted(set(raw_refs)),
        identities=identities,
        canonical_records=canonical_records,
        source_observations=source_observations,
        relationships=relationships,
        quality=quality,
        metadata={"result_count": len(results)},
    )
