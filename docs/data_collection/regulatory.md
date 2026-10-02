# Regulatory context

## Scope

This domain captures the **SEBI regulatory corpus** that provides market-level and company-relevant regulatory context. It is intentionally separate from NSE company disclosures:

- NSE = what a listed company disclosed to the exchange.
- SEBI = the regulator's rules, circulars, enforcement, guidance, publications and regulatory context.

Current source families represented by the provider:

- Legal / all legal listings
- Regulations
- Circulars
- Master circulars
- Orders / enforcement
- Informal guidance
- Press releases
- Broad SEBI news listing

SEBI's current website exposes searchable listings by title/keywords/entity, with separate areas for regulations, circulars, master circulars, informal guidance, orders and press releases. The current public listings contain thousands of records, so pagination and source provenance are first-class concerns.

## Collection design

The first pass collects **listing metadata** only. Detail pages can be explicitly crawled, and document URLs are then represented as `RegulatoryDocument` objects. Downloads are a separate operation.

Every item retains:

- source category
- title
- publication date
- detail URL
- discovered links
- raw rendered row/cells
- provenance

The generic model is deliberate because SEBI's categories have different semantics. Semantic normalization belongs in processing/enrichment.

## Equity relevance

Not every SEBI item is specific to listed equities. The corpus should therefore retain the full regulatory context but later processing can classify items into themes such as:

- listed-company disclosure
- insider trading
- takeover / SAST
- market manipulation / fraud
- minimum public shareholding
- buyback / capital raising
- research analysts / investment advisers
- governance
- surveillance / market-wide rules
- investor protection
- other market infrastructure context

## Point-in-time rule

Use the publication timestamp of the regulatory item separately from `retrieved_at`. A later amendment, replacement or corrigendum should remain a distinct publication with its own provenance rather than silently mutating history.
