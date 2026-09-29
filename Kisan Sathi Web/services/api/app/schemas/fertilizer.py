from pydantic import BaseModel, ConfigDict, Field
class FertilizerCreate(BaseModel): name: str; type: str; bag_size: str; subsidized_mrp: float; govt_subsidy_per_bag: float; dosage_per_acre: str; suitable_crops: list[str] = Field(default_factory=list)
class FertilizerUpdate(BaseModel): name: str | None = None; type: str | None = None; bag_size: str | None = None; subsidized_mrp: float | None = None; govt_subsidy_per_bag: float | None = None; dosage_per_acre: str | None = None; suitable_crops: list[str] | None = None
class FertilizerResponse(FertilizerCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)
class FertilizerRecommendationRequest(BaseModel): crop_name: str = Field(min_length=1); fertilizer_type: str | None = None; max_budget_per_bag: float | None = Field(default=None, ge=0)
class FertilizerRecommendationResponse(BaseModel): crop_name: str; fertilizer_type: str | None = None; max_budget_per_bag: float | None = None; recommended_fertilizers: list[FertilizerResponse]
