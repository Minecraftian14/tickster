import yfinance as yf

from nodes_pack.exp_zeta_hero import extract_ticker_data
from nodes_pack.exp_zeta_hero.warren_buffett import __main__ as warren_buffett
from nodes_pack.yfinance_nodes import to_dict
from tests.business.utilities.cache_utility import tests_cache


@tests_cache.memoize()
def _get_test_ticker() -> yf.Ticker:
    ticker = yf.Ticker("RELIANCE.NS")
    return to_dict(ticker)


def test_extract_ticker_data():
    print()
    ticker = _get_test_ticker()
    ticker_data = extract_ticker_data(ticker)
    print(ticker_data)


def test_warren_buffet():
    print()
    ticker = _get_test_ticker()
    ticker_data = extract_ticker_data(ticker)
    analysis_data = warren_buffett.prepare_data(ticker_data)
    ticker_document = warren_buffett.data_to_markdown(analysis_data)
    print(ticker_document)
