from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from data_collection.domains.models import Provenance


class InsiderTransaction(BaseModel):
    """Canonical SEBI PIT disclosure as exposed by NSE."""

    model_config = ConfigDict(extra="allow")

    event_id: str
    instrument_id: str | None = None
    symbol: str | None = None
    company_name: str | None = None
    regulation: str | None = None
    person_name: str | None = None
    person_category: str | None = None
    security_type_prior: str | None = None
    securities_prior: Decimal | None = None
    holding_percent_prior: Decimal | None = None
    security_type_acquired: str | None = None
    securities_acquired: Decimal | None = None
    transaction_value: Decimal | None = None
    transaction_type: str | None = None
    security_type_post: str | None = None
    securities_post: Decimal | None = None
    holding_percent_post: Decimal | None = None
    acquisition_from: date | None = None
    acquisition_to: date | None = None
    intimation_date: datetime | None = None
    mode: str | None = None
    derivative_type: str | None = None
    derivative_contract_type: str | None = None
    buy_value: Decimal | None = None
    buy_quantity: Decimal | None = None
    sell_value: Decimal | None = None
    sell_quantity: Decimal | None = None
    exchange: str | None = None
    remarks: str | None = None
    xbrl_url: str | None = None
    broadcast_at: datetime | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance


class LargeDeal(BaseModel):
    """Bulk/block/short-sale market disclosure from NSE."""

    model_config = ConfigDict(extra="allow")

    event_id: str
    instrument_id: str | None = None
    symbol: str
    company_name: str | None = None
    deal_type: str
    trade_date: date | None = None
    client_name: str | None = None
    side: str | None = None
    quantity: Decimal | None = None
    weighted_average_price: Decimal | None = None
    remarks: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance
