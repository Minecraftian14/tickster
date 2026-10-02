from __future__ import annotations

import argparse
import json
import os

from dotenv import load_dotenv

from data_collection.providers.yfinance import YahooFinanceProvider


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Probe available market-data providers")
    parser.add_argument("provider", choices=["yfinance", "upstox"])
    parser.add_argument("--symbol", default="RELIANCE")
    parser.add_argument("--isin", default=None)
    parser.add_argument("--instrument-key", default=None)
    args = parser.parse_args()

    if args.provider == "yfinance":
        provider = YahooFinanceProvider()
        print(json.dumps(provider.health(), indent=2))
        records = provider.collect_price_sample(args.symbol)
        print("\nPRICE SAMPLE")
        for record in records:
            print(record.model_dump_json(indent=2))
        return

    token = os.environ.get("upstox_connector.upstox.anaytics_token")
    if not token:
        raise SystemExit("Set UPSTOX_ACCESS_TOKEN before running an Upstox probe.")
    from data_collection.providers.upstox import UpstoxProvider
    if not args.instrument_key:
        raise SystemExit("Upstox requires --instrument-key, e.g. NSE_EQ|INE002A01018")
    from datetime import date, timedelta
    provider = UpstoxProvider(token)
    to_date = date.today()
    from_date = to_date - timedelta(days=7)
    payload = provider.historical_candles_v3(args.instrument_key, "days", 1, to_date, from_date)
    records = provider.parse_candles(payload, args.instrument_key, timeframe="1d")
    print(json.dumps({"provider": provider.name, "records": len(records)}, indent=2))
    for record in records[:5]:
        print(record.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
