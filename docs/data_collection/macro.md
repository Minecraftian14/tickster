# Macro context

## Scope

The macro domain provides context for Indian equity research rather than trading execution. It currently supports:

- RBI Database on Indian Economy (DBIE) exported tabular reports via CSV/XLS/XLSX.
- MOSPI e-Sankhyiki CPI API.
- MOSPI e-Sankhyiki item-level CPI API.
- MOSPI e-Sankhyiki IIP API.

RBI's DBIE documentation describes pre-formatted reports that can be exported to Excel, PDF, Text and CSV. MOSPI's current API documentation exposes `/api/getCPIIndex`, `/api/getItemIndex`, and `/api/iip/getIIPData`; larger responses require the MOSPI authentication flow/token.

## Canonical shape

`MacroObservation` captures:

- series identifier
- observation date
- value
- unit
- metadata/raw row
- source + dataset provenance
- retrieval/observation timestamps

The collector intentionally does not invent a universal macro taxonomy. Series metadata can be added later through `MacroSeries`.

## Why two primary sources?

RBI and MOSPI are not treated as redundant providers. RBI is particularly broad for monetary, financial-market, banking, forex, external-sector and other macro/financial series. MOSPI is the direct statistical source for CPI/IIP and other national-statistics products.
