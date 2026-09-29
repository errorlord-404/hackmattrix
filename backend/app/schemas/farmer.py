from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FarmerCreate(BaseModel):
    name: str
    phone: str
    location: str
    preferred_language: str
    field_ids: List[str] = Field(default_factory=list)


class FarmerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    preferred_language: Optional[str] = None
    field_ids: Optional[List[str]] = None


class FarmerResponse(FarmerCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)

