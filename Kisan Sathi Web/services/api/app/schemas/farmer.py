from pydantic import BaseModel, ConfigDict, Field
class FarmerCreate(BaseModel): name: str; phone: str; location: str; preferred_language: str; field_ids: list[str] = Field(default_factory=list)
class FarmerUpdate(BaseModel): name: str | None = None; phone: str | None = None; location: str | None = None; preferred_language: str | None = None; field_ids: list[str] | None = None
class FarmerResponse(FarmerCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)
