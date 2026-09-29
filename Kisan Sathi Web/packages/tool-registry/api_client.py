"""Authenticated HTTP boundary used by the provider-neutral tool executor."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

try:
    from .errors import BackendError, ExecutionContextError, is_retryable_status
except ImportError:  # pragma: no cover - direct package-path imports
    from errors import BackendError, ExecutionContextError, is_retryable_status


_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SAFE_CODE = re.compile(r"^[A-Za-z0-9._:-]{1,96}$")
_SECRET_TEXT = re.compile(r"(?:api[-_]?key|authorization|access[-_]?token|refresh[-_]?token|client[-_]?secret|password|credential|secret)\s*[:=]", re.IGNORECASE)


def _require_id(value: str, label: str) -> str:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise ValueError(f"{label} must be a bounded server-issued identifier")
    return value


@dataclass(frozen=True, slots=True)
class ActorScope:
    """Immutable claims-derived identity; it is never part of model arguments."""

    sub: str
    tenant_id: str
    farmer_id: str
    roles: tuple[str, ...] = ()
    session_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "sub", _require_id(self.sub, "sub"))
        object.__setattr__(self, "tenant_id", _require_id(self.tenant_id, "tenant_id"))
        object.__setattr__(self, "farmer_id", _require_id(self.farmer_id, "farmer_id"))
        object.__setattr__(self, "session_id", _require_id(self.session_id, "session_id") if self.session_id else "")
        normalized_roles = tuple(sorted({_require_id(str(role), "role") for role in self.roles}))
        object.__setattr__(self, "roles", normalized_roles)

    @property
    def actor_id(self) -> str:
        return self.sub


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Trusted per-call context supplied by the authenticated harness."""

    actor: ActorScope
    request_id: str
    session_id: str
    turn_id: str
    tool_call_id: str
    service_token: str | None = None
    signed_actor_context: str | None = None

    def __post_init__(self) -> None:
        for label in ("request_id", "session_id", "turn_id", "tool_call_id"):
            _require_id(getattr(self, label), label)
        if self.actor.session_id and self.actor.session_id != self.session_id:
            raise ValueError("execution session does not match actor scope")
        if self.service_token is not None and not self.service_token.strip():
            raise ValueError("service_token cannot be empty")
        if self.signed_actor_context is not None and not self.signed_actor_context.strip():
            raise ValueError("signed_actor_context cannot be empty")


@dataclass(frozen=True, slots=True)
class BackendResponse:
    data: Any
    request_id: str
    status_code: int


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def idempotency_key(actor: ActorScope, tool_name: str, resource: str, payload: Any) -> str:
    """Derive a stable, actor-scoped key for one canonical write payload."""

    material = canonical_json(
        {
            "actor": {"sub": actor.sub, "tenant_id": actor.tenant_id, "farmer_id": actor.farmer_id},
            "tool": tool_name,
            "resource": resource,
            "payload": payload,
        }
    ).encode("utf-8")
    return "ks-" + hashlib.sha256(material).hexdigest()[:48]


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def sign_actor_context(context: ExecutionContext, secret: str | bytes, *, audience: str = "kisansathi-api", ttl_seconds: int = 60, now: int | None = None) -> str:
    """Create a short-lived opaque internal actor envelope without exposing IDs to the model."""

    secret_bytes = secret.encode("utf-8") if isinstance(secret, str) else secret
    issued = int(time.time() if now is None else now)
    payload = {
        "aud": audience,
        "exp": issued + max(1, min(ttl_seconds, 300)),
        "iat": issued,
        "actor": {
            "sub": context.actor.sub,
            "tenant_id": context.actor.tenant_id,
            "farmer_id": context.actor.farmer_id,
            "roles": list(context.actor.roles),
        },
        "request_id": context.request_id,
        "session_id": context.session_id,
        "turn_id": context.turn_id,
        "tool_call_id": context.tool_call_id,
    }
    encoded = _b64(canonical_json(payload).encode("utf-8"))
    signature = hmac.new(secret_bytes, encoded.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded}.{_b64(signature)}"


def _safe_message(value: Any, fallback: str) -> str:
    if not isinstance(value, str) or not value.strip() or _SECRET_TEXT.search(value):
        return fallback
    return value.strip()[:300]


