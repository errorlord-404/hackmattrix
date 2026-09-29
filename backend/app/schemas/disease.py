from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DiseaseCreate(BaseModel):
    crop_name: str
    disease_name: str
    symptoms: List[str] = Field(default_factory=list)
    severity_levels: List[str] = Field(default_factory=list)
    treatment_recommendation: str


class DiseaseUpdate(BaseModel):
    crop_name: Optional[str] = None
    disease_name: Optional[str] = None
    symptoms: Optional[List[str]] = None
    severity_levels: Optional[List[str]] = None
    treatment_recommendation: Optional[str] = None


class DiseaseResponse(DiseaseCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)
