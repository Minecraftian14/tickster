from datetime import datetime, timezone

from data_collection.collection.results import CollectionResult, RawPayload
from data_collection.domains.models import Instrument, Provenance
from data_foundation.ingest import ingest_collection_results


def test_ingest_builds_identity_and_raw_refs():
    now = datetime.now(timezone.utc)
    instrument = Instrument(instrument_id="I1", isin="INE001", symbol="ABC", exchange="NSE", provenance=Provenance(source="nse", source_type="exchange", retrieved_at=now))
    payload = RawPayload(source="nse", domain="instruments", retrieved_at=now, payload={"ok": 1})
    result = CollectionResult(domain="instruments", records=[instrument], raw_payloads=[payload])
    bundle = ingest_collection_results([result])
    assert bundle.identities[0].instrument_id == "I1"
    assert payload.stable_id() in bundle.raw_refs
