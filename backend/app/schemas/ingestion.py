from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class IngestionRunResponse(BaseModel):
    id: str
    trigger: str
    sources: list[str] = Field(default_factory=list)
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    stats: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
