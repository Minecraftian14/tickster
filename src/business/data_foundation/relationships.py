from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import re
from typing import Any, Iterable

from .models import GraphNode, Relationship, RelationshipGraph


def _norm(value: Any) -> str:
    return str(value).strip().upper()


def _slug(value: Any) -> str:
    text = _norm(value)
    return re.sub(r"[^A-Z0-9]+", "_", text).strip("_") or "UNKNOWN"


def relationship_id(subject_id: str, predicate: str, object_id: str, *, valid_from: Any = None, valid_to: Any = None) -> str:
    body = repr((subject_id, predicate, object_id, valid_from, valid_to)).encode()
    return sha256(body).hexdigest()


def make_relationship(
    subject_id: str,
    predicate: str,
    object_id: str,
    *,
    source: str | None = None,
    evidence_ids: Iterable[str] = (),
    valid_from: Any = None,
    valid_to: Any = None,
    metadata: dict[str, Any] | None = None,
) -> Relationship:
    return Relationship(
        relationship_id=relationship_id(subject_id, predicate, object_id, valid_from=valid_from, valid_to=valid_to),
        subject_id=subject_id,
        predicate=predicate,
        object_id=object_id,
        source=source,
        evidence_ids=sorted(set(evidence_ids)),
        valid_from=valid_from,
        valid_to=valid_to,
        asserted_at=datetime.now(timezone.utc),
        metadata=metadata or {},
    )


def index_relationships(edges: Iterable[Relationship]) -> dict[str, list[Relationship]]:
    by_subject: dict[str, list[Relationship]] = {}
    for edge in edges:
        by_subject.setdefault(edge.subject_id, []).append(edge)
    for values in by_subject.values():
        values.sort(key=lambda item: (item.predicate, item.object_id, item.relationship_id))
    return by_subject


class RelationshipIndex:
    """Queryable in-memory index over a factual relationship graph."""

    def __init__(self, relationships: Iterable[Relationship] = ()) -> None:
        self.relationships = list(relationships)
        self._outgoing: dict[str, list[Relationship]] = defaultdict(list)
        self._incoming: dict[str, list[Relationship]] = defaultdict(list)
        for edge in self.relationships:
            self._outgoing[edge.subject_id].append(edge)
            self._incoming[edge.object_id].append(edge)
        for values in (*self._outgoing.values(), *self._incoming.values()):
            values.sort(key=lambda item: (item.predicate, item.object_id, item.relationship_id))

    @classmethod
    def from_graph(cls, graph: RelationshipGraph) -> "RelationshipIndex":
        return cls(graph.relationships)

    def outgoing(self, subject_id: str, *, predicate: str | None = None) -> list[Relationship]:
        values = self._outgoing.get(subject_id, [])
        if predicate is None:
            return list(values)
        return [edge for edge in values if edge.predicate == predicate]

    def incoming(self, object_id: str, *, predicate: str | None = None) -> list[Relationship]:
        values = self._incoming.get(object_id, [])
        if predicate is None:
            return list(values)
        return [edge for edge in values if edge.predicate == predicate]

    def neighbors(self, entity_id: str, *, predicate: str | None = None) -> list[str]:
        values = self.outgoing(entity_id, predicate=predicate) + self.incoming(entity_id, predicate=predicate)
        return sorted({
            edge.object_id if edge.subject_id == entity_id else edge.subject_id
            for edge in values
        })

    def subjects(self) -> list[str]:
        return sorted(self._outgoing)

    def objects(self) -> list[str]:
        return sorted(self._incoming)


def _record_id(record: Any) -> str | None:
    direct = getattr(record, "record_id", None)
    if direct:
        return str(direct)
    for key in (
        "event_id", "asset_id", "filing_id", "document_id", "news_id", "index_id",
        "observation_id", "relationship_id", "series_id", "instrument_id",
    ):
        value = getattr(record, key, None)
        if value:
            return str(value)
    payload = getattr(record, "payload", None)
    if isinstance(payload, dict):
        for key in (
            "event_id", "asset_id", "filing_id", "document_id", "news_id", "index_id",
            "observation_id", "relationship_id", "series_id", "instrument_id",
        ):
            value = payload.get(key)
            if value:
                return str(value)
    return None


def _record_type(record: Any) -> str:
    value = getattr(record, "record_type", None)
    if value:
        return str(value)
    return record.__class__.__name__


def _payload(record: Any) -> dict[str, Any]:
    value = getattr(record, "payload", None)
    return value if isinstance(value, dict) else {}


def _instrument_ids(record: Any) -> list[str]:
    values: list[str] = []
    direct = getattr(record, "instrument_id", None) or _payload(record).get("instrument_id")
    if direct:
        values.append(str(direct))
    for value in (getattr(record, "instrument_ids", None) or _payload(record).get("instrument_ids") or []):
        if value:
            values.append(str(value))
    return list(dict.fromkeys(values))


