from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class GovSchemeCreate(BaseModel): 
    source_record_id: Optional[str] = None
    name: str
    description: str
    eligibility_criteria: List[str] = Field(default_factory=list)
    benefits: str
    required_documents: List[str] = Field(default_factory=list)
    application_deadline: Optional[datetime] = None
    application_steps: List[str] = Field(default_factory=list)
    official_source_url: str
    applicable_states: List[str] = Field(default_factory=list)
    source: str = "manual"
    fetched_at: Optional[datetime] = None


class GovSchemeUpdate(BaseModel):
    source_record_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    eligibility_criteria: Optional[List[str]] = None
    benefits: Optional[str] = None
    required_documents: Optional[List[str]] = None
    application_deadline: Optional[datetime] = None
    application_steps: Optional[List[str]] = None
    official_source_url: Optional[str] = None
    applicable_states: Optional[List[str]] = None
    source: Optional[str] = None
    fetched_at: Optional[datetime] = None


class GovSchemeResponse(GovSchemeCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)


class SchemeEligibilityRequest(BaseModel):
    farmer_state: str
    eligibility_criteria: List[str] = Field(default_factory=list)


class SchemeEligibilityResponse(BaseModel):
    farmer_state: str
    eligible_schemes: List[GovSchemeResponse]
