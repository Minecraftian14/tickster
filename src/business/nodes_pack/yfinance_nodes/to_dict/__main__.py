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


def tickers_to_dict(tickers: yf.Tickers) -> dict:
    data = {}
    for ticker_name in tickers.symbols:
        data[ticker_name] = to_dict(tickers.tickers[ticker_name])
    return data


def to_dict(data: Any) -> dict:
    if isinstance(data, yf.Tickers): return tickers_to_dict(data)
    data_type = str(type(data))
    # print("TYPE", data_type)
    if 'curl_cffi' in data_type: return None
    if 'NoneType' in data_type: return None
    if 'method' in data_type: return None
    if 'yfinance' not in data_type: return data
    return {field: to_dict(blind_getattr(data, field)) for field in dir(data) if '_' not in field}


main_callable = to_dict
