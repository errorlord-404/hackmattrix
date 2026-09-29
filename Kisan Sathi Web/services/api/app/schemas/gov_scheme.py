from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
class GovSchemeCreate(BaseModel):
    source_record_id: str | None = None; name: str; description: str; eligibility_criteria: list[str] = Field(default_factory=list); benefits: str; required_documents: list[str] = Field(default_factory=list); application_deadline: datetime | None = None; application_steps: list[str] = Field(default_factory=list); official_source_url: str; applicable_states: list[str] = Field(default_factory=list); source: str = "manual"; fetched_at: datetime | None = None
class GovSchemeUpdate(BaseModel):
    source_record_id: str | None = None; name: str | None = None; description: str | None = None; eligibility_criteria: list[str] | None = None; benefits: str | None = None; required_documents: list[str] | None = None; application_deadline: datetime | None = None; application_steps: list[str] | None = None; official_source_url: str | None = None; applicable_states: list[str] | None = None; source: str | None = None; fetched_at: datetime | None = None
class GovSchemeResponse(GovSchemeCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)
class SchemeEligibilityRequest(BaseModel): farmer_state: str; eligibility_criteria: list[str] = Field(default_factory=list)
class SchemeEligibilityResponse(BaseModel): farmer_state: str; eligible_schemes: list[GovSchemeResponse]
