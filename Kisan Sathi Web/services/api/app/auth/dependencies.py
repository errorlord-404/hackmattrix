from __future__ import annotations

import hmac
import re
from dataclasses import dataclass
from uuid import uuid4

from fastapi import Header, HTTPException, Request

from kisansathi_auth.claims import ActorScope
from kisansathi_auth.csrf import CsrfError, CsrfTokenCodec, require_csrf
from kisansathi_auth.session import InvalidSession, SessionCodec, SessionRegistry

from app.core.config import settings as api_settings
from .internal_context import InternalContextCodec, InternalContextError


_SESSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    mode: str
    session_id: str
    actor: ActorScope
    token_source: str = "development"


def _unauthorized(detail: str = "Authentication required.") -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def _state(request: Request, name: str, factory):
    value = getattr(request.app.state, name, None)
    if value is None:
        value = factory()
        setattr(request.app.state, name, value)
    return value


def _session_codec(request: Request) -> SessionCodec:
    configured = request.app.state.settings
    if not configured.session_configured:
        raise HTTPException(status_code=503, detail="Authentication is unavailable.")
    secret = configured.session_secret or "development-session-secret-change-me-32"
    return _state(request, "session_codec", lambda: SessionCodec({configured.session_kid: secret}, active_kid=configured.session_kid, ttl_seconds=configured.session_ttl_seconds))


def _csrf_codec(request: Request) -> CsrfTokenCodec:
    configured = request.app.state.settings
    if not configured.session_configured:
        raise HTTPException(status_code=503, detail="Authentication is unavailable.")
    secret = configured.csrf_secret or "development-csrf-secret-change-me-32"
    return _state(request, "csrf_codec", lambda: CsrfTokenCodec(secret, ttl_seconds=configured.csrf_ttl_seconds))


def _registry(request: Request) -> SessionRegistry:
    return _state(request, "session_registry", SessionRegistry)


def _development_scope(request: Request, session_id: str) -> ActorScope:
    return ActorScope(sub=f"dev-{api_settings.default_farmer_id}", tenant_id=api_settings.default_tenant_id, farmer_id=api_settings.default_farmer_id, roles=("farmer",), session_id=session_id)


def _legacy_service_scope(request: Request, session_id: str) -> ActorScope:
    return ActorScope(sub=f"service-{api_settings.default_farmer_id}", tenant_id=api_settings.default_tenant_id, farmer_id=api_settings.default_farmer_id, roles=("service",), session_id=session_id)


async def require_actor_scope(
    request: Request,
    authorization: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
    internal_context: str | None = Header(default=None, alias="X-Internal-Actor-Context"),
) -> ActorScope:
    """Establish immutable identity from verified claims or explicit dev mode."""

    configured = request.app.state.settings
    session_id = validate_session_id(x_session_id, f"session-{uuid4().hex}")
    cookie_token = request.cookies.get(configured.session_cookie_name)
    csrf_cookie = request.cookies.get(configured.csrf_cookie_name)
    csrf_header = request.headers.get("X-CSRF-Token")

    if internal_context:
        if not configured.internal_context_secret:
            raise _unauthorized("Internal authentication is unavailable.")
        try:
            codec = _state(request, "internal_context_codec", lambda: InternalContextCodec(configured.internal_context_secret, audience=configured.internal_context_audience))
            verified = codec.verify(internal_context, expected_method=request.method, expected_path=request.url.path)
            if verified.session_id != session_id and x_session_id:
                raise _unauthorized("Internal session binding is invalid.")
            request.state.internal_context = verified
            request.state.actor_scope = verified.actor
            return verified.actor
        except InternalContextError as exc:
            raise _unauthorized("Invalid internal actor context.") from exc

    if cookie_token:
        try:
            scope = _session_codec(request).decode(cookie_token)
            if _registry(request).is_revoked(scope.session_id):
                raise InvalidSession("revoked")
            require_csrf(request.method, cookie_token, csrf_cookie, csrf_header, csrf=_csrf_codec(request), session_id=scope.session_id)
        except CsrfError as exc:
            raise HTTPException(status_code=403, detail="CSRF validation failed.") from exc
        except (InvalidSession, ValueError) as exc:
            raise _unauthorized("Invalid session.") from exc
        request.state.actor_scope = scope
        return scope

    if authorization:
        scheme, separator, token = authorization.partition(" ")
        if not separator or scheme.lower() != "bearer" or not token:
            raise _unauthorized("Use a bearer token.")
        if configured.bearer_token and hmac.compare_digest(token, configured.bearer_token):
            scope = _legacy_service_scope(request, session_id)
            request.state.actor_scope = scope
            return scope
        if not configured.session_configured:
            if configured.bearer_token:
                raise _unauthorized("Invalid bearer token.")
            raise HTTPException(status_code=503, detail="Authentication is unavailable.")
        try:
            scope = _session_codec(request).decode(token)
            if _registry(request).is_revoked(scope.session_id):
                raise InvalidSession("revoked")
        except (InvalidSession, ValueError) as exc:
            raise _unauthorized("Invalid bearer token.") from exc
        request.state.actor_scope = scope
        return scope

    if configured.auth_required:
        raise _unauthorized()

    scope = _development_scope(request, session_id)
    request.state.actor_scope = scope
    return scope


async def require_web_session(
    request: Request,
    authorization: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
    internal_context: str | None = Header(default=None, alias="X-Internal-Actor-Context"),
) -> AuthenticatedSession:
    actor = await require_actor_scope(request, authorization, x_session_id, internal_context)
    source = "internal" if internal_context else "cookie" if request.cookies.get(request.app.state.settings.session_cookie_name) else "bearer" if authorization else "development"
    return AuthenticatedSession(mode="development" if actor.sub.startswith("dev-") else "authenticated", session_id=actor.session_id, actor=actor, token_source=source)


def validate_session_id(value: str | None, fallback: str) -> str:
    session_id = value or fallback
    if not _SESSION_ID.fullmatch(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID.")
    return session_id
