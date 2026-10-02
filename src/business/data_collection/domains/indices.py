from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from data_collection.domains.models import Provenance


class IndexSnapshot(BaseModel):
    """Point-in-time index level/market snapshot from NSE."""

    model_config = ConfigDict(extra="allow")

    index_id: str
    index_symbol: str
    index_name: str | None = None
    timestamp: datetime
    value: Decimal | None = None
    change: Decimal | None = None
    change_percent: Decimal | None = None
    previous_close: Decimal | None = None
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    year_high: Decimal | None = None
    year_low: Decimal | None = None
    one_year_return_percent: Decimal | None = None
    one_month_return_percent: Decimal | None = None
    constituent_count: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance


class IndexPriceBar(BaseModel):
    """Historical OHLC record for a benchmark/index."""

    model_config = ConfigDict(extra="allow")

    index_id: str
    index_symbol: str
    index_name: str | None = None
    timestamp: datetime
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal | None = None
    provenance: Provenance


class IndexValuationSnapshot(BaseModel):
    """Daily index valuation context such as P/E, P/B and dividend yield."""

    index_id: str
    index_symbol: str
    index_name: str | None = None
    observation_date: date
    pe: Decimal | None = None
    pb: Decimal | None = None
    dividend_yield: Decimal | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance


class IndexConstituent(BaseModel):
    """One member of an index snapshot, preserving provider-specific fields."""

    model_config = ConfigDict(extra="allow")

    index_id: str
    index_symbol: str
    index_name: str | None = None
    instrument_id: str | None = None
    symbol: str
    company_name: str | None = None
    weight_percent: Decimal | None = None
    rank: int | None = None
    price: Decimal | None = None
    change: Decimal | None = None
    change_percent: Decimal | None = None
    market_cap: Decimal | None = None
    free_float_market_cap: Decimal | None = None
    volume: int | None = None
    traded_value: Decimal | None = None
    effective_date: date | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance


class SectorClassification(BaseModel):
    """NSE company classification used to provide sector/industry context."""

    model_config = ConfigDict(extra="allow")

    instrument_id: str
    symbol: str
    sector_macro: str | None = None
    sector: str | None = None
    industry: str | None = None
    basic_industry: str | None = None
    classification_as_of: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance
