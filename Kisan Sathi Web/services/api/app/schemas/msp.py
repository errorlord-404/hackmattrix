from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
class MSPCreate(BaseModel): crop_name: str; msp_price_per_quintal: float; season: str; marketing_year: str; procurement_centres: list[str] = Field(default_factory=list); variety: str | None = None; source: str = "manual"; source_url: str | None = None; source_record_id: str | None = None; fetched_at: datetime | None = None
class MSPUpdate(BaseModel): crop_name: str | None = None; msp_price_per_quintal: float | None = None; season: str | None = None; marketing_year: str | None = None; procurement_centres: list[str] | None = None; variety: str | None = None; source: str | None = None; source_url: str | None = None; source_record_id: str | None = None; fetched_at: datetime | None = None
class MSPResponse(MSPCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)
class MSPMarketComparisonItem(BaseModel): mandi_name: str; state: str; district: str; market_price_per_quintal: float; msp_price_per_quintal: float; difference_from_msp: float; observed_at: datetime; source: str; source_url: str | None = None
class MSPMarketComparisonResponse(BaseModel): crop_name: str; msp: MSPResponse | None = None; markets: list[MSPMarketComparisonItem] = Field(default_factory=list); message: str
