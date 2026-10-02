# Development plan

## Current strategy

Develop domain-first. Complete each domain enough to establish the information capability, then harden shared collection infrastructure before moving into heavier enrichment.

## Domain status

1. Instrument — complete enough for stable identity.
2. Market — functionally complete for EOD/historical/cross-source collection; hardening in progress.
3. Corporate actions — complete.
4. Fundamentals/shareholding — collected; canonical-period hardening in progress.
5. Company events/filings/documents — source coverage established; deeper extraction remains in enrichment.
6. News — source collection established; entity/event enrichment remains.
7. Index / benchmark context — complete for current/historical structured context.
8. Macro / regulatory — source coverage established.

## Hardening milestone

Before the enrichment layer, resolve:

1. package/import identity,
2. version metadata,
3. historical request chunking,
4. complete canonical market quotes,
5. period-aware fundamentals,
6. persistent raw evidence,
7. source-aware observation preservation,
8. filing/asset relationships,
9. observable parser issues,
10. documentation/source registry synchronization.

## Enrichment phase after hardening

- entity resolution / identifier graph,
- source reconciliation,
- corporate-event normalization,
- revision chains,
- financial concept mapping,
- derived market/financial features,
- document text extraction and structure,
- news/entity linking,
- temporal company timeline,
- embeddings and retrieval indexes.

## Representation phase

The same canonical corpus should support JSON, JSONL, Markdown, Parquet, company dossiers, timelines, RAG chunks, semantic search and knowledge-graph-like views.
