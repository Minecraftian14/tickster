# import os
# from datetime import date, timedelta

# from dotenv import load_dotenv
# load_dotenv()

import pytest
import yfinance as yf


def test_api_first_contact():
    data = yf.Ticker("MSFT")
    for prop in dir(data):
        if '_' in prop: continue
        try: 
            print()
            print("#", prop)
            print(getattr(data, prop))
        except yf.exceptions.YFNotImplementedError: pass


def test_yf_search():
    data = yf.Search("reliance")
    print()
    print("# Quotes")
    [print(q['shortname']) for q in data.quotes]
    print("# News")
    [print(n['title']) for n in data.news]


def test_yf_lookup():
    data = yf.Lookup("reliance")
    print()
    print(data.stock)

def test_yf_sector():
    data = yf.Sector("technology")
    # basic-materials, communication-services, consumer-cyclical, consumer-defensive, energy, financial-services, healthcare, industrials, real-estate, technology, utilities
    print()
    print(data.name)
    print(data.overview)
    print(data.research_reports)
    print(data.symbol)
    print(data.industries)
    print(data.top_companies)
    print(data.top_etfs)
    print(data.top_mutual_funds)

def test_yf_industry():
    data = yf.Industry("semiconductors")
    print()
    print(data.name)
    print(data.overview)
    print(data.research_reports)
    print(data.sector_key)
    print(data.sector_name)
    print(data.symbol)
    print(data.top_companies)
    print(data.top_growth_companies)
    print(data.top_performing_companies)

def test_yf_screen():
    # https://ranaroussi.github.io/yfinance/reference/api/yfinance.EquityQuery.html#yfinance.EquityQuery
    query = yf.EquityQuery('and', [
        yf.EquityQuery('eq', ['exchange', 'BSE']),
        yf.EquityQuery('eq', ['industry', 'Semiconductors']),
    ])
    data = yf.screen(query)
    print()
    print(data.keys())
    print(data.items())
