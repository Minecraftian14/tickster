# v0.5.0 — Relationships and Timeline Engine

## Relationship graph

`build_relationship_graph()` derives only factual edges explicitly implied by record structure.
It does not infer relationships from free text.

### Node identity

Node IDs use stable namespaces:

- `company:{instrument_id}`
- `instrument:{instrument_id}`
- `index:{index_id}`
- `filing:{filing_id}`
- `document:{document_id}`
- `document_asset:{asset_id}`
- `news:{news_id}`
- `record:{record_type}:{record_id}`

Because the collection layer currently has canonical instrument identity rather than an independent
company master, `company:{instrument_id}` is an explicit foundation convention. It is not intended to
prevent a future company entity from owning multiple instruments.

### Evidence and multi-source assertions

Every edge may retain source and evidence IDs. When equivalent relationships are asserted by multiple
records/sources, the graph keeps one deterministic edge, merges evidence, and records `source="multiple"`
plus a sorted source list in metadata.

### Queries

`RelationshipIndex` supports deterministic outgoing, incoming, and neighbor lookups. The graph itself is
serializable Pydantic data and can be persisted/regenerated later without introducing a graph database
dependency.

## Timeline

Timeline entries use `temporal_envelope()` and therefore inherit the v0.3 distinction between event time
and knowledge availability. `CanonicalRecord` payloads are understood, including nested provenance.

Records with no provider-supplied identifier receive a deterministic synthetic ID derived from the record
content; they are retained rather than silently dropped.

Timeline output is chronological and factual. No causal or predictive interpretation is performed.
