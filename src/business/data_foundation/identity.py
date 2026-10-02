from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from data_collection.domains.models import Instrument

from .models import IdentityAlias, InstrumentIdentity


class IdentityAmbiguityError(ValueError):
    """Raised when an alias resolves to multiple canonical instruments."""

    def __init__(self, query: str, candidates: Sequence[str]) -> None:
        self.query = query
        self.candidates = tuple(candidates)
        super().__init__(f"Ambiguous identity '{query}'; candidates: {', '.join(self.candidates)}")


def _norm(value: Any) -> str:
    return str(value).strip().upper()


def _add_alias(
    out: list[IdentityAlias],
    *,
    alias_type: str,
    value: Any,
    instrument_id: str,
    source: str | None = None,
    valid_from: Any = None,
    valid_to: Any = None,
) -> None:
    if value is None:
        return
    text = str(value).strip()
    if not text:
        return
    candidate = IdentityAlias(
        alias_type=alias_type,
        value=text,
        instrument_id=instrument_id,
        source=source,
        valid_from=valid_from,
        valid_to=valid_to,
    )
    key = (candidate.alias_type, _norm(candidate.value), candidate.source, candidate.valid_from, candidate.valid_to)
    if not any((a.alias_type, _norm(a.value), a.source, a.valid_from, a.valid_to) == key for a in out):
        out.append(candidate)


def build_identity(instrument: Instrument) -> InstrumentIdentity:
    source = instrument.provenance.source
    aliases: list[IdentityAlias] = []
    valid_from = getattr(instrument, "valid_from", None)
    valid_to = getattr(instrument, "valid_to", None)
    _add_alias(aliases, alias_type="isin", value=instrument.isin, instrument_id=instrument.instrument_id, source=source, valid_from=valid_from, valid_to=valid_to)
    _add_alias(aliases, alias_type="symbol", value=instrument.symbol, instrument_id=instrument.instrument_id, source=source, valid_from=valid_from, valid_to=valid_to)
    _add_alias(aliases, alias_type="name", value=instrument.name, instrument_id=instrument.instrument_id, source=source, valid_from=valid_from, valid_to=valid_to)
    _add_alias(aliases, alias_type="short_name", value=instrument.short_name, instrument_id=instrument.instrument_id, source=source, valid_from=valid_from, valid_to=valid_to)
    _add_alias(aliases, alias_type="instrument_key", value=instrument.instrument_key, instrument_id=instrument.instrument_id, source=source, valid_from=valid_from, valid_to=valid_to)
    _add_alias(aliases, alias_type="exchange_token", value=instrument.exchange_token, instrument_id=instrument.instrument_id, source=source, valid_from=valid_from, valid_to=valid_to)
    return InstrumentIdentity(
        instrument_id=instrument.instrument_id,
        isin=instrument.isin,
        symbol=instrument.symbol,
        exchange=instrument.exchange,
        name=instrument.name,
        active=instrument.active,
        aliases=aliases,
        metadata={"series": instrument.series, "security_type": instrument.security_type},
    )


def merge_identities(instruments: Iterable[Instrument]) -> list[InstrumentIdentity]:
    grouped: dict[str, list[Instrument]] = defaultdict(list)
    for item in instruments:
        grouped[item.instrument_id].append(item)

    merged: list[InstrumentIdentity] = []
    for instrument_id, group in grouped.items():
        group_sorted = sorted(
            group,
            key=lambda x: (
                x.provenance.observed_at or x.provenance.published_at or x.provenance.retrieved_at,
                sum(v is not None for v in [x.isin, x.name, x.instrument_key, x.exchange_token, x.sector, x.industry]),
            ),
            reverse=True,
        )
        head = build_identity(group_sorted[0])
        aliases = list(head.aliases)
        for item in group:
            for alias in build_identity(item).aliases:
                if not any(
                    (a.alias_type, _norm(a.value), a.source, a.valid_from, a.valid_to)
                    == (alias.alias_type, _norm(alias.value), alias.source, alias.valid_from, alias.valid_to)
                    for a in aliases
                ):
                    aliases.append(alias)
        head.aliases = aliases
        merged.append(head)
    return sorted(merged, key=lambda x: x.instrument_id)


def build_alias_index(identities: Iterable[InstrumentIdentity]) -> dict[tuple[str, str], str]:
    """Build a strict index for aliases that are unique across the identity set.

    Historical callers expecting a dict still receive one. Ambiguous aliases are
    intentionally omitted; ``IdentityRegistry`` below retains the full candidate set.
    """
    candidates: dict[tuple[str, str], set[str]] = defaultdict(set)
    for identity in identities:
        for alias in identity.aliases:
            candidates[(alias.alias_type, _norm(alias.value))].add(identity.instrument_id)
    return {key: next(iter(values)) for key, values in candidates.items() if len(values) == 1}


def resolve_instrument_id(
    alias_index: dict[tuple[str, str], str],
    *,
    isin: str | None = None,
    symbol: str | None = None,
    instrument_key: str | None = None,
    exchange_token: str | None = None,
    name: str | None = None,
) -> str | None:
    for alias_type, value in (
        ("isin", isin),
        ("instrument_key", instrument_key),
        ("exchange_token", exchange_token),
        ("symbol", symbol),
        ("name", name),
    ):
        if value:
            resolved = alias_index.get((alias_type, _norm(value)))
            if resolved:
                return resolved
    return None



