from beanie import Document
from pydantic import Field
class Farmer(Document):
    name: str; phone: str; location: str; preferred_language: str; field_ids: list[str] = Field(default_factory=list)
    class Settings: name = "farmers"
