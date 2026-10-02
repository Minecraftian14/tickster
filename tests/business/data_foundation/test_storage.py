from pathlib import Path

from data_collection.domains.models import Instrument, Provenance
from datetime import datetime, timezone
from data_foundation.storage import write_canonical_jsonl, write_manifest


def test_storage_writes_records_and_manifest(tmp_path: Path):
    item = Instrument(instrument_id="I1", symbol="ABC", exchange="NSE", provenance=Provenance(source="nse", source_type="exchange", retrieved_at=datetime.now(timezone.utc)))
    record_path = write_canonical_jsonl([item], tmp_path, domain="instruments")
    manifest_path = write_manifest({"version": "0.1.0"}, tmp_path)
    assert record_path.exists()
    assert manifest_path.exists()
    assert '"instrument_id":"I1"' in record_path.read_text()
