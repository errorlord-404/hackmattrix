from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
class MachineryRentalPayload(BaseModel):
    source_record_id: str | None = None; record_kind: str = "provider_listing"; name: str; category: str; description: str | None = None; provider_name: str | None = None; location: str | None = None; district: str | None = None; state: str | None = None; latitude: float | None = Field(default=None, ge=-90, le=90); longitude: float | None = Field(default=None, ge=-180, le=180); service_radius_km: float | None = Field(default=None, ge=0); geocode_source: str | None = None; verified_at: datetime | None = None; distance_km: float | None = Field(default=None, ge=0); hourly_rate: float | None = Field(default=None, ge=0); daily_rate: float | None = Field(default=None, ge=0); availability_status: str = "unknown"; contact_phone: str | None = None; rating: float | None = Field(default=None, ge=0, le=5); source: str = "manual"; source_url: str | None = None; source_status: str = "active"; image_url: str | None = None; observed_at: datetime | None = None; fetched_at: datetime | None = None; metadata: dict | None = None; hp: str | None = None; implements_included: str | None = None; owner_name: str | None = None; village: str | None = None; phone: str | None = None; reviews_count: int | None = Field(default=None, ge=0); available_status: str | None = None
    @model_validator(mode="after")
    def provider_and_location(self):
        if not (self.provider_name or self.owner_name): raise ValueError("provider_name or owner_name is required")
        if not (self.location or self.village): raise ValueError("location or village is required")
        return self
class MachineryRentalCreate(MachineryRentalPayload): pass
class MachineryRentalUpdate(BaseModel):
    source_record_id: str | None = None; record_kind: str | None = None; name: str | None = None; category: str | None = None; description: str | None = None; provider_name: str | None = None; location: str | None = None; district: str | None = None; state: str | None = None; latitude: float | None = Field(default=None, ge=-90, le=90); longitude: float | None = Field(default=None, ge=-180, le=180); service_radius_km: float | None = Field(default=None, ge=0); availability_status: str | None = None; contact_phone: str | None = None; rating: float | None = Field(default=None, ge=0, le=5); source: str | None = None; source_url: str | None = None; source_status: str | None = None; image_url: str | None = None; observed_at: datetime | None = None; fetched_at: datetime | None = None; metadata: dict | None = None; hp: str | None = None; implements_included: str | None = None; owner_name: str | None = None; village: str | None = None; phone: str | None = None; reviews_count: int | None = Field(default=None, ge=0); available_status: str | None = None
class MachineryRentalResponse(MachineryRentalPayload):
    id: str
    model_config = ConfigDict(from_attributes=True)
