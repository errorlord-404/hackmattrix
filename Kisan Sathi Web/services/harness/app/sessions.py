from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any

from kisansathi_auth.claims import ActorScope
from kisansathi_auth.session import InvalidSession, SessionCodec, SessionRegistry


@dataclass(frozen=True, slots=True)
class HarnessSession:
    session_id: str
    actor: ActorScope
    status: str = "active"
    active_turn_id: str | None = None


class SessionOwnershipError(PermissionError):
    """Raised for missing, revoked, or cross-actor sessions."""


class SessionManager:
    def __init__(self, *, secret: str | bytes, kid: str = "primary", ttl_seconds: int = 3600) -> None:
        self.codec = SessionCodec({kid: secret}, active_kid=kid, ttl_seconds=ttl_seconds)
        self.registry = SessionRegistry()
        self._sessions: dict[str, HarnessSession] = {}
        self._lock = Lock()

    def create(self, actor: ActorScope) -> tuple[HarnessSession, str]:
        if not actor.session_id:
            raise ValueError("actor session_id is required")
        session = HarnessSession(actor.session_id, actor)
        with self._lock:
            self._sessions[session.session_id] = session
        return session, self.codec.encode(actor)

    def verify_cookie(self, cookie: str, *, expected_session_id: str | None = None) -> HarnessSession:
        try:
            actor = self.codec.decode(cookie)
        except InvalidSession as exc:
            raise SessionOwnershipError("session is invalid") from exc
        if self.registry.is_revoked(actor.session_id):
            raise SessionOwnershipError("session is revoked")
        if expected_session_id is not None and actor.session_id != expected_session_id:
            raise SessionOwnershipError("session ownership mismatch")
        with self._lock:
            session = self._sessions.get(actor.session_id)
            if session is None:
                session = HarnessSession(actor.session_id, actor)
                self._sessions[actor.session_id] = session
            elif session.actor != actor:
                raise SessionOwnershipError("session actor mismatch")
        return session

    def require(self, session_id: str, actor: ActorScope) -> HarnessSession:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None or session.status != "active" or self.registry.is_revoked(session_id) or session.actor != actor:
            raise SessionOwnershipError("session is not owned by actor")
        return session

    def set_turn(self, session_id: str, actor: ActorScope, turn_id: str | None) -> HarnessSession:
        session = self.require(session_id, actor)
        with self._lock:
            if turn_id is not None and session.active_turn_id not in (None, turn_id):
                raise ValueError("a turn is already active")
            updated = HarnessSession(session.session_id, session.actor, session.status, turn_id)
            self._sessions[session_id] = updated
            return updated

    def revoke(self, session_id: str, actor: ActorScope) -> None:
        self.require(session_id, actor)
        self.registry.revoke(session_id)
        with self._lock:
            session = self._sessions[session_id]
            self._sessions[session_id] = HarnessSession(session.session_id, session.actor, "revoked", None)

    def cookie_kwargs(self) -> dict[str, Any]:
        return self.codec.cookie_kwargs()
