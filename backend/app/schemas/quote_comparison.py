from __future__ import annotations

from pydantic import BaseModel, Field


class MarketplaceQuote(BaseModel):
    """A supplier or farmer-provided quote; this service never invents a price."""

    provider_name: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=240)
    base_cost: float = Field(ge=0)
    delivery_cost: float = Field(default=0, ge=0)
    loading_cost: float = Field(default=0, ge=0)
    unloading_cost: float = Field(default=0, ge=0)
    additional_cost: float = Field(default=0, ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=8)
    unit: str | None = Field(default=None, max_length=80)
    source_url: str | None = Field(default=None, max_length=2048)
    note: str | None = Field(default=None, max_length=500)


class QuoteComparisonRequest(BaseModel):
    quotes: list[MarketplaceQuote] = Field(min_length=1, max_length=30)


class QuoteComparisonItem(MarketplaceQuote):
    total_cost: float
    rank: int


class QuoteComparisonResponse(BaseModel):
    comparison_basis: str
    items: list[QuoteComparisonItem]
