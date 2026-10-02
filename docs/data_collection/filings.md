# Filings / Documents domain

## Scope

This domain collects **filing metadata first** and referenced document assets second.

Current NSE source families:

- Legacy financial-results catalog: `/api/corporates-financial-results`
- Integrated Filing - Financials: `/api/integrated-filing-results`
- Annual reports: `/api/annual-reports`
- Announcement-XBRL catalog
- Secretarial compliance catalog

NSE's current Integrated Filing page exposes filing metadata including quarter end,
submission type, audited/unaudited status, consolidated/standalone status,
broadcast time, revision time and XBRL/details links. The current NSE site also
lists Annual Reports as a separate corporate filing category.

## Design rules

1. Keep the full raw catalog response.
2. Keep point-in-time timestamps: published/received/revised/retrieved.
3. Keep every attachment/XBRL URL as a `DocumentAsset`.
4. Downloaded bytes are content-addressed by SHA-256.
5. XBRL parsing is taxonomy-agnostic and intentionally loss-minimizing.
6. Financial concept mapping belongs in processing/enrichment, not collection.
7. PDF/HTML text extraction is optional processing, not a prerequisite for ingest.

## Why this matters

The financial-results period date is not the same thing as the time the market learned
the information. `published_at`/`received_at` are therefore retained separately from
`period_end` to support point-in-time research and later LLM context construction.

## Current model flow

`NSE catalog -> Filing -> DocumentAsset -> downloaded bytes -> XBRL/PDF processing -> LLM representations`
