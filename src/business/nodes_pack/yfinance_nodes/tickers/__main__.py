import yfinance as yf


def tickers(*ticker: str) -> yf.Ticker:
    ticker = [t.strip() for t in ticker]
    return yf.Tickers(tickers=" ".join(ticker))


main_callable = tickers
