from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from data_collection.domains.models import CompanyDocument, CorporateAction, Instrument, NewsItem, Provenance
from data_foundation.identity import IdentityAmbiguityError, IdentityRegistry, build_identity, merge_identities
from data_foundation.models import IdentityAlias, InstrumentIdentity
from data_foundation.query import build_temporal_index
from data_foundation.temporal import is_visible_at, temporal_envelope


UTC = timezone.utc


def provenance(source: str = "test", *, published_at: datetime | None = None, observed_at: datetime | None = None) -> Provenance:
    return Provenance(source=source, source_type="test", retrieved_at=datetime(2026, 10, 2, 10, tzinfo=UTC), published_at=published_at, observed_at=observed_at)


def instrument(instrument_id: str, symbol: str, name: str, isin: str) -> Instrument:
    return Instrument(instrument_id=instrument_id, symbol=symbol, name=name, isin=isin, exchange="NSE", provenance=provenance())


def test_identity_adds_name_and_symbol_aliases() -> None:
    identity = build_identity(instrument("i1", "REL", "Reliance Industries", "INE1"))
    types = {(a.alias_type, a.value) for a in identity.aliases}
    assert ("symbol", "REL") in types
    assert ("name", "Reliance Industries") in types
    assert ("isin", "INE1") in types


def test_registry_resolves_company_and_instrument() -> None:
    registry = IdentityRegistry.from_identities(merge_identities([instrument("i1", "REL", "Reliance Industries", "INE1")]))
    assert registry.company.resolve("reliance industries").instrument_id == "i1"
    assert registry.instrument.resolve("REL").instrument_id == "i1"
    assert registry.instrument.aliases("REL", alias_type="isin")[0].value == "INE1"


def test_registry_reports_ambiguity_instead_of_picking_winner() -> None:
    left = InstrumentIdentity(instrument_id="i1", symbol="ABC", aliases=[IdentityAlias(alias_type="symbol", value="ABC", instrument_id="i1")])
    right = InstrumentIdentity(instrument_id="i2", symbol="ABC", aliases=[IdentityAlias(alias_type="symbol", value="ABC", instrument_id="i2")])
    registry = IdentityRegistry.from_identities([left, right])
    with pytest.raises(IdentityAmbiguityError):
        registry.resolve("ABC", alias_types=("symbol",))


def test_alias_validity_is_honored_for_historical_resolution() -> None:
    identities = [
        InstrumentIdentity(
            instrument_id="i1",
            symbol="OLD",
            aliases=[IdentityAlias(alias_type="symbol", value="OLD", instrument_id="i1", valid_to=date(2025, 12, 31))],
        ),
        InstrumentIdentity(
            instrument_id="i2",
            symbol="OLD",
            aliases=[IdentityAlias(alias_type="symbol", value="OLD", instrument_id="i2", valid_from=date(2026, 1, 1))],
        ),
    ]
    registry = IdentityRegistry.from_identities(identities)
    assert registry.resolve("OLD", alias_types=("symbol",), as_of=datetime(2025, 6, 1, tzinfo=UTC)).instrument_id == "i1"
    assert registry.resolve("OLD", alias_types=("symbol",), as_of=datetime(2026, 6, 1, tzinfo=UTC)).instrument_id == "i2"


def test_registry_unknown_returns_none() -> None:
    registry = IdentityRegistry.from_identities([])
    assert registry.company.resolve("NOPE") is None


def test_date_only_publication_is_conservatively_end_of_day() -> None:
    doc = CompanyDocument(
        document_id="d1",
        instrument_id="i1",
        document_type="annual_report",
        title="Annual Report",
        published_at=datetime(2026, 10, 1, 0, tzinfo=UTC),
        provenance=provenance(),
    )
    envelope = temporal_envelope(doc)
    assert envelope.availability_basis == "published"
    assert envelope.available_at == datetime(2026, 10, 1, 0, tzinfo=UTC)


def test_date_only_availability_when_provenance_is_observation_date() -> None:
    action = CorporateAction(
        instrument_id="i1",
        action_type="dividend",
        ex_date=date(2026, 10, 10),
        provenance=provenance(observed_at=datetime(2026, 10, 9, 12, tzinfo=UTC)),
    )
    envelope = temporal_envelope(action)
    assert envelope.availability_basis == "observed"
    assert envelope.available_at == datetime(2026, 10, 9, 12, tzinfo=UTC)


def test_effective_date_alone_does_not_claim_prior_knowledge() -> None:
    action = CorporateAction(
        instrument_id="i1",
        action_type="dividend",
        ex_date=date(2026, 10, 10),
        provenance=provenance(),
    )
    assert not is_visible_at(action, datetime(2026, 10, 9, 23, tzinfo=UTC), strict=True)


def test_temporal_index_what_was_known_at() -> None:
    pub = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
    item = NewsItem(news_id="n1", instrument_ids=["i1"], title="News", published_at=pub, provenance=provenance(published_at=pub))
    later = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    hidden = NewsItem(news_id="n2", instrument_ids=["i1"], title="Later", published_at=later, provenance=provenance(published_at=later))
    identity = InstrumentIdentity(
        instrument_id="i1",
        symbol="REL",
        name="Reliance Industries",
        aliases=[
            IdentityAlias(alias_type="symbol", value="REL", instrument_id="i1"),
            IdentityAlias(alias_type="name", value="Reliance Industries", instrument_id="i1"),
        ],
    )
    index = build_temporal_index([item, hidden], identity_registry=IdentityRegistry.from_identities([identity]))
    known = index.what_was_known_at("REL", datetime(2026, 10, 1, 9, 30, tzinfo=UTC))
    assert [record.news_id for record in known] == ["n1"]


def test_events_between_uses_event_time_and_can_require_availability() -> None:
    pub = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
    action = CorporateAction(
        instrument_id="i1",
        action_type="dividend",
        announcement_date=date(2026, 10, 1),
        provenance=provenance(published_at=pub),
    )
    index = build_temporal_index([action])
    events = index.events_between("i1", datetime(2026, 10, 1, tzinfo=UTC), datetime(2026, 10, 2, tzinfo=UTC))
    assert events == [action]
    assert index.events_between(
        "i1",
        datetime(2026, 10, 1, tzinfo=UTC),
        datetime(2026, 10, 1, 7, 0, tzinfo=UTC),
        require_available_by_end=True,
    ) == []


def test_documents_available_at_filters_document_like_records() -> None:
    pub = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
    doc = CompanyDocument(document_id="d1", instrument_id="i1", document_type="investor_presentation", title="Deck", published_at=pub, provenance=provenance(published_at=pub))
    news = NewsItem(news_id="n1", instrument_ids=["i1"], title="News", published_at=pub, provenance=provenance(published_at=pub))
    index = build_temporal_index([doc, news])
    docs = index.documents_available_at("i1", datetime(2026, 10, 1, 9, 0, tzinfo=UTC))
    assert docs == [doc]


def test_unknown_availability_is_excluded_in_strict_mode() -> None:
    action = CorporateAction(instrument_id="i1", action_type="split", ex_date=date(2026, 10, 10), provenance=provenance())
    index = build_temporal_index([action])
    assert index.what_was_known_at("i1", datetime(2026, 10, 9, tzinfo=UTC), strict=True) == []
    assert index.what_was_known_at("i1", datetime(2026, 10, 9, tzinfo=UTC), strict=False) == [action]


def test_package_version() -> None:
    import data_foundation
    assert data_foundation.__version__ == "1.0.0"
