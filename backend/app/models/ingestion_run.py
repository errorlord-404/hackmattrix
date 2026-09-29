from datetime import datetime
from typing import Any, Optional

from beanie import Document
from pydantic import Field


class IngestionRun(Document):
    trigger: str
    sources: list[str] = Field(default_factory=list)
    status: str = "running"
    started_at: datetime
    completed_at: Optional[datetime] = None
    stats: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)

    class Settings:
        name = "ingestion_runs"
        indexes = [[("started_at", -1)], "status"]
