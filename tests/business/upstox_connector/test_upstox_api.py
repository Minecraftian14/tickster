import os
from datetime import date, timedelta

import upstox_client
from dotenv import load_dotenv

load_dotenv()


SYMBOL = "RELIANCE"

SHORT_WINDOW = 10
MEDIUM_WINDOW = 20
LONG_WINDOW = 50

configuration = upstox_client.Configuration()
configuration.access_token = os.environ["upstox_connector.upstox.anaytics_token"]

client = upstox_client.ApiClient(configuration)

instrument_api = upstox_client.InstrumentsApi(client)
historical_api = upstox_client.HistoryApi(client)

# upstox_connector.upstox.anaytics_token

def find_instrument(symbol: str):
    print(f"Searching for {symbol}...")

    response = instrument_api.search_instrument(
        query=symbol,
        exchanges="NSE",
        segments="EQ",
        records=10,
    )

    results = response.data

    if not results:
        raise RuntimeError(f"Could not find {symbol}")

    instrument = results[0]

    print(f"Found: {instrument['trading_symbol']}")
    print(f"Instrument key: {instrument['instrument_key']}")

    return instrument['instrument_key']


def get_prices(instrument_key: str):

    end_date = date.today()
    start_date = end_date - timedelta(days=120)

    print(
        f"\nFetching candles "
        f"{start_date} → {end_date}..."
    )

    response = historical_api.get_historical_candle_data1(
        instrument_key,
        "day",
        end_date.strftime("%Y-%m-%d"),
        start_date.strftime("%Y-%m-%d"),
        '2.0'
    )

    candles = response.data.candles


    prices = [
        candle[4]
        for candle in candles
    ]

    prices.reverse()

    return prices


def sma(values, window):
    if len(values) < window:
        return None

    return sum(values[-window:]) / window


def analyze(prices):

    short = sma(prices, SHORT_WINDOW)
    medium = sma(prices, MEDIUM_WINDOW)
    long = sma(prices, LONG_WINDOW)

    print("\nMoving averages")
    print("----------------")
    print(f"SMA {SHORT_WINDOW:2}: {short:.2f}")
    print(f"SMA {MEDIUM_WINDOW:2}: {medium:.2f}")
    print(f"SMA {LONG_WINDOW:2}: {long:.2f}")

    print("\nStrategy")

    if short > medium > long:
        print("🟢 BULLISH")
        print("Short > Medium > Long")

    elif short < medium < long:
        print("🔴 BEARISH")
        print("Short < Medium < Long")

    else:
        print("🟡 MIXED")
        print("Moving averages are not aligned.")


def test_upstox_api():

    print("================================")
    print(" Triple Moving Average Strategy")
    print("================================\n")

    instrument_key = find_instrument(SYMBOL)

    prices = get_prices(instrument_key)

    print(f"\nReceived {len(prices)} candles.")

    analyze(prices)