def _alias_active_at(alias: IdentityAlias, as_of: Any) -> bool:
    if as_of is None:
        return True
    # Normalize date/datetime comparisons by comparing datetimes when possible.
    from datetime import date, datetime, time, timezone

    def dt(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, date):
            return datetime.combine(value, time.min, tzinfo=timezone.utc)
        return None

    point = dt(as_of)
    start = dt(alias.valid_from)
    end = dt(alias.valid_to)
    if point is None:
        return True
    if start is not None and point < start:
        return False
    if end is not None and point > end:
        return False
    return True

@dataclass(frozen=True)
class Resolution:
    query: str
    instrument_id: str
    alias: IdentityAlias


class IdentityRegistry:
    """Queryable identity registry built from canonical instrument identities."""

    def __init__(self, identities: Iterable[InstrumentIdentity] = ()) -> None:
        self._identities = {identity.instrument_id: identity for identity in identities}
        self._candidates: dict[tuple[str, str], set[str]] = defaultdict(set)
        self._aliases: dict[tuple[str, str, str], list[IdentityAlias]] = defaultdict(list)
        for identity in self._identities.values():
            for alias in identity.aliases:
                key = (alias.alias_type, _norm(alias.value))
                self._candidates[key].add(identity.instrument_id)
                self._aliases[(identity.instrument_id, alias.alias_type, _norm(alias.value))].append(alias)

        self.company = _CompanyResolver(self)
        self.instrument = _InstrumentResolver(self)

    @classmethod
    def from_identities(cls, identities: Iterable[InstrumentIdentity]) -> "IdentityRegistry":
        return cls(identities)

    def add(self, identity: InstrumentIdentity) -> None:
        self.__init__(list(self._identities.values()) + [identity])

    def identity(self, instrument_id: str) -> InstrumentIdentity | None:
        return self._identities.get(instrument_id)

    def candidates(self, query: str, *, alias_types: Sequence[str] | None = None) -> list[str]:
        normalized = _norm(query)
        types = set(alias_types) if alias_types else None
        found: set[str] = set()
        for (alias_type, value), ids in self._candidates.items():
            if value == normalized and (types is None or alias_type in types):
                found.update(ids)
        return sorted(found)

    def resolve(self, query: str, *, alias_types: Sequence[str] | None = None, as_of: Any = None) -> Resolution | None:
        normalized = _norm(query)
        candidate_keys = [
            (alias_type, normalized)
            for alias_type in (alias_types or ("isin", "instrument_key", "exchange_token", "symbol", "name", "short_name"))
            if (alias_type, normalized) in self._candidates
        ]
        candidate_ids: list[str] = []
        for key in candidate_keys:
            alias_type, _ = key
            for instrument_id in sorted(self._candidates[key]):
                identity = self._identities[instrument_id]
                if any(a.alias_type == alias_type and _norm(a.value) == normalized and _alias_active_at(a, as_of) for a in identity.aliases):
                    candidate_ids.append(instrument_id)
        candidate_ids = list(dict.fromkeys(candidate_ids))
        if not candidate_ids:
            return None
        if len(candidate_ids) > 1:
            raise IdentityAmbiguityError(query, candidate_ids)
        instrument_id = candidate_ids[0]
        identity = self._identities[instrument_id]
        aliases = [a for a in identity.aliases if _norm(a.value) == normalized and (not alias_types or a.alias_type in alias_types) and _alias_active_at(a, as_of)]
        return Resolution(query=query, instrument_id=instrument_id, alias=aliases[0])

    def aliases(self, instrument: str, *, alias_type: str | None = None, as_of: Any = None) -> list[IdentityAlias]:
        resolved = self.resolve(instrument, as_of=as_of)
        if resolved is None:
            identity = self._identities.get(instrument)
        else:
            identity = self._identities.get(resolved.instrument_id)
        if identity is None:
            return []
        aliases = [alias for alias in identity.aliases if _alias_active_at(alias, as_of)]
        if alias_type is None:
            return aliases
        return [alias for alias in aliases if alias.alias_type == alias_type]

    def all_identities(self) -> list[InstrumentIdentity]:
        return sorted(self._identities.values(), key=lambda item: item.instrument_id)


class _CompanyResolver:
    def __init__(self, registry: IdentityRegistry) -> None:
        self._registry = registry

    def resolve(self, query: str, *, as_of: Any = None) -> Resolution | None:
        return self._registry.resolve(query, alias_types=("isin", "symbol", "name", "short_name"), as_of=as_of)


class _InstrumentResolver:
    def __init__(self, registry: IdentityRegistry) -> None:
        self._registry = registry

    def aliases(self, instrument: str, *, alias_type: str | None = None, as_of: Any = None) -> list[IdentityAlias]:
        return self._registry.aliases(instrument, alias_type=alias_type, as_of=as_of)

    def resolve(self, query: str) -> Resolution | None:
        return self._registry.resolve(query)
