from datetime import datetime
from typing import Any
from beanie import Document
from pydantic import Field
from pymongo import IndexModel
class MachineryRental(Document):
    source_record_id: str | None = None; record_kind: str = "provider_listing"; name: str; category: str; description: str | None = None; provider_name: str | None = None; location: str | None = None; district: str | None = None; state: str | None = None; latitude: float | None = Field(default=None, ge=-90, le=90); longitude: float | None = Field(default=None, ge=-180, le=180); location_point: dict[str, Any] | None = None; service_radius_km: float | None = Field(default=None, ge=0); geocode_source: str | None = None; verified_at: datetime | None = None; distance_km: float | None = None; hourly_rate: float | None = None; daily_rate: float | None = None; availability_status: str = "unknown"; contact_phone: str | None = None; rating: float | None = None; source: str = "manual"; source_url: str | None = None; source_status: str = "active"; image_url: str | None = None; observed_at: datetime | None = None; fetched_at: datetime | None = None; metadata: dict[str, Any] | None = None; hp: str | None = None; implements_included: str | None = None; owner_name: str | None = None; village: str | None = None; phone: str | None = None; reviews_count: int | None = None; available_status: str | None = None
    class Settings: name = "machinery_rentals"; indexes = [IndexModel([("location_point", "2dsphere")], sparse=True), IndexModel("source_record_id", unique=True, sparse=True), "state", "district", "category"]
