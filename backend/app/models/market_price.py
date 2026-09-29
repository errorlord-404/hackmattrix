from datetime import datetime

from beanie import Document
from pymongo import IndexModel
from typing import Optional


class MarketPrice(Document):
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

    class Settings:
        name = "market_prices"
        indexes = [
            [("crop_name", 1), ("mandi_name", 1), ("date", -1)],
            [("crop_name", 1), ("state", 1), ("district", 1), ("date", -1)],
            IndexModel("source_record_id", unique=True, sparse=True),
        ]
