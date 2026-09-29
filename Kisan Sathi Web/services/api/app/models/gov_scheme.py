from datetime import datetime
from beanie import Document
from pydantic import Field
from pymongo import IndexModel
class GovScheme(Document):
    source_record_id: str | None = None; name: str; description: str; eligibility_criteria: list[str] = Field(default_factory=list); benefits: str; required_documents: list[str] = Field(default_factory=list); application_deadline: datetime | None = None; application_steps: list[str] = Field(default_factory=list); official_source_url: str; applicable_states: list[str] = Field(default_factory=list); source: str = "manual"; fetched_at: datetime | None = None
    class Settings: name = "gov_schemes"; indexes = [IndexModel("source_record_id", unique=True, sparse=True), "fetched_at", "source"]
