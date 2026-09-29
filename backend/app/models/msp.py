from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class MSP(Document):
    crop_name: str
    msp_price_per_quintal: float
    season: str
    marketing_year: str
    procurement_centres: list[str] = Field(default_factory=list)
    variety: Optional[str] = None
    source: str = "manual"
    source_url: Optional[str] = None
    source_record_id: Optional[str] = None
    fetched_at: Optional[datetime] = None

    class Settings:
        name = "msps"
        indexes = [
            [("crop_name", 1), ("marketing_year", -1)],
            IndexModel("source_record_id", unique=True, sparse=True),
        ]
