from typing import Any

import yfinance as yf


def blind_getattr(o: object, name: str):
    try: return getattr(o, name)
    except Exception as e:
        print(e)
        return None


def anything_or_nothing(action):
    try: return action()
    except Exception as e:
        print(e)
        return None


def ticker_to_dict(ticker: yf.Ticker) -> dict:
    return {
        'finances': {
            'info': anything_or_nothing(lambda: ticker.info),
            'income_statement': anything_or_nothing(lambda: ticker.income_stmt),
            'balance_sheet': anything_or_nothing(lambda: ticker.balance_sheet),
            'cash_flow': anything_or_nothing(lambda: ticker.cash_flow),
        },
        'news': anything_or_nothing(lambda: ticker.news),
    }


def tickers_to_dict(tickers: yf.Tickers) -> dict:
    data = {}
    for ticker_name in tickers.symbols:
        data[ticker_name] = ticker_to_dict(tickers.tickers[ticker_name])
    return data


def to_dict(data: Any) -> dict:
    if isinstance(data, yf.Ticker): return ticker_to_dict(data)
    if isinstance(data, yf.Tickers): return tickers_to_dict(data)
    if 'yfinance' not in str(type(data)): return data
    return {field: to_dict(blind_getattr(data, field)) for field in dir(data) if '_' not in field}


main_callable = to_dict
