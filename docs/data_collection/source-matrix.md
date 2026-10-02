# Source matrix (initial working version)

| Source | Type | Domains | Redundancy group | v1 status |
|---|---|---|---|---|
| yfinance | aggregator | instruments, market, corporate_actions, fundamentals, news | historical_market_aggregators | keep | 
| NSE | primary exchange | instruments, market, corporate_actions, company_events, filings | nse_access | keep |
| indian-market-data | open-source wrapper | instruments, market, corporate_actions, company_events | nse_access | test |
| jugaad-data | open-source wrapper | market, macro | nse_access | test |
| NSEPython | open-source wrapper | market, corporate_actions, company_events | nse_access | test |
| Upstox | broker API | instruments, market, fundamentals, shareholding, corporate_actions, news | broker_data_api | keep/test |
| FYERS | broker API | market, instruments | broker_data_api | test alternative |
| Dhan | broker API | market, instruments | broker_data_api | test alternative |
| Angel One | broker API | market, instruments | broker_data_api | test alternative |
| Zerodha | broker API | market, instruments | broker_data_api | optional alternative |
| Stoxim | structured fundamentals | fundamentals, shareholding, corporate_actions | fundamentals_sources | test |
| SEBI | regulator | filings, company_events | regulatory_docs | keep |
| RBI | primary macro | macro | macro | keep |
| AMFI | fund data | fund_data | fund_data | v2 |
| mftool | AMFI wrapper | fund_data | fund_data | v2 |

This matrix is deliberately provisional. Each candidate should be validated with the source-laboratory probes before final selection.
