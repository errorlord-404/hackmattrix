from datetime import datetime
from typing import List, Optional

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class Crop(Document):
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

    class Settings:
        name = "crops"
        indexes = [
            IndexModel("source_record_id", unique=True, sparse=True),
            "name",
        ]
