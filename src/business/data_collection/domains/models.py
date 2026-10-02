from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Provenance(BaseModel):
    source: str
    source_type: str
    source_dataset: str | None = None
    source_url: str | None = None
    retrieved_at: datetime
    published_at: datetime | None = None
    observed_at: datetime | None = None
    raw_ref: str | None = None


class Instrument(BaseModel):
    model_config = ConfigDict(extra="allow")
    instrument_id: str
    isin: str | None = None
    symbol: str
    exchange: Literal["NSE", "BSE", "OTHER"] | None = None
    segment: str | None = None
    instrument_key: str | None = None
    exchange_token: str | None = None
    tick_size: Decimal | None = None
    lot_size: int | None = None
    freeze_quantity: Decimal | None = None
    name: str | None = None
    short_name: str | None = None
    series: str | None = None
    security_type: str | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str = "INR"
    active: bool | None = None
    cas_eligible: bool | None = None
    provenance: Provenance


class PriceBar(BaseModel):
    model_config = ConfigDict(extra="allow")
    instrument_id: str
    timestamp: datetime
    timeframe: str
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal | None = None
    volume: int | None = None
    turnover: Decimal | None = None
    delivery_quantity: int | None = None
    delivery_percent: Decimal | None = None
    provenance: Provenance


class MarketQuote(BaseModel):
    model_config = ConfigDict(extra="allow")
    instrument_id: str
    timestamp: datetime
    last_price: Decimal | None = None
    last_trade_quantity: int | None = None
    previous_close: Decimal | None = None
    day_open: Decimal | None = None
    day_high: Decimal | None = None
    day_low: Decimal | None = None
    volume: int | None = None
    year_high: Decimal | None = None
    year_low: Decimal | None = None
    raw_quote: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance


class CorporateAction(BaseModel):
    model_config = ConfigDict(extra="allow")
    instrument_id: str
    action_type: str
    announcement_date: date | None = None
    ex_date: date | None = None
    record_date: date | None = None
    amount: Decimal | None = None
    ratio: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance


class FundamentalSnapshot(BaseModel):
    model_config = ConfigDict(extra="allow")
    instrument_id: str
    period_end: date | None = None
    period_type: str | None = None
    statement_type: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance


class ShareholdingSnapshot(BaseModel):
    model_config = ConfigDict(extra="allow")
    instrument_id: str
    period_end: date | None = None
    holders: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance


class CompanyDocument(BaseModel):
    model_config = ConfigDict(extra="allow")
    document_id: str
    instrument_id: str | None = None
    document_type: str
    title: str
    published_at: datetime | None = None
    url: str | None = None
    mime_type: str | None = None
    raw_ref: str | None = None
    text_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance


class NewsItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    news_id: str
    instrument_ids: list[str] = Field(default_factory=list)
    title: str
    published_at: datetime | None = None
    url: str | None = None
    text: str | None = None
    source_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance


class MacroObservation(BaseModel):
    model_config = ConfigDict(extra="allow")
    series_id: str
    observation_date: date
    value: Any
    unit: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance
