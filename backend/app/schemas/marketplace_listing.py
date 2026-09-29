from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MarketplaceListingResponse(BaseModel):
    id: str
    listing_type: str
    record_kind: str = "provider_listing"
    title: str
    category: str | None = None
    provider_name: str | None = None
    description: str | None = None
    location: str | None = None
    district: str | None = None
    state: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    distance_km: float | None = Field(default=None, ge=0)
    service_radius_km: float | None = Field(default=None, ge=0)
    geocode_source: str | None = None
    verified_at: datetime | None = None
    price_amount: float | None = Field(default=None, ge=0)
    price_currency: str = "INR"
    price_unit: str | None = None
    availability_status: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    image_url: str | None = None
    listing_url: str | None = None
    source: str
    source_url: str
    source_status: str = "active"
    observed_at: datetime | None = None
    fetched_at: datetime
    metadata: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class MarketplaceDirectoryStatus(BaseModel):
    configured: bool
    source_count: int
    listing_types: list[str]
    message: str
