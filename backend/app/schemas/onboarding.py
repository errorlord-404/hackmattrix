from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProfileReadiness(BaseModel):
    exists: bool
    has_coordinates: bool
    preferred_language: str | None = None


class FieldReadiness(BaseModel):
    active_count: int = Field(ge=0)
    with_crop_count: int = Field(ge=0)
    with_active_cycle_count: int = Field(ge=0)
    approximate_boundaries: int = Field(ge=0)
    farmer_drawn_unverified_boundaries: int = Field(ge=0)
    unclassified_boundaries: int = Field(ge=0)


class OnboardingStatusResponse(BaseModel):
    profile: ProfileReadiness
    fields: FieldReadiness
    latest_sensor_observed_at: datetime | None = None
    voice_configured: bool
    reference_database_available: bool
    next_setup_step: Literal[
        "create_profile", "set_location", "create_field", "review_boundary", "choose_crop", "start_crop_cycle", "ready"
    ]
    limitations: list[str] = Field(default_factory=list)
