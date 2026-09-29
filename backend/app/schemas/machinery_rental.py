from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MachineryRentalPayload(BaseModel):
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
    service_radius_km: Optional[float] = Field(default=None, ge=0)
    geocode_source: Optional[str] = None
    verified_at: Optional[datetime] = None
    distance_km: Optional[float] = Field(default=None, ge=0)
    hourly_rate: Optional[float] = Field(default=None, ge=0)
    daily_rate: Optional[float] = Field(default=None, ge=0)
    availability_status: str = "unknown"
    contact_phone: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    source: str = "manual"
    source_url: Optional[str] = None
    source_status: str = "active"
    image_url: Optional[str] = None
    observed_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    metadata: Optional[dict] = None
    hp: Optional[str] = None
    implements_included: Optional[str] = None
    owner_name: Optional[str] = None
    village: Optional[str] = None
    phone: Optional[str] = None
    reviews_count: Optional[int] = Field(default=None, ge=0)
    available_status: Optional[str] = None

    @model_validator(mode="after")
    def require_provider_and_location(self):
        if not (self.provider_name or self.owner_name):
            raise ValueError("provider_name or owner_name is required")
        if not (self.location or self.village):
            raise ValueError("location or village is required")
        return self


class MachineryRentalCreate(MachineryRentalPayload):
    pass


class MachineryRentalUpdate(BaseModel):
    source_record_id: Optional[str] = None
    record_kind: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    provider_name: Optional[str] = None
    location: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    service_radius_km: Optional[float] = Field(default=None, ge=0)
    geocode_source: Optional[str] = None
    verified_at: Optional[datetime] = None
    distance_km: Optional[float] = Field(default=None, ge=0)
    hourly_rate: Optional[float] = Field(default=None, ge=0)
    daily_rate: Optional[float] = Field(default=None, ge=0)
    availability_status: Optional[str] = None
    contact_phone: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    source: Optional[str] = None
    source_url: Optional[str] = None
    source_status: Optional[str] = None
    image_url: Optional[str] = None
    observed_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    metadata: Optional[dict] = None
    hp: Optional[str] = None
    implements_included: Optional[str] = None
    owner_name: Optional[str] = None
    village: Optional[str] = None
    phone: Optional[str] = None
    reviews_count: Optional[int] = Field(default=None, ge=0)
    available_status: Optional[str] = None


class MachineryRentalResponse(MachineryRentalPayload):
    id: str

    model_config = ConfigDict(from_attributes=True)
