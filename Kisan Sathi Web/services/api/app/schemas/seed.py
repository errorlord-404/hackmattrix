from pydantic import BaseModel, ConfigDict, Field
class SeedCreate(BaseModel): crop: str; variety: str; duration_days: str; yield_potential: str; disease_resistance: str; recommended_zone: str
class SeedUpdate(BaseModel): crop: str | None = None; variety: str | None = None; duration_days: str | None = None; yield_potential: str | None = None; disease_resistance: str | None = None; recommended_zone: str | None = None
class SeedResponse(SeedCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)
class SeedRecommendationRequest(BaseModel): crop: str = Field(min_length=1); preferred_zone: str | None = None; disease_risk: str | None = None
class SeedRecommendationResponse(BaseModel): crop: str; preferred_zone: str | None = None; disease_risk: str | None = None; recommended_seeds: list[SeedResponse]