class ApiClient:
    """Small server-to-server client with no browser/model identity selector."""

    def __init__(
        self,
        base_url: str,
        *,
        service_token: str | None = None,
        actor_context_secret: str | bytes | None = None,
        actor_context_audience: str = "kisansathi-api",
        timeout_seconds: float = 20.0,
        max_response_bytes: int = 32 * 1024,
        transport: httpx.AsyncBaseTransport | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        parsed = urlsplit(base_url.rstrip("/"))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url must use an absolute http:// or https:// URL")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if max_response_bytes < 1024:
            raise ValueError("max_response_bytes must be at least 1024")
        self.base_url = base_url.rstrip("/")
        self.service_token = service_token
        self.actor_context_secret = actor_context_secret
        self.actor_context_audience = actor_context_audience
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = min(int(max_response_bytes), 1024 * 1024)
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
        )
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "ApiClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    def _headers(self, context: ExecutionContext, *, idempotency: str | None, content_type: str | None) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "X-Request-ID": context.request_id,
            "X-Session-ID": context.session_id,
            "X-Turn-ID": context.turn_id,
            "X-Tool-Call-ID": context.tool_call_id,
        }
        token = context.service_token or self.service_token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        actor_context = context.signed_actor_context
        if actor_context is None and self.actor_context_secret is not None:
            actor_context = sign_actor_context(context, self.actor_context_secret, audience=self.actor_context_audience)
        if actor_context:
            headers["X-Internal-Actor-Context"] = actor_context
        if idempotency:
            headers["Idempotency-Key"] = idempotency
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    @staticmethod
    def _path(path: str) -> str:
        if not isinstance(path, str) or not path.startswith("/") or path.startswith("//") or ".." in path.split("/"):
            raise ValueError("API paths must be internal absolute paths")
        return path

    async def request(
        self,
        method: str,
        path: str,
        *,
        context: ExecutionContext,
        params: Mapping[str, Any] | None = None,
        json_body: Any = None,
        content: bytes | None = None,
        content_type: str | None = None,
        idempotency: str | None = None,
    ) -> BackendResponse:
        if not isinstance(context, ExecutionContext):
            raise ExecutionContextError("An authenticated execution context is required.", code="execution_context_required")
        path = self._path(path)
        method = method.upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError("unsupported HTTP method")
        if content is not None and json_body is not None:
            raise ValueError("content and json_body are mutually exclusive")
        request_id = context.request_id
        try:
            response = await self._client.request(
                method,
                path,
                params={key: value for key, value in (params or {}).items() if value is not None},
                json=None if content is not None else json_body,
                content=content,
                headers=self._headers(context, idempotency=idempotency, content_type=content_type),
            )
        except httpx.TimeoutException as exc:
            raise BackendError("The farming service timed out.", "backend_timeout", retryable=True, request_id=request_id) from exc
        except httpx.RequestError as exc:
            raise BackendError("The farming service is unreachable.", "backend_unreachable", retryable=True, request_id=request_id) from exc

        response_request_id = response.headers.get("X-Request-ID", request_id)
        if len(response.content) > self.max_response_bytes:
            raise BackendError(
                "The farming service returned a response that exceeds the configured bound.",
                "backend_response_too_large",
                status_code=response.status_code,
                retryable=False,
                request_id=response_request_id,
            )
        if response.is_error:
            code = "backend_http_error"
            message = f"The farming service returned HTTP {response.status_code}."
            try:
                payload = response.json()
            except ValueError:
                payload = None
            detail = payload.get("detail") if isinstance(payload, dict) else None
            if isinstance(detail, dict):
                candidate_code = detail.get("code")
                if isinstance(candidate_code, str) and _SAFE_CODE.fullmatch(candidate_code):
                    code = candidate_code
                message = _safe_message(detail.get("message"), message)
            elif isinstance(detail, str):
                message = _safe_message(detail, message)
            raise BackendError(message, code, status_code=response.status_code, retryable=is_retryable_status(response.status_code), request_id=response_request_id)

        if response.status_code == 204:
            payload = None
        else:
            try:
                payload = response.json()
            except ValueError as exc:
                raise BackendError("The farming service returned an invalid response.", "backend_invalid_response", status_code=response.status_code, retryable=False, request_id=response_request_id) from exc
        return BackendResponse(payload, response_request_id, response.status_code)

    async def get(self, path: str, *, context: ExecutionContext, params: Mapping[str, Any] | None = None) -> BackendResponse:
        return await self.request("GET", path, context=context, params=params)

    async def post(self, path: str, *, context: ExecutionContext, json_body: Any, idempotency: str | None = None) -> BackendResponse:
        return await self.request("POST", path, context=context, json_body=json_body, idempotency=idempotency)

    async def put(self, path: str, *, context: ExecutionContext, json_body: Any, idempotency: str) -> BackendResponse:
        return await self.request("PUT", path, context=context, json_body=json_body, idempotency=idempotency)

    async def patch(self, path: str, *, context: ExecutionContext, json_body: Any, idempotency: str) -> BackendResponse:
        return await self.request("PATCH", path, context=context, json_body=json_body, idempotency=idempotency)

    async def post_bytes(
        self,
        path: str,
        *,
        context: ExecutionContext,
        content: bytes,
        content_type: str,
        params: Mapping[str, Any] | None = None,
        idempotency: str | None = None,
    ) -> BackendResponse:
        return await self.request("POST", path, context=context, params=params, content=content, content_type=content_type, idempotency=idempotency)


# Compatibility name used by the source adapter and a convenient import for callers.
BackendClient = ApiClient
