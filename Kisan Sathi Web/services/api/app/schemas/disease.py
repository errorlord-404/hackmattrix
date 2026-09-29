from pydantic import BaseModel, ConfigDict, Field
class DiseaseCreate(BaseModel):
    crop_name: str; disease_name: str; symptoms: list[str] = Field(default_factory=list); severity_levels: list[str] = Field(default_factory=list); treatment_recommendation: str
class DiseaseUpdate(BaseModel):
    crop_name: str | None = None; disease_name: str | None = None; symptoms: list[str] | None = None; severity_levels: list[str] | None = None; treatment_recommendation: str | None = None
class DiseaseResponse(DiseaseCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)
