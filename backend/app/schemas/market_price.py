from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MarketPriceCreate(BaseModel):
    crop_name: str
    mandi_name: str
    price_per_quintal: float
    date: datetime
    state: str
    district: str
    arrival_quintals: Optional[float] = None
    source: str = "manual"
    observed_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    min_price_per_quintal: Optional[float] = None
    max_price_per_quintal: Optional[float] = None
    variety: Optional[str] = None
    grade: Optional[str] = None
    source_record_id: Optional[str] = None
    source_url: Optional[str] = None


class MarketPriceUpdate(BaseModel):
    crop_name: Optional[str] = None
    mandi_name: Optional[str] = None
    price_per_quintal: Optional[float] = None
    date: Optional[datetime] = None
    state: Optional[str] = None
    district: Optional[str] = None
    arrival_quintals: Optional[float] = None
    source: Optional[str] = None
    observed_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    min_price_per_quintal: Optional[float] = None
    max_price_per_quintal: Optional[float] = None
    variety: Optional[str] = None
    grade: Optional[str] = None
    source_record_id: Optional[str] = None
    source_url: Optional[str] = None


class MarketPriceResponse(MarketPriceCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)


class MandiComparisonResponse(BaseModel):
    market_price_id: str
    crop_name: str
    mandi_name: str
    state: str
    district: str
    price_per_quintal: float
    transport_cost: float
    loading_cost: float
    unloading_cost: float
    market_fees: float
    storage_cost: float
    expected_spoilage: float
    sale_revenue: float
    net_realisation: float
    quantity_quintals: float = 1.0
    assumptions: dict[str, float | str]
    data_source: str
    observed_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    freshness_seconds: Optional[int] = None


class CompareMandisResponse(BaseModel):
    crop_name: str
    farmer_district: str
    farmer_state: str
    results: list[MandiComparisonResponse]
    comparison_status: str = "illustrative_only"
    warnings: list[str] = Field(default_factory=list)


class MarketPriceSummaryItem(BaseModel):
    id: Optional[str] = None
    crop_name: str
    mandi_name: str
    state: str
    district: str
    price_per_quintal: float
    arrival_quintals: Optional[float] = None
    date: datetime
    source: str
    observed_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    freshness_seconds: Optional[int] = None
    grade: Optional[str] = None
    variety: Optional[str] = None
    source_url: Optional[str] = None


class SaleRouteQuote(BaseModel):
    market_price_id: str = Field(min_length=1)
    road_distance_km: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    distance_source: Optional[str] = None
    transport_cost_inr: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    loading_cost_inr: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    unloading_cost_inr: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    market_fees_inr: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    storage_cost_inr: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    expected_spoilage_inr: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    quote_source: Optional[str] = None
    quote_observed_at: Optional[datetime] = None


class SaleRouteCompareRequest(BaseModel):
    crop_name: str = Field(min_length=1)
    quantity_quintals: float = Field(gt=0, allow_inf_nan=False)
    grade: Optional[str] = None
    variety: Optional[str] = None
    max_price_age_days: int = Field(default=7, ge=1, le=30)
    routes: list[SaleRouteQuote] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def unique_market_records(self):
        ids = [route.market_price_id for route in self.routes]
        if len(ids) != len(set(ids)):
            raise ValueError("Each market price record may appear in only one route")
        return self


class SaleRouteResult(BaseModel):
    market_price_id: str
    mandi_name: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    grade: Optional[str] = None
    variety: Optional[str] = None
    price_per_quintal: Optional[float] = None
    price_observed_at: Optional[datetime] = None
    price_source: Optional[str] = None
    price_source_url: Optional[str] = None
    road_distance_km: Optional[float] = None
    distance_source: Optional[str] = None
    quote_source: Optional[str] = None
    quote_observed_at: Optional[datetime] = None
    sale_revenue_inr: Optional[float] = None
    disclosed_costs_inr: Optional[float] = None
    net_realisation_inr: Optional[float] = None
    rank: Optional[int] = None
    missing_evidence: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SaleRouteCompareResponse(BaseModel):
    crop_name: str
    quantity_quintals: float
    status: str
    recommended_market_price_id: Optional[str] = None
    results: list[SaleRouteResult]
    warnings: list[str] = Field(default_factory=list)


class MarketHistoryPoint(BaseModel):
    mandi_name: str
    date: datetime
    price_per_quintal: float
    arrival_quintals: Optional[float] = None
    source: str


class MarketTrendResponse(BaseModel):
    crop_name: str
    mandi_name: Optional[str] = None
    days: int
    current: Optional[float] = None
    delta: Optional[float] = None
    delta_percent: Optional[float] = None
    week_high: Optional[float] = None
    week_low: Optional[float] = None
    series: list[MarketHistoryPoint]
