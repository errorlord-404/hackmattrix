from datetime import datetime
from typing import Any, Optional

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class MachineryRental(Document):
    source_record_id: Optional[str] = None
    record_kind: str = "provider_listing"
    name: str
    category: str
    description: Optional[str] = None
    provider_name: Optional[str] = None
    location: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    location_point: Optional[dict[str, Any]] = None
    service_radius_km: Optional[float] = Field(default=None, ge=0)
    geocode_source: Optional[str] = None
    verified_at: Optional[datetime] = None
    distance_km: Optional[float] = None
    hourly_rate: Optional[float] = None
    daily_rate: Optional[float] = None
    availability_status: str = "unknown"
    contact_phone: Optional[str] = None
    rating: Optional[float] = None
    source: str = "manual"
    source_url: Optional[str] = None
    source_status: str = "active"
    image_url: Optional[str] = None
    observed_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None
    # Legacy/reference-catalog aliases retained for backend-fastapi clients.
    hp: Optional[str] = None
    implements_included: Optional[str] = None
    owner_name: Optional[str] = None
    village: Optional[str] = None
    phone: Optional[str] = None
    reviews_count: Optional[int] = None
    available_status: Optional[str] = None

    class Settings:
        name = "machinery_rentals"
        indexes = [IndexModel([("location_point", "2dsphere")], sparse=True), IndexModel("source_record_id", unique=True, sparse=True), "state", "district", "category"]