def _index_info(record: Any) -> tuple[str | None, str | None]:
    payload = _payload(record)
    index_id = getattr(record, "index_id", None) or payload.get("index_id")
    index_symbol = getattr(record, "index_symbol", None) or payload.get("index_symbol")
    return (str(index_id) if index_id else None, str(index_symbol) if index_symbol else None)


def _source(record: Any) -> str | None:
    provenance = getattr(record, "provenance", None)
    return getattr(provenance, "source", None) or getattr(record, "source", None)


def _evidence_ids(record: Any) -> list[str]:
    evidence: list[str] = []
    provenance = getattr(record, "provenance", None)
    raw_ref = getattr(provenance, "raw_ref", None) or getattr(record, "raw_ref", None)
    if raw_ref:
        evidence.append(str(raw_ref))
    evidence.extend(str(value) for value in getattr(record, "source_observation_ids", None) or [])
    return sorted(set(evidence))


def _node(node_id: str, node_type: str, label: str, *, instrument_id: str | None = None, metadata: dict[str, Any] | None = None) -> GraphNode:
    return GraphNode(node_id=node_id, node_type=node_type, label=label, instrument_id=instrument_id, metadata=metadata or {})


def build_relationship_graph(records: Iterable[Any], *, include_data_records: bool = True) -> RelationshipGraph:
    """Build a deterministic graph from collected/canonical records.

    The builder only establishes explicit factual relationships implied by the
    record schema. It performs no semantic inference.
    """
    records = list(records)
    nodes: dict[str, GraphNode] = {}
    relationships: dict[str, Relationship] = {}

    def add_node(node: GraphNode) -> None:
        existing = nodes.get(node.node_id)
        if existing is None:
            nodes[node.node_id] = node
            return
        # Keep graph construction input-order independent: richer labels/metadata win.
        label = existing.label
        if label == existing.node_id and node.label != node.node_id:
            label = node.label
        metadata = dict(existing.metadata)
        metadata.update(node.metadata)
        nodes[node.node_id] = existing.model_copy(update={"label": label, "metadata": metadata})

    def add_edge(edge: Relationship) -> None:
        existing = relationships.get(edge.relationship_id)
        if existing is None:
            relationships[edge.relationship_id] = edge
            return
        evidence = sorted(set(existing.evidence_ids).union(edge.evidence_ids))
        sources = sorted({value for value in (existing.source, edge.source) if value})
        source = sources[0] if len(sources) == 1 else ("multiple" if sources else None)
        metadata = dict(existing.metadata)
        metadata.update(edge.metadata)
        if len(sources) > 1:
            metadata["sources"] = sources
        relationships[edge.relationship_id] = existing.model_copy(update={
            "evidence_ids": evidence,
            "source": source,
            "metadata": metadata,
        })

    record_predicate = {
        "PriceBar": "has_price_observation",
        "MarketQuote": "has_market_quote",
        "FundamentalSnapshot": "has_financial_snapshot",
        "CompanyPeer": "has_peer",
        "ShareholdingSnapshot": "has_shareholding",
        "CorporateAction": "has_corporate_action",
        "CompanyEvent": "has_event",
        "InsiderTransaction": "has_insider_transaction",
        "LargeDeal": "has_large_deal",
        "Filing": "has_filing",
        "CompanyDocument": "has_document",
        "DocumentAsset": "has_document_asset",
        "XBRLFact": "has_xbrl_fact",
        "NewsItem": "has_news",
        "SectorClassification": "has_classification",
        "IndexSnapshot": "has_index_snapshot",
        "IndexPriceBar": "has_index_price",
        "IndexValuationSnapshot": "has_index_valuation",
        "MacroObservation": "has_macro_observation",
        "RegulatoryItem": "has_regulatory_item",
        "RegulatoryDocument": "has_regulatory_document",
        "MacroSeries": "has_macro_series",
        "MacroRelease": "has_macro_release",
    }

    for record in records:
        rtype = _record_type(record)
        rid = _record_id(record)
        instruments = _instrument_ids(record)
        source = _source(record)
        evidence = _evidence_ids(record)

        if rtype == "Instrument":
            iid = getattr(record, "instrument_id", None) or _payload(record).get("instrument_id")
            if iid:
                label = getattr(record, "name", None) or getattr(record, "symbol", None) or str(iid)
                add_node(_node(f"instrument:{iid}", "instrument", str(label), instrument_id=str(iid)))
                add_node(_node(f"company:{iid}", "company", str(label), instrument_id=str(iid)))
                add_edge(make_relationship(
                    f"company:{iid}", "has_instrument", f"instrument:{iid}",
                    source=source, evidence_ids=evidence,
                ))
            continue

        if rtype == "IndexConstituent":
            index_id, index_symbol = _index_info(record)
            if index_id and instruments:
                add_node(_node(f"index:{index_id}", "index", index_symbol or index_id))
                for iid in instruments:
                    add_node(_node(f"instrument:{iid}", "instrument", iid, instrument_id=iid))
                    add_edge(make_relationship(
                        f"index:{index_id}", "contains_instrument", f"instrument:{iid}",
                        source=source, evidence_ids=evidence,
                        valid_from=getattr(record, "effective_date", None) or _payload(record).get("effective_date"),
                        metadata={"index_symbol": index_symbol},
                    ))
            continue

        if rtype in {"IndexSnapshot", "IndexPriceBar", "IndexValuationSnapshot"}:
            index_id, index_symbol = _index_info(record)
            if rid and index_id:
                add_node(_node(f"index:{index_id}", "index", index_symbol or index_id))
                if include_data_records:
                    object_id = f"record:{rtype}:{rid}"
                    add_node(_node(object_id, "record", rid, metadata={"record_type": rtype}))
                    add_edge(make_relationship(
                        f"index:{index_id}", "has_index_record", object_id,
                        source=source, evidence_ids=evidence,
                    ))
            continue

        if rtype == "CompanyDocument":
            iid = instruments[0] if instruments else None
            if iid and rid:
                add_node(_node(f"company:{iid}", "company", iid, instrument_id=iid))
                object_id = f"document:{rid}"
                add_node(_node(object_id, "document", getattr(record, "title", None) or rid, instrument_id=iid, metadata={"document_type": getattr(record, "document_type", None)}))
                add_edge(make_relationship(f"company:{iid}", "has_document", object_id, source=source, evidence_ids=evidence))
            continue

        if rtype == "Filing":
            if rid:
                iid = instruments[0] if instruments else None
                object_id = f"filing:{rid}"
                add_node(_node(object_id, "filing", getattr(record, "filing_type", None) or rid, instrument_id=iid))
                if iid:
                    add_node(_node(f"company:{iid}", "company", iid, instrument_id=iid))
                    add_edge(make_relationship(f"company:{iid}", "has_filing", object_id, source=source, evidence_ids=evidence))
                for asset_id in getattr(record, "assets", None) or _payload(record).get("assets") or []:
                    asset_node = f"document_asset:{asset_id}"
                    add_node(_node(asset_node, "document_asset", asset_id, instrument_id=iid))
                    add_edge(make_relationship(object_id, "has_document_asset", asset_node, source=source, evidence_ids=evidence))
            continue

        if rtype == "DocumentAsset":
            if rid:
                iid = instruments[0] if instruments else None
                object_id = f"document_asset:{rid}"
                add_node(_node(object_id, "document_asset", getattr(record, "title", None) or rid, instrument_id=iid))
                filing_id = getattr(record, "filing_id", None)
                if filing_id:
                    add_node(_node(f"filing:{filing_id}", "filing", str(filing_id), instrument_id=iid))
                    add_edge(make_relationship(f"filing:{filing_id}", "has_document_asset", object_id, source=source, evidence_ids=evidence))
                elif iid:
                    add_edge(make_relationship(f"company:{iid}", "has_document_asset", object_id, source=source, evidence_ids=evidence))
            continue

        if rtype in {"RegulatoryItem", "RegulatoryDocument"} and rid:
            node_prefix = "regulatory" if rtype == "RegulatoryItem" else "regulatory_document"
            object_id = f"{node_prefix}:{rid}"
            add_node(_node(object_id, node_prefix, getattr(record, "title", None) or rid))
            if rtype == "RegulatoryDocument" and getattr(record, "regulatory_id", None):
                parent = f"regulatory:{record.regulatory_id}"
                add_node(_node(parent, "regulatory", str(record.regulatory_id)))
                add_edge(make_relationship(parent, "has_document", object_id, source=source, evidence_ids=evidence))
            else:
                for iid in getattr(record, "instrument_ids", None) or _payload(record).get("instrument_ids") or []:
                    add_node(_node(f"company:{iid}", "company", iid, instrument_id=iid))
                    add_edge(make_relationship(f"company:{iid}", "has_regulatory_item", object_id, source=source, evidence_ids=evidence))
            continue

        if rtype == "NewsItem":
            if rid:
                object_id = f"news:{rid}"
                add_node(_node(object_id, "news", getattr(record, "title", None) or rid))
                for iid in instruments:
                    add_node(_node(f"company:{iid}", "company", iid, instrument_id=iid))
                    add_edge(make_relationship(f"company:{iid}", "has_news", object_id, source=source, evidence_ids=evidence))
            continue

        if rid and include_data_records:
            object_id = f"record:{rtype}:{rid}"
            label = getattr(record, "title", None) or getattr(record, "subject", None) or getattr(record, "event_type", None) or rid
            add_node(_node(object_id, "record", str(label), instrument_id=instruments[0] if instruments else None, metadata={"record_type": rtype}))
            predicate = record_predicate.get(rtype)
            if predicate and instruments:
                for iid in instruments:
                    add_node(_node(f"company:{iid}", "company", iid, instrument_id=iid))
                    add_edge(make_relationship(f"company:{iid}", predicate, object_id, source=source, evidence_ids=evidence))

    return RelationshipGraph(
        nodes=sorted(nodes.values(), key=lambda item: (item.node_type, item.node_id)),
        relationships=sorted(relationships.values(), key=lambda item: item.relationship_id),
        metadata={"record_count": len(records), "node_count": len(nodes), "relationship_count": len(relationships)},
    )
