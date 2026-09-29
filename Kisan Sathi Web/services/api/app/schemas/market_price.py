from datetime import datetime
from pydantic import BaseModel, ConfigDict
class MarketPriceCreate(BaseModel):
    crop_name: str; mandi_name: str; price_per_quintal: float; date: datetime; state: str; district: str; arrival_quintals: float | None = None; source: str = "manual"; observed_at: datetime | None = None; fetched_at: datetime | None = None; min_price_per_quintal: float | None = None; max_price_per_quintal: float | None = None; variety: str | None = None; grade: str | None = None; source_record_id: str | None = None; source_url: str | None = None
class MarketPriceUpdate(BaseModel):
    crop_name: str | None = None; mandi_name: str | None = None; price_per_quintal: float | None = None; date: datetime | None = None; state: str | None = None; district: str | None = None; arrival_quintals: float | None = None; source: str | None = None; observed_at: datetime | None = None; fetched_at: datetime | None = None; min_price_per_quintal: float | None = None; max_price_per_quintal: float | None = None; variety: str | None = None; grade: str | None = None; source_record_id: str | None = None; source_url: str | None = None
class MarketPriceResponse(MarketPriceCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)
class MandiComparisonResponse(BaseModel):
    market_price_id: str; crop_name: str; mandi_name: str; state: str; district: str; price_per_quintal: float; transport_cost: float; loading_cost: float; unloading_cost: float; market_fees: float; storage_cost: float; expected_spoilage: float; sale_revenue: float; net_realisation: float; quantity_quintals: float = 1.0; assumptions: dict[str, float | str]; data_source: str; observed_at: datetime | None = None; fetched_at: datetime | None = None; freshness_seconds: int | None = None
class CompareMandisResponse(BaseModel): crop_name: str; farmer_district: str; farmer_state: str; results: list[MandiComparisonResponse]
class MarketPriceSummaryItem(BaseModel): crop_name: str; mandi_name: str; state: str; district: str; price_per_quintal: float; arrival_quintals: float | None = None; date: datetime; source: str; observed_at: datetime | None = None; fetched_at: datetime | None = None; freshness_seconds: int | None = None
class MarketHistoryPoint(BaseModel): mandi_name: str; date: datetime; price_per_quintal: float; arrival_quintals: float | None = None; source: str
class MarketTrendResponse(BaseModel): crop_name: str; mandi_name: str | None = None; days: int; current: float | None = None; delta: float | None = None; delta_percent: float | None = None; week_high: float | None = None; week_low: float | None = None; series: list[MarketHistoryPoint]
