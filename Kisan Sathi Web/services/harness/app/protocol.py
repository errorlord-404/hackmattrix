from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


EventKind = Literal[
    "ready", "unavailable", "diagnostic", "agentMessageDelta", "agentMessageCompleted",
    "tool", "approval", "clarification", "turnCompleted", "threadStatus", "reconnect", "cancelled",
]


def _safe_id(value: str, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError(f"{label} must be a bounded identifier")
    return value


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    session_id: str
    turn_id: str
    sequence: int
    kind: EventKind
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = ""
    occurred_at: str = ""
    replay: bool = False
    duplicate: bool = False

    def __post_init__(self) -> None:
        _safe_id(self.session_id, "session_id")
        _safe_id(self.turn_id, "turn_id")
        if self.sequence < 1:
            raise ValueError("sequence must be positive")
        if not self.event_id:
            object.__setattr__(self, "event_id", f"evt-{self.session_id}-{self.sequence}")
        if not self.occurred_at:
            object.__setattr__(self, "occurred_at", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": "1.0",
            "event_id": self.event_id,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "sequence": self.sequence,
            "occurred_at": self.occurred_at,
            "kind": self.kind,
            "payload": self.payload,
            "delivery": {"cursor": str(self.sequence), "replay": self.replay, "duplicate": self.duplicate},
        }

    def ndjson(self) -> str:
        return json.dumps(self.as_dict(), separators=(",", ":"), ensure_ascii=False) + "\n"


@dataclass(frozen=True, slots=True)
class ResumeSnapshot:
    session_id: str
    state: str
    last_sequence: int
    pending_approval_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"session_id": self.session_id, "state": self.state, "last_sequence": self.last_sequence, "pending_approval_ids": list(self.pending_approval_ids)}
