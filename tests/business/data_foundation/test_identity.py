from datetime import datetime, timezone

from data_collection.domains.models import Instrument, Provenance
from data_foundation.identity import build_alias_index, merge_identities, resolve_instrument_id


def prov(source="test"):
    return Provenance(source=source, source_type="fixture", retrieved_at=datetime.now(timezone.utc))


def test_merge_identities_collects_aliases():
    a = Instrument(instrument_id="I1", isin="INE001", symbol="ABC", exchange="NSE", instrument_key="NSE_EQ|ABC", provenance=prov("a"))
    b = Instrument(instrument_id="I1", isin="INE001", symbol="ABC", exchange="NSE", exchange_token="123", provenance=prov("b"))
    identities = merge_identities([a, b])
    assert len(identities) == 1
    index = build_alias_index(identities)
    assert resolve_instrument_id(index, isin="INE001") == "I1"
    assert resolve_instrument_id(index, exchange_token="123") == "I1"
