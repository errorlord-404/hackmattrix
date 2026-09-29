from datetime import datetime
from typing import List, Optional

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class GovScheme(Document):
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

    class Settings:
        name = "gov_schemes"
        indexes = [IndexModel("source_record_id", unique=True, sparse=True), "fetched_at", "source"]
