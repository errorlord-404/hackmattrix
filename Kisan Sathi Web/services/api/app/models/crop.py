from datetime import datetime
from beanie import Document
from pydantic import Field
from pymongo import IndexModel

class Crop(Document):
    name: str; season: str | None = None; water_requirement: str | None = None
    soil_compatibility: list[str] = Field(default_factory=list); previous_crop_compatibility: list[str] = Field(default_factory=list)
    avg_yield_per_acre: float | None = None; avg_price_per_quintal: float | None = None; source: str = "manual"; source_url: str | None = None; source_record_id: str | None = None; fetched_at: datetime | None = None
    class Settings: name = "crops"; indexes = [IndexModel("source_record_id", unique=True, sparse=True), "name"]
