from __future__ import annotations

import gzip
import json
import os
import requests

from datetime import date
from typing import List, Optional

from diskcache import Cache
from pydantic import BaseModel, RootModel

import upstox_client as uc


class InstrumentInfo(BaseModel):
    asset_key         : Optional[str] = None 
    asset_symbol      : Optional[str] = None
    asset_type        : Optional[str] = None
    cas_eligible      : Optional[bool] = None
    country           : Optional[str] = None 
    end_time          : Optional[str] = None 
    exchange          : str
    exchange_token    : str
    expiry            : Optional[int] = None
    freeze_quantity   : Optional[float] = None 
    instrument_key    : str
    instrument_type   : str
    isin              : Optional[str] = None
    last_trading_date : Optional[int] = None
    latency           : Optional[str] = None 
    lot_size          : Optional[int] = None 
    minimum_lot       : Optional[int] = None
    mtf_bracket       : Optional[float] = None
    mtf_enabled       : Optional[bool] = None
    name              : str
    price_quote_unit  : Optional[str] = None
    qty_multiplier    : Optional[float] = None
    security_type     : Optional[str] = None
    segment           : str
    short_name        : Optional[str] = None
    start_time        : Optional[str] = None 
    strike_price      : Optional[float] = None
    tick_size         : Optional[float] = None
    trading_symbol    : str
    underlying_key    : Optional[str] = None
    underlying_symbol : Optional[str] = None
    underlying_type   : Optional[str] = None
    week_days         : Optional[str] = None 
    weekly            : Optional[bool] = None


class InstrumentList(RootModel[list[InstrumentInfo]]):  pass


class UpstoxAPI:

    @staticmethod
    def __extract__(config, key):
        return config[f"upstox_connector.upstox.{key}"]

    def __init__(self, config=None):
        if config is None: config = os.environ

        self.sandbox_api_key = UpstoxAPI.__extract__(config, "sandbox.api_key")
        self.sandbox_api_secret = UpstoxAPI.__extract__(config, "sandbox.api_secret")
        self.sandbox_token = UpstoxAPI.__extract__(config, "sandbox.token")
        self.anaytics_token = UpstoxAPI.__extract__(config, "anaytics_token")

        self.instruments_complete_url = UpstoxAPI.__extract__(config, "instruments.complete")
        self.instruments_nse_url = UpstoxAPI.__extract__(config, "instruments.nse")
        self.instruments_bse_url = UpstoxAPI.__extract__(config, "instruments.bse")
        self.instruments_mcx_url = UpstoxAPI.__extract__(config, "instruments.mcx")

        # CACHE PREPARATION
        self.cache_dir = UpstoxAPI.__extract__(config, "cache_dir")
        self.cache = Cache(self.cache_dir)
        today = date.today()
        self.download_instruments_data = self.cache.memoize(ignore=(0,))(self.download_instruments_data)
        self.instruments = self.download_instruments_data(self.instruments_complete_url, today)

        # READ ONLY INTERACTIONS
        configuration = uc.Configuration()
        configuration.access_token = self.anaytics_token
        self.analysis = uc.ApiClient(configuration)

        self.instrument_api = uc.InstrumentsApi(self.analysis)
        self.historical_api = uc.HistoryApi(self.analysis)

        # READ+WRITE INTERACTIONS
        configuration = uc.Configuration()
        configuration.access_token = self.sandbox_token
        self.sandbox = uc.ApiClient(configuration)

        # ChargeApi, ExpiredInstrumentApi, FundamentalsApi, HistoryApi,
        # HistoryV3Api, InstrumentsApi, IpoApi, LoginApi, MarketApi,
        # MarketHolidaysAndTimingsApi, MarketQuoteApi, MarketQuoteV3Api,
        # MutualFundApi, NewsApi, OptionsApi, OrderApi, OrderApiV3, PortfolioApi,
        # PostTradeApi, TradeProfitAndLossApi, UserApi, WebsocketApi

    def download_instruments_data(self, url, key):
        print("Downloading", url, "keyed by", key)
        response = requests.get(url, stream=True)
        response.raise_for_status()
        json_text = gzip.decompress(response.content)
        data = InstrumentList.model_validate_json(json_text.decode("utf-8"))
        # data = json.loads(json_text.decode("utf-8"))
        return data


if __name__=="__main__":
    print("Hey")

    from dotenv import load_dotenv
    load_dotenv()

    # uapi = UpstoxAPI()
    # print(uapi.instruments.root[0].instrument_key)

    