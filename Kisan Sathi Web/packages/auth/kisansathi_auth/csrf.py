from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any


UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class CsrfError(ValueError):
    """Raised when a cookie-authenticated unsafe request lacks valid CSRF proof."""


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class CsrfTokenCodec:
    def __init__(self, secret: str | bytes, *, ttl_seconds: int = 3600) -> None:
        self.secret = secret.encode("utf-8") if isinstance(secret, str) else bytes(secret)
        if len(self.secret) < 16:
            raise ValueError("CSRF secret must be at least 16 bytes")
        self.ttl_seconds = max(1, min(int(ttl_seconds), 86_400))

    def issue(self, session_id: str, *, now: int | None = None) -> str:
        issued = int(time.time() if now is None else now)
        payload = {
            "sid": session_id,
            "iat": issued,
            "exp": issued + self.ttl_seconds,
            "nonce": secrets.token_urlsafe(24),
        }
        encoded = _encode(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        signature = hmac.new(self.secret, encoded.encode("ascii"), hashlib.sha256).digest()
        return f"{encoded}.{_encode(signature)}"

    def verify(self, token: str, session_id: str, *, now: int | None = None) -> bool:
        try:
            encoded, signature = token.split(".", 1)
            expected = hmac.new(self.secret, encoded.encode("ascii"), hashlib.sha256).digest()
            if not hmac.compare_digest(expected, _decode(signature)):
                raise CsrfError("invalid CSRF token")
            payload = json.loads(_decode(encoded).decode("utf-8"))
            current = int(time.time() if now is None else now)
            if payload.get("sid") != session_id or not isinstance(payload.get("exp"), int):
                raise CsrfError("invalid CSRF token")
            if current > payload["exp"] or current < int(payload.get("iat", 0)) - 30:
                raise CsrfError("expired CSRF token")
            return True
        except (CsrfError, ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            if isinstance(exc, CsrfError):
                raise
            raise CsrfError("invalid CSRF token") from exc


def require_csrf(
    method: str,
    session_cookie: str | None,
    csrf_cookie: str | None,
    csrf_header: str | None,
    *,
    csrf: CsrfTokenCodec,
    session_id: str,
    now: int | None = None,
) -> bool:
    """Validate double-submit CSRF only when the request authenticates by cookie."""

    if method.upper() not in UNSAFE_METHODS or not session_cookie:
        return True
    if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
        raise CsrfError("CSRF token required")
    return csrf.verify(csrf_cookie, session_id, now=now)
