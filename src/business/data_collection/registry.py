from __future__ import annotations

SOURCES = {
    "yfinance": {
        "type": "aggregator",
        "domains": ["instruments", "market", "corporate_actions", "fundamentals", "news"],
        "status": "candidate",
        "redundancy_group": "historical_market_aggregators",
    },
    "nse": {
        "type": "primary_exchange",
        "domains": ["instruments", "market", "corporate_actions", "company_events", "filings"],
        "status": "candidate",
        "redundancy_group": "nse_access",
    },
    "indian-market-data": {
        "type": "open_source_wrapper",
        "domains": ["instruments", "market", "corporate_actions", "company_events"],
        "status": "candidate",
        "redundancy_group": "nse_access",
    },
    "jugaad-data": {
        "type": "open_source_wrapper",
        "domains": ["market", "macro"],
        "status": "candidate",
        "redundancy_group": "nse_access",
    },
    "NSEPython": {
        "type": "open_source_wrapper",
        "domains": ["market", "corporate_actions", "company_events"],
        "status": "candidate",
        "redundancy_group": "nse_access",
    },
    "upstox": {
        "type": "broker_api",
        "domains": ["instruments", "market", "fundamentals", "shareholding", "corporate_actions", "news"],
        "status": "installed_or_configured",
        "redundancy_group": "broker_data_api",
    },
    "fyers": {
        "type": "broker_api",
        "domains": ["market", "instruments"],
        "status": "candidate",
        "redundancy_group": "broker_data_api",
    },
    "dhan": {
        "type": "broker_api",
        "domains": ["market", "instruments"],
        "status": "candidate",
        "redundancy_group": "broker_data_api",
    },
    "angel_one": {
        "type": "broker_api",
        "domains": ["market", "instruments"],
        "status": "candidate",
        "redundancy_group": "broker_data_api",
    },
    "zerodha": {
        "type": "broker_api",
        "domains": ["market", "instruments"],
        "status": "candidate",
        "redundancy_group": "broker_data_api",
    },
    "stoxim": {
        "type": "structured_fundamentals",
        "domains": ["fundamentals", "shareholding", "corporate_actions", "company_events"],
        "status": "candidate",
        "redundancy_group": "fundamentals_sources",
    },
    "sebi": {
        "type": "regulator",
        "domains": ["filings", "company_events"],
        "status": "candidate",
        "redundancy_group": "regulatory_docs",
    },
    "rbi": {
        "type": "primary_macro",
        "domains": ["macro"],
        "status": "candidate",
        "redundancy_group": "macro",
    },
    "amfi": {
        "type": "primary_fund_data",
        "domains": ["fund_data"],
        "status": "out_of_scope_v1",
        "redundancy_group": "fund_data",
    },
    "mftool": {
        "type": "open_source_wrapper",
        "domains": ["fund_data"],
        "status": "out_of_scope_v1",
        "redundancy_group": "fund_data",
    },
}
