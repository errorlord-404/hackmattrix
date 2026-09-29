from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SeedCreate(BaseModel):
    crop: str
    variety: str
    duration_days: str
    yield_potential: str
    disease_resistance: str
    recommended_zone: str


class SeedUpdate(BaseModel):
    crop: Optional[str] = None
    variety: Optional[str] = None
    duration_days: Optional[str] = None
    yield_potential: Optional[str] = None
    disease_resistance: Optional[str] = None
    recommended_zone: Optional[str] = None


class SeedResponse(SeedCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)


class SeedRecommendationRequest(BaseModel):
    crop: str = Field(min_length=1)
    preferred_zone: Optional[str] = Field(default=None, min_length=1)
    disease_risk: Optional[str] = Field(default=None, min_length=1)


class SeedRecommendationResponse(BaseModel):
    crop: str
    preferred_zone: Optional[str] = None
    disease_risk: Optional[str] = None
    recommended_seeds: List[SeedResponse]
