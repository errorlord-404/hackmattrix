from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CropCreate(BaseModel):
    name: str
    season: str
    water_requirement: str
    soil_compatibility: List[str] = Field(default_factory=list)
    previous_crop_compatibility: List[str] = Field(default_factory=list)
    avg_yield_per_acre: float
    avg_price_per_quintal: float


class CropUpdate(BaseModel):
    name: Optional[str] = None
    season: Optional[str] = None
    water_requirement: Optional[str] = None
    soil_compatibility: Optional[List[str]] = None
    previous_crop_compatibility: Optional[List[str]] = None
    avg_yield_per_acre: Optional[float] = None
    avg_price_per_quintal: Optional[float] = None


class CropResponse(BaseModel):
    id: str
    name: str
    season: Optional[str] = None
    water_requirement: Optional[str] = None
    soil_compatibility: List[str] = Field(default_factory=list)
    previous_crop_compatibility: List[str] = Field(default_factory=list)
    avg_yield_per_acre: Optional[float] = None
    avg_price_per_quintal: Optional[float] = None
    source: str = "manual"
    source_url: Optional[str] = None
    source_record_id: Optional[str] = None
    fetched_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
