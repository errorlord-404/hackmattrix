from typing import List

from beanie import Document
from pydantic import Field


class Disease(Document):
    crop_name: str
    disease_name: str
    symptoms: List[str] = Field(default_factory=list)
    severity_levels: List[str] = Field(default_factory=list)
    treatment_recommendation: str

    class Settings:
        name = "diseases"
