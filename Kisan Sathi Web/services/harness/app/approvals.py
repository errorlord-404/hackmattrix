from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any

from kisansathi_auth.claims import ActorScope


TERMINAL = frozenset({"accepted", "declined", "expired", "cancelled", "succeeded", "failed"})


def request_digest(tool: str, arguments: Any) -> str:
    material = json.dumps({"tool": tool, "arguments": arguments}, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    request_id: str
    actor: ActorScope
    tool: str
    arguments: dict[str, Any]
    payload_hash: str
    status: str
    created_at: int
    expires_at: int
    decision_at: int | None = None
    decision_reason: str | None = None


class ApprovalError(ValueError):
    pass


class ApprovalManager:
    def __init__(self, *, ttl_seconds: int = 300) -> None:
        self.ttl_seconds = max(30, min(ttl_seconds, 900))
        self._values: dict[str, ApprovalRequest] = {}
        self._lock = Lock()

    def propose(self, *, request_id: str, actor: ActorScope, tool: str, arguments: dict[str, Any], now: int | None = None) -> ApprovalRequest:
        issued = int(time.time() if now is None else now)
        value = ApprovalRequest(request_id, actor, tool, dict(arguments), request_digest(tool, arguments), "awaiting_confirmation", issued, issued + self.ttl_seconds)
        with self._lock:
            existing = self._values.get(request_id)
            if existing:
                if existing.actor != actor or existing.payload_hash != value.payload_hash:
                    raise ApprovalError("approval request binding conflict")
                return existing
            self._values[request_id] = value
        return value

    def get(self, request_id: str, actor: ActorScope, *, now: int | None = None) -> ApprovalRequest:
        with self._lock:
            value = self._values.get(request_id)
        if value is None or value.actor != actor:
            raise ApprovalError("approval request is not owned by actor")
        current = int(time.time() if now is None else now)
        if value.status == "awaiting_confirmation" and current > value.expires_at:
            value = ApprovalRequest(value.request_id, value.actor, value.tool, value.arguments, value.payload_hash, "expired", value.created_at, value.expires_at, current, "expired")
            with self._lock:
                self._values[request_id] = value
        return value

    def resolve(self, *, request_id: str, actor: ActorScope, accepted: bool, payload_hash: str, reason: str | None = None, now: int | None = None) -> ApprovalRequest:
        value = self.get(request_id, actor, now=now)
        if value.payload_hash != payload_hash:
            raise ApprovalError("approval payload does not match")
        if value.status in TERMINAL or value.status == "executing":
            return value
        current = int(time.time() if now is None else now)
        status = "accepted" if accepted else "declined"
        updated = ApprovalRequest(value.request_id, value.actor, value.tool, value.arguments, value.payload_hash, status, value.created_at, value.expires_at, current, reason)
        with self._lock:
            self._values[request_id] = updated
        return updated

    def begin_execution(self, request_id: str, actor: ActorScope, *, now: int | None = None) -> ApprovalRequest:
        value = self.get(request_id, actor, now=now)
        if value.status != "accepted":
            raise ApprovalError("approval is not accepted")
        updated = ApprovalRequest(value.request_id, value.actor, value.tool, value.arguments, value.payload_hash, "executing", value.created_at, value.expires_at, value.decision_at, value.decision_reason)
        with self._lock:
            self._values[request_id] = updated
        return updated

    def finish(self, request_id: str, actor: ActorScope, *, succeeded: bool, reason: str | None = None) -> ApprovalRequest:
        value = self.get(request_id, actor)
        if value.status in {"succeeded", "failed"}:
            return value
        if value.status != "executing":
            raise ApprovalError("approval is not executing")
        updated = ApprovalRequest(value.request_id, value.actor, value.tool, value.arguments, value.payload_hash, "succeeded" if succeeded else "failed", value.created_at, value.expires_at, value.decision_at, reason or value.decision_reason)
        with self._lock:
            self._values[request_id] = updated
        return updated

    def cancel(self, request_id: str, actor: ActorScope, *, reason: str = "cancelled") -> ApprovalRequest:
        value = self.get(request_id, actor)
        if value.status in TERMINAL:
            return value
        updated = ApprovalRequest(value.request_id, value.actor, value.tool, value.arguments, value.payload_hash, "cancelled", value.created_at, value.expires_at, int(time.time()), reason)
        with self._lock:
            self._values[request_id] = updated
        return updated
