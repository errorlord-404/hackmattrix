from datetime import datetime
from beanie import Document
from pymongo import IndexModel
class MarketPrice(Document):
    crop_name: str; mandi_name: str; price_per_quintal: float; date: datetime; state: str; district: str; arrival_quintals: float | None = None; source: str = "manual"; observed_at: datetime | None = None; fetched_at: datetime | None = None; min_price_per_quintal: float | None = None; max_price_per_quintal: float | None = None; variety: str | None = None; grade: str | None = None; source_record_id: str | None = None; source_url: str | None = None
    class Settings: name = "market_prices"; indexes = [[("crop_name", 1), ("mandi_name", 1), ("date", -1)], IndexModel("source_record_id", unique=True, sparse=True)]
