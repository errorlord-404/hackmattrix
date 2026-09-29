from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
class CropCreate(BaseModel):
    name: str; season: str; water_requirement: str; soil_compatibility: list[str] = Field(default_factory=list); previous_crop_compatibility: list[str] = Field(default_factory=list); avg_yield_per_acre: float; avg_price_per_quintal: float
class CropUpdate(BaseModel):
    name: str | None = None; season: str | None = None; water_requirement: str | None = None; soil_compatibility: list[str] | None = None; previous_crop_compatibility: list[str] | None = None; avg_yield_per_acre: float | None = None; avg_price_per_quintal: float | None = None
class CropResponse(CropCreate):
    id: str; source: str = "manual"; source_url: str | None = None; source_record_id: str | None = None; fetched_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)
