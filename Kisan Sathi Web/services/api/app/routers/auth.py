from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from kisansathi_auth.claims import ActorScope
from kisansathi_auth.oidc import AuthorizationStateStore, OIDCConfig, OIDCVerifier, OIDCVerificationError

from app.auth.dependencies import AuthenticatedSession, _csrf_codec, _registry, _session_codec, require_web_session
from app.auth.test_issuer import issue_scope


router = APIRouter(prefix="/auth", tags=["auth"])


class TestLoginRequest(BaseModel):
    sub: str = Field(default="test-user")
    tenant_id: str = Field(default="test-tenant")
    farmer_id: str = Field(default="test-farmer")
    roles: tuple[str, ...] = ("farmer",)
    session_id: str | None = None


def _state_store(request: Request) -> AuthorizationStateStore:
    value = getattr(request.app.state, "oidc_state_store", None)
    if value is None:
        value = AuthorizationStateStore(ttl_seconds=300)
        request.app.state.oidc_state_store = value
    return value


def _verifier(request: Request) -> OIDCVerifier:
    configured = request.app.state.settings
    if not configured.oidc_configured:
        raise HTTPException(status_code=503, detail="OIDC authentication is not configured.")
    value = getattr(request.app.state, "oidc_verifier", None)
    if value is None:
        value = OIDCVerifier(OIDCConfig(issuer=configured.oidc_issuer, audience=configured.oidc_audience, client_id=configured.oidc_client_id, client_secret=configured.oidc_client_secret, redirect_uri=configured.oidc_redirect_uri, discovery_url=configured.oidc_discovery_url or None, algorithms=configured.oidc_algorithms))
        request.app.state.oidc_verifier = value
    return value


def _redirect_target(request: Request) -> str:
    configured = request.app.state.settings.frontend_origin or "/"
    if configured.startswith("/"):
        return configured
    parsed = urlparse(configured)
    return configured if parsed.scheme in {"http", "https"} and parsed.netloc else "/"


def _set_session(response: Response, request: Request, scope: ActorScope) -> None:
    configured = request.app.state.settings
    session = _session_codec(request)
    csrf = _csrf_codec(request).issue(scope.session_id)
    response.set_cookie(configured.session_cookie_name, session.encode(scope), **session.cookie_kwargs())
    response.set_cookie(configured.csrf_cookie_name, csrf, httponly=False, secure=True, samesite="lax", path="/", max_age=configured.csrf_ttl_seconds)


@router.get("/login")
def login(request: Request) -> Response:
    configured = request.app.state.settings
    if configured.test_issuer_enabled and not configured.oidc_configured:
        return JSONResponse({"mode": "test", "test_login": "/auth/test/login", "provider": "local-test-issuer"})
    pending = _state_store(request).create(redirect_uri=configured.oidc_redirect_uri)
    try:
        target = _verifier(request).authorization_url(pending)
    except OIDCVerificationError as exc:
        raise HTTPException(status_code=503, detail="OIDC provider discovery is unavailable.") from exc
    response = RedirectResponse(target, status_code=307)
    response.set_cookie(configured.auth_state_cookie_name, pending.state, httponly=True, secure=True, samesite="lax", path="/auth", max_age=300)
    return response


@router.get("/callback")
def callback(request: Request, code: str = Query(..., min_length=1, max_length=4096), state: str = Query(..., min_length=1, max_length=512)) -> Response:
    configured = request.app.state.settings
    state_cookie = request.cookies.get(configured.auth_state_cookie_name)
    if not state_cookie or state_cookie != state:
        raise HTTPException(status_code=400, detail="Invalid authentication state.")
    try:
        pending = _state_store(request).consume(state)
        verifier = _verifier(request)
        token_response = verifier.exchange_code(code, pending)
        scope = verifier.verify_id_token(token_response["id_token"], nonce=pending.nonce)
    except (KeyError, OIDCVerificationError) as exc:
        raise HTTPException(status_code=400, detail="Authentication callback could not be verified.") from exc
    response = RedirectResponse(_redirect_target(request), status_code=303)
    _set_session(response, request, scope)
    response.delete_cookie(configured.auth_state_cookie_name, path="/auth")
    return response


@router.post("/test/login")
def test_login(request: Request, payload: TestLoginRequest) -> Response:
    configured = request.app.state.settings
    try:
        scope = issue_scope(configured, sub=payload.sub, tenant_id=payload.tenant_id, farmer_id=payload.farmer_id, roles=payload.roles, session_id=payload.session_id)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail="Not found.") from exc
    response = JSONResponse({"status": "authenticated", "actor": {"sub": scope.sub, "tenant_id": scope.tenant_id, "farmer_id": scope.farmer_id, "roles": list(scope.roles)}})
    _set_session(response, request, scope)
    return response


@router.get("/session")
def session_status(authenticated: AuthenticatedSession = Depends(require_web_session)) -> dict[str, Any]:
    actor = authenticated.actor
    return {"authenticated": True, "mode": authenticated.mode, "token_source": authenticated.token_source, "actor": {"sub": actor.sub, "tenant_id": actor.tenant_id, "farmer_id": actor.farmer_id, "roles": list(actor.roles)}, "capabilities": {"can_use_tools": True}}


@router.post("/logout")
def logout(request: Request, response: Response, authenticated: AuthenticatedSession = Depends(require_web_session)) -> Response:
    cookie_token = request.cookies.get(request.app.state.settings.session_cookie_name)
    if cookie_token:
        _registry(request).revoke(authenticated.session_id)
    response.delete_cookie(request.app.state.settings.session_cookie_name, path="/")
    response.delete_cookie(request.app.state.settings.csrf_cookie_name, path="/")
    response.delete_cookie(request.app.state.settings.auth_state_cookie_name, path="/auth")
    response.status_code = 204
    return response
