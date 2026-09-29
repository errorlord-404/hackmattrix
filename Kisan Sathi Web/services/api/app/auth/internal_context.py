from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any, Mapping

from kisansathi_auth.claims import ActorScope


class InternalContextError(ValueError):
    """Raised when a harness-to-API actor envelope cannot be trusted."""


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@dataclass(frozen=True, slots=True)
class VerifiedInternalContext:
    actor: ActorScope
    audience: str
    request_id: str
    session_id: str
    turn_id: str
    tool_call_id: str
    method: str | None
    path: str | None
    issued_at: int
    expires_at: int
    nonce: str | None = None


class InternalContextCodec:
    """Short-lived, audience-bound actor context for trusted service calls.

    The browser and model never receive this envelope. It is only accepted when
    the caller also presents the configured server-to-server secret.
    """

    def __init__(self, secret: str | bytes, *, audience: str = "kisansathi-api", max_ttl_seconds: int = 300) -> None:
        self.secret = secret.encode("utf-8") if isinstance(secret, str) else bytes(secret)
        if len(self.secret) < 16:
            raise ValueError("internal context secret must be at least 16 bytes")
        self.audience = audience
        self.max_ttl_seconds = max(1, min(int(max_ttl_seconds), 300))
        self._seen: dict[str, int] = {}
        self._lock = Lock()

    @staticmethod
    def _canonical(payload: Mapping[str, Any]) -> bytes:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def issue(
        self,
        actor: ActorScope,
        *,
        request_id: str,
        session_id: str,
        turn_id: str,
        tool_call_id: str,
        method: str | None = None,
        path: str | None = None,
        now: int | None = None,
        ttl_seconds: int | None = None,
    ) -> str:
        if not isinstance(actor, ActorScope):
            raise TypeError("actor must be an ActorScope")
        issued = int(time.time() if now is None else now)
        ttl = max(1, min(int(ttl_seconds or self.max_ttl_seconds), self.max_ttl_seconds))
        payload = {
            "aud": self.audience,
            "iat": issued,
            "exp": issued + ttl,
            "nonce": secrets.token_urlsafe(18),
            "actor": {
                "sub": actor.sub,
                "tenant_id": actor.tenant_id,
                "farmer_id": actor.farmer_id,
                "roles": list(actor.roles),
                "sid": actor.session_id or session_id,
            },
            "request_id": request_id,
            "session_id": session_id,
            "turn_id": turn_id,
            "tool_call_id": tool_call_id,
            "method": method.upper() if method else None,
            "path": path,
        }
        encoded = _b64(self._canonical(payload))
        signature = hmac.new(self.secret, encoded.encode("ascii"), hashlib.sha256).digest()
        return f"{encoded}.{_b64(signature)}"

    def verify(
        self,
        value: str,
        *,
        expected_method: str | None = None,
        expected_path: str | None = None,
        now: int | None = None,
        consume: bool = True,
    ) -> VerifiedInternalContext:
        try:
            encoded, signature = value.split(".", 1)
            expected_signature = hmac.new(self.secret, encoded.encode("ascii"), hashlib.sha256).digest()
            if not hmac.compare_digest(expected_signature, _unb64(signature)):
                raise InternalContextError("invalid internal context signature")
            payload = json.loads(_unb64(encoded).decode("utf-8"))
            if not isinstance(payload, dict) or payload.get("aud") != self.audience:
                raise InternalContextError("internal context audience is invalid")
            issued = payload.get("iat")
            expires = payload.get("exp")
            current = int(time.time() if now is None else now)
            if not isinstance(issued, int) or not isinstance(expires, int) or current < issued - 30 or current > expires:
                raise InternalContextError("internal context is expired or not yet valid")
            if expires - issued > self.max_ttl_seconds:
                raise InternalContextError("internal context lifetime is too long")
            nonce = payload.get("nonce")
            if nonce is not None and (not isinstance(nonce, str) or not nonce):
                raise InternalContextError("internal context nonce is invalid")
            method = payload.get("method")
            path = payload.get("path")
            if method is not None and (not isinstance(method, str) or method.upper() != method):
                raise InternalContextError("internal context method is invalid")
            if expected_method and method and method != expected_method.upper():
                raise InternalContextError("internal context method does not match request")
            if expected_path and path and path != expected_path:
                raise InternalContextError("internal context path does not match request")
            actor_data = payload.get("actor")
            if not isinstance(actor_data, dict):
                raise InternalContextError("internal context actor is missing")
            actor = ActorScope(
                sub=actor_data["sub"],
                tenant_id=actor_data["tenant_id"],
                farmer_id=actor_data["farmer_id"],
                roles=actor_data["roles"],
                session_id=actor_data.get("sid") or payload["session_id"],
            )
            values = {key: payload.get(key) for key in ("request_id", "session_id", "turn_id", "tool_call_id")}
            if any(not isinstance(item, str) or not item for item in values.values()):
                raise InternalContextError("internal context trace binding is incomplete")
            if actor.session_id and actor.session_id != values["session_id"]:
                raise InternalContextError("internal context session binding is invalid")
            if consume and nonce:
                with self._lock:
                    self._seen = {key: expiry for key, expiry in self._seen.items() if expiry > current}
                    if nonce in self._seen:
                        raise InternalContextError("internal context has already been used")
                    self._seen[nonce] = expires
            return VerifiedInternalContext(actor=actor, audience=self.audience, request_id=values["request_id"], session_id=values["session_id"], turn_id=values["turn_id"], tool_call_id=values["tool_call_id"], method=method, path=path, issued_at=issued, expires_at=expires, nonce=nonce)
        except InternalContextError:
            raise
        except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InternalContextError("invalid internal actor context") from exc
