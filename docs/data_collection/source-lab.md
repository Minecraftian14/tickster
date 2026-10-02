# Source Laboratory

The source lab tests candidate providers independently from production collection code.

It records installation/authentication, endpoint behavior, fields, historical depth, granularity, limitations and sample payloads.

## Redundancy groups

- `nse_access`: NSE + indian-market-data + jugaad-data + NSEPython
- `broker_data_api`: Upstox + FYERS + Dhan + Angel One + Zerodha
- `historical_market_aggregators`: yfinance
- `fundamentals_sources`: Upstox + Stoxim + company/exchange filings
- `regulatory_docs`: NSE + SEBI + company IR
- `macro`: RBI

Wrappers in the same group are **access mechanisms**, not independent data sources. We should choose the simplest reliable adapter and keep alternatives available for validation experiments.
