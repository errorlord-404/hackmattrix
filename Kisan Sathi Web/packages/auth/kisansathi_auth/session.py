from __future__ import annotations

import threading
import time
from collections.abc import Mapping
from typing import Any

import jwt

from .claims import ActorScope, ClaimsValidationError, scope_from_claims


class InvalidSession(ValueError):
    """Raised when a signed session cookie cannot establish identity."""


class SessionCodec:
    """HS256 cookie codec with kid-based rotation and manual testable clocks."""

    algorithm = "HS256"

    def __init__(self, keys: Mapping[str, str | bytes], *, active_kid: str, ttl_seconds: int = 3600) -> None:
        if not keys or active_kid not in keys:
            raise ValueError("an active session signing key is required")
        self.keys = {str(kid): (secret.encode("utf-8") if isinstance(secret, str) else bytes(secret)) for kid, secret in keys.items()}
        if any(len(secret) < 16 for secret in self.keys.values()):
            raise ValueError("session signing keys must be at least 16 bytes")
        self.active_kid = active_kid
        self.ttl_seconds = max(1, min(int(ttl_seconds), 86_400))

    def encode(self, scope: ActorScope, *, now: int | None = None, kid: str | None = None) -> str:
        if not isinstance(scope, ActorScope) or not scope.session_id:
            raise ValueError("a session-bound ActorScope is required")
        selected = kid or self.active_kid
        if selected not in self.keys:
            raise ValueError("unknown session signing key")
        issued = int(time.time() if now is None else now)
        payload = {
            "typ": "kisansathi.session",
            "sub": scope.sub,
            "tenant_id": scope.tenant_id,
            "farmer_id": scope.farmer_id,
            "roles": list(scope.roles),
            "sid": scope.session_id,
            "iat": issued,
            "exp": issued + self.ttl_seconds,
        }
        return jwt.encode(payload, self.keys[selected], algorithm=self.algorithm, headers={"kid": selected})

    def decode(self, token: str, *, now: int | None = None) -> ActorScope:
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != self.algorithm or not isinstance(header.get("kid"), str):
                raise InvalidSession("unsupported session signature")
            secret = self.keys.get(header["kid"])
            if secret is None:
                raise InvalidSession("unknown session key")
            payload = jwt.decode(
                token,
                secret,
                algorithms=[self.algorithm],
                options={
                    "verify_exp": False,
                    "verify_iat": False,
                    "verify_nbf": False,
                    "require": ["typ", "sub", "tenant_id", "farmer_id", "roles", "sid", "iat", "exp"],
                },
            )
            if payload.get("typ") != "kisansathi.session":
                raise InvalidSession("invalid session type")
            current = int(time.time() if now is None else now)
            exp = payload.get("exp")
            issued = payload.get("iat")
            if not isinstance(exp, (int, float)) or not isinstance(issued, (int, float)):
                raise InvalidSession("invalid session time claims")
            if current > int(exp) or current < int(issued) - 30:
                raise InvalidSession("expired session")
            return scope_from_claims(payload)
        except InvalidSession:
            raise
        except (jwt.PyJWTError, ClaimsValidationError, TypeError, ValueError, KeyError) as exc:
            raise InvalidSession("invalid session") from exc

    def cookie_kwargs(self) -> dict[str, Any]:
        return {
            "httponly": True,
            "secure": True,
            "samesite": "lax",
            "path": "/",
            "max_age": self.ttl_seconds,
        }


class SessionRegistry:
    """Small revocation boundary; deployments may replace this with a shared store."""

    def __init__(self) -> None:
        self._revoked: dict[str, int] = {}
        self._lock = threading.Lock()

    def revoke(self, session_id: str, *, expires_at: int | None = None, now: int | None = None) -> None:
        current = int(time.time() if now is None else now)
        with self._lock:
            self._revoked[session_id] = int(expires_at or current + 86_400)

    def is_revoked(self, session_id: str, *, now: int | None = None) -> bool:
        current = int(time.time() if now is None else now)
        with self._lock:
            expired = [key for key, expiry in self._revoked.items() if expiry <= current]
            for key in expired:
                self._revoked.pop(key, None)
            return session_id in self._revoked
