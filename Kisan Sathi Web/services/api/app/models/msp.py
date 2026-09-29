from datetime import datetime
from beanie import Document
from pydantic import Field
from pymongo import IndexModel
class MSP(Document):
    crop_name: str; msp_price_per_quintal: float; season: str; marketing_year: str; procurement_centres: list[str] = Field(default_factory=list); variety: str | None = None; source: str = "manual"; source_url: str | None = None; source_record_id: str | None = None; fetched_at: datetime | None = None
    class Settings: name = "msps"; indexes = [IndexModel("source_record_id", unique=True, sparse=True)]
