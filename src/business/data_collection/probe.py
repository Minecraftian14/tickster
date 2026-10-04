from __future__ import annotations

import argparse
import json
import os

from dotenv import load_dotenv


def _providers():
    from data_collection.providers.yfinance import YahooFinanceProvider
    from data_collection.providers.nse_archives import NSEArchivesProvider
    providers = {
        "yfinance": YahooFinanceProvider(),
        "nse-archives": NSEArchivesProvider(),
    }
    token = os.environ.get("upstox_connector.upstox.anaytics_token")
    if token:
        from data_collection.providers.upstox import UpstoxProvider
        providers["upstox"] = UpstoxProvider(token)
    return providers


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Probe installed Indian-equity data providers")
    parser.add_argument("--health", action="store_true", help="Only run cheap health/import checks")
    args = parser.parse_args()

    providers = _providers()
    for name, provider in providers.items():
        print(json.dumps({"provider": name, **provider.health()}, indent=2, default=str))

    if args.health:
        return

    symbol = os.environ.get("PROBE_SYMBOL", "RELIANCE")
    yf = providers["yfinance"]
    if yf.health().get("installed"):
        print("\nYFINANCE SAMPLE")
        for record in yf.collect_price_sample(symbol, period="5d"):
            print(record.model_dump_json())

    upstox = providers.get("upstox")
    instrument_key = os.environ.get("UPSTOX_INSTRUMENT_KEY")
    if upstox and instrument_key:
        from datetime import date, timedelta
        print("\nUPSTOX SAMPLE")
        payload = upstox.historical_candles_v3(instrument_key, "days", 1, date.today(), date.today() - timedelta(days=7))
        for record in upstox.parse_candles(payload, os.environ.get("UPSTOX_INSTRUMENT_ID", instrument_key), timeframe="1d")[:5]:
            print(record.model_dump_json())


if __name__ == "__main__":
    main()
