# v1.1.0 Collection Foundation Hardening

This milestone hardens the shared collection layer without adding another large information universe.

## Changes

- Standard package identity: the import package is `data_collection` under `src/business`.
- Version metadata is synchronized at `1.1.0`.
- Minimal `pyproject.toml` provides install metadata and pytest's source path.
- Upstox daily history is chunked to respect the documented V3 retrieval window.
- Market quotes promote the important V3 quote/depth/CAS fields into canonical records.
- Fundamentals create period-aware snapshots from historical statement payloads and expose competitor profiles.
- Raw responses have a content-addressed persistence API.
- Price-bar deduplication preserves source observations by default; explicit collapsing is opt-in.
- Filing collection returns related `DocumentAsset` records and correctly links their `filing_id`.
- Parser/data-quality diagnostics are recorded in `CollectionResult.issues` rather than silently disappearing.
- Documentation and source registry are synchronized with the current domain coverage.

## Notes

Intraday support remains available but is not optimized for sub-second execution. F&O remains outside v1.
