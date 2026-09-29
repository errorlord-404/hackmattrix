from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FertilizerCreate(BaseModel):
    name: str
    type: str
    bag_size: str
    subsidized_mrp: float
    govt_subsidy_per_bag: float
    dosage_per_acre: str
    suitable_crops: List[str] = Field(default_factory=list)


class FertilizerUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    bag_size: Optional[str] = None
    subsidized_mrp: Optional[float] = None
    govt_subsidy_per_bag: Optional[float] = None
    dosage_per_acre: Optional[str] = None
    suitable_crops: Optional[List[str]] = None


class FertilizerResponse(FertilizerCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)


class FertilizerRecommendationRequest(BaseModel):
    crop_name: str = Field(min_length=1)
    fertilizer_type: Optional[str] = Field(default=None, min_length=1)
    max_budget_per_bag: Optional[float] = Field(default=None, ge=0)


class FertilizerRecommendationResponse(BaseModel):
    crop_name: str
    fertilizer_type: Optional[str] = None
    max_budget_per_bag: Optional[float] = None
    recommended_fertilizers: List[FertilizerResponse]
