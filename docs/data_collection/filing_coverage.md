# Filing coverage registry

NSE publishes a broad XBRL filing-family catalogue. As of 2026-09-03 the catalogue
contains 58 listed filing families spanning financial reporting, governance,
ownership, shareholder actions, capital raising, credit, audit, ESG, regulatory risk,
and investor relations.

The project keeps this list as a **capability registry** rather than assuming that
every family has a dedicated JSON endpoint. The broad NSE corporate-announcements
feed can carry category/description plus attachment and XBRL links; specialized pages
and APIs can be added behind the same FilingCollector abstraction when validated.

The current broad announcement endpoint is:

`GET https://www.nseindia.com/api/corporate-announcements?index=equities`

It supports symbol/date filtering and exposes fields such as `desc`, `attchmntText`,
`attchmntFile`, `sm_isin`, announcement time, and dissemination time in current
responses. The collector preserves the raw row and extracts linked assets into
`DocumentAsset` records.
