# Source matrix

| Source | Type | Domains | Redundancy group | Status | Notes |
|---|---|---|---|---|---|
| yfinance | aggregator | instruments, market, corporate_actions, fundamentals, news | historical_market_aggregators | keep | Broad research/secondary source. |
| NSE | primary exchange | instruments, market, corporate_actions, company_events, filings, shareholding, insider_transactions, market_events, indices | nse_access | keep | Primary Indian exchange/reference layer. |
| nse_indices | primary exchange HTTP | indices, sector_classification, index_history, index_valuation | nse_access | keep | Specialized NSE index adapter. |
| nse_public | primary exchange HTTP | shareholding, insider_transactions, market_events, company_events, indices | nse_access | keep | Specialized current-data adapter. |
| nse_filings | primary exchange HTTP | filings, documents, fundamentals, company_events, governance, shareholder_actions, capital_raising, regulatory_risk, esg, credit | nse_access | keep | Filing/catalog + asset access. |
| indian-market-data | open-source wrapper | instruments, market, corporate_actions, company_events, indices, market_events | nse_access | candidate | Alternative NSE archive/access mechanism. |
| jugaad-data | open-source wrapper | market, macro, company_events, indices | nse_access | candidate | Alternative NSE/RBI access mechanism. |
| NSEPython | open-source wrapper | market, corporate_actions, company_events, indices | nse_access | candidate | Alternative NSE access mechanism. |
| Upstox | broker API | instruments, market, fundamentals, shareholding, corporate_actions | broker_data_api | primary broker candidate | Current configured operational provider. |
| FYERS | broker API | market, instruments | broker_data_api | alternative | Candidate alternative to Upstox. |
| Dhan | broker API | market, instruments | broker_data_api | alternative | Candidate alternative to Upstox. |
| Angel One | broker API | market, instruments | broker_data_api | alternative | Candidate alternative to Upstox. |
| Zerodha | broker API | market, instruments | broker_data_api | alternative | Optional alternative. |
| Stoxim | structured fundamentals | fundamentals, shareholding, corporate_actions | fundamentals_sources | candidate | Candidate secondary structured source. |
| SEBI | regulator | regulatory, filings, company_events, insider_transactions | regulatory_docs | keep | Regulatory context and documents. |
| RBI/DBIE | primary macro | macro | macro | keep | Broad macro/economic context. |
| MOSPI | primary macro | macro, CPI, IIP | macro | keep | Official statistical APIs. |
| Google News RSS | RSS aggregator | news | news_aggregators | candidate | Discovery/secondary news. |
| Economic Times RSS | publisher RSS | news | publisher_rss | candidate | Headline/excerpt source; use within publisher terms. |
| Business Standard RSS | publisher RSS | news | publisher_rss | candidate | Headline/excerpt source; use within publisher terms. |
| niftyterminal | open-source wrapper | instruments, market, fundamentals, indices, documents | nse_access | unprobed | Registry candidate only; no production adapter yet. |
| AMFI | primary fund data | fund_data | fund_data | v2 | Outside cash-equity v1 scope. |
| mftool | open-source wrapper | fund_data | fund_data | v2 | AMFI convenience wrapper; outside v1. |

## Redundancy principles

- NSE wrappers are alternate access paths to the NSE information universe.
- Broker APIs are interchangeable alternatives for broker-sourced market data.
- yfinance is a secondary aggregation layer and can serve as an independent cross-check.
- Primary exchange/regulator sources remain the provenance anchors where available.
