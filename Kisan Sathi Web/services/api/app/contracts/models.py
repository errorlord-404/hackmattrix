from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant", "tool"]
    content: str = Field(min_length=1, max_length=100_000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(min_length=1, max_length=100)
    session_id: str | None = None
    turn_id: str | None = None
    tool_names: list[str] | None = Field(default=None, max_length=78)


class Delivery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cursor: str = Field(min_length=1, max_length=128)
    replay: bool = False
    duplicate: bool = False


EventKind = Literal[
    "ready",
    "unavailable",
    "diagnostic",
    "agentMessageDelta",
    "agentMessageCompleted",
    "tool",
    "approval",
    "clarification",
    "turnCompleted",
    "threadStatus",
    "reconnect",
    "cancelled",
]


class StreamEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal["1.0"] = "1.0"
    event_id: str = Field(default_factory=lambda: f"evt-{uuid4().hex}", min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    turn_id: str = Field(min_length=1, max_length=128)
    sequence: int = Field(ge=1)
    occurred_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    kind: EventKind
    payload: dict[str, Any]
    delivery: Delivery

    @field_validator("occurred_at")
    @classmethod
    def nonempty_timestamp(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("occurred_at must not be empty")
        return value


class ToolsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    count: int = Field(ge=0)
    tools: list[dict[str, Any]]

