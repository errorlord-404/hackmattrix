from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from kisansathi_auth.claims import ActorScope


_SECRET = re.compile(r"(api[-_]?key|authorization|access[-_]?token|refresh[-_]?token|client[-_]?secret|password|credential|secret|cookie)", re.IGNORECASE)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): "[REDACTED]" if _SECRET.search(str(key)) else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return [redact(item) for item in value]
    if isinstance(value, str) and _SECRET.search(value):
        return "[REDACTED]"
    return value


@dataclass(frozen=True, slots=True)
class AuditRecord:
    actor: ActorScope
    request_id: str
    session_id: str
    turn_id: str
    tool_call_id: str
    tool: str
    decision: str
    args: dict[str, Any]
    result_identity: str | None = None
    retry_count: int = 0
    cancellation: str | None = None
    created_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        occurred = self.created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return {"actor": {"sub": self.actor.sub, "tenant_id": self.actor.tenant_id, "farmer_id": self.actor.farmer_id}, "request_id": self.request_id, "session_id": self.session_id, "turn_id": self.turn_id, "tool_call_id": self.tool_call_id, "tool": self.tool, "decision": self.decision, "args": redact(self.args), "result_identity": self.result_identity, "retry_count": self.retry_count, "cancellation": self.cancellation, "created_at": occurred}


class AuditLog:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def record(self, value: AuditRecord) -> dict[str, Any]:
        item = value.as_dict()
        self.records.append(item)
        return item
