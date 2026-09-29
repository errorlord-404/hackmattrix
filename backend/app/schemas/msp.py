from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MSPCreate(BaseModel):
    crop_name: str
    msp_price_per_quintal: float
    season: str
    marketing_year: str
    procurement_centres: List[str] = Field(default_factory=list)
    variety: Optional[str] = None
    source: str = "manual"
    source_url: Optional[str] = None
    source_record_id: Optional[str] = None
    fetched_at: Optional[datetime] = None


class MSPUpdate(BaseModel):
    crop_name: Optional[str] = None
    msp_price_per_quintal: Optional[float] = None
    season: Optional[str] = None
    marketing_year: Optional[str] = None
    procurement_centres: Optional[List[str]] = None
    variety: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    source_record_id: Optional[str] = None
    fetched_at: Optional[datetime] = None


class MSPResponse(MSPCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)


class MSPMarketComparisonItem(BaseModel):
    mandi_name: str
    state: str
    district: str
    market_price_per_quintal: float
    msp_price_per_quintal: float
    difference_from_msp: float
    observed_at: datetime
    source: str
    source_url: Optional[str] = None


class MSPMarketComparisonResponse(BaseModel):
    crop_name: str
    msp: Optional[MSPResponse] = None
    markets: List[MSPMarketComparisonItem] = Field(default_factory=list)
    message: str
