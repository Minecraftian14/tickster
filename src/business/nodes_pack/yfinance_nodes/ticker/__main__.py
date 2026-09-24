import yfinance as yf


def ticker(ticker: str = "") -> yf.Ticker:
    return yf.Ticker(ticker=ticker)


main_callable = ticker
