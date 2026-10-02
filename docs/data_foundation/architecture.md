# Architecture

```text
External sources
      |
      v
 data_collection 1.1.0
      |
      | canonical records + raw evidence refs
      v
 data_foundation 0.1.0
      |
      +-- identity
      +-- temporal / point-in-time
      +-- provenance / source observations
      +-- reconciliation
      +-- relationships
      +-- quality semantics
      +-- company timeline
      +-- persistence/query
      |
      v
 future data_enrichment package
```

`data_foundation` must remain provider-agnostic. It may know the schemas of canonical collection objects, but it should not know how Upstox, NSE, Yahoo or any other source is queried.
