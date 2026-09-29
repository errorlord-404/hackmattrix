from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.auth.internal_context import InternalContextCodec
from app.main import create_app
from app.settings import ServiceSettings
from kisansathi_auth.claims import ActorScope


def _cookies(response) -> dict[str, str]:
    return {name: value for name, value in re.findall(r"(kisansathi_(?:session|csrf))=([^;]+)", response.headers.get("set-cookie", ""))}


def _headers(cookies: dict[str, str], *, csrf: bool = False) -> dict[str, str]:
    value = {"Cookie": "; ".join(f"{key}={item}" for key, item in cookies.items())}
    if csrf:
        value["X-CSRF-Token"] = cookies["kisansathi_csrf"]
    return value


def test_test_issuer_is_mode_gated_and_session_does_not_expose_tokens() -> None:
    client = TestClient(create_app(ServiceSettings(dev_mode=True, auth_mode="test")))
    response = client.post("/auth/test/login", json={"sub": "user-a", "tenant_id": "tenant-a", "farmer_id": "farmer-a", "session_id": "session-a"})
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "Secure" in response.headers["set-cookie"]
    cookies = _cookies(response)
    status = client.get("/auth/session", headers=_headers(cookies))
    assert status.status_code == 200
    assert status.json()["actor"] == {"sub": "user-a", "tenant_id": "tenant-a", "farmer_id": "farmer-a", "roles": ["farmer"]}
    assert "eyJ" not in status.text

    disabled = TestClient(create_app(ServiceSettings(dev_mode=True, auth_mode="")))
    assert disabled.post("/auth/test/login", json={}).status_code == 404


def test_cookie_mutation_requires_csrf_and_logout_revokes_session() -> None:
    client = TestClient(create_app(ServiceSettings(dev_mode=True, auth_mode="test")))
    cookies = _cookies(client.post("/auth/test/login", json={"session_id": "session-csrf"}))
    without_csrf = client.post("/auth/logout", headers=_headers(cookies))
    assert without_csrf.status_code == 403
    logout = client.post("/auth/logout", headers=_headers(cookies, csrf=True))
    assert logout.status_code == 204
    assert client.get("/auth/session", headers=_headers(cookies)).status_code == 401


def test_production_startup_fails_closed_without_oidc_and_secrets() -> None:
    with pytest.raises(RuntimeError, match="Production startup requires OIDC"):
        create_app(ServiceSettings(environment="production"))


def test_signed_internal_context_requires_valid_trace_and_signature() -> None:
    secret = "internal-context-secret-that-is-long-enough"
    settings = ServiceSettings(dev_mode=False, internal_context_secret=secret)
    client = TestClient(create_app(settings))
    actor = ActorScope("harness-a", "tenant-a", "farmer-a", ("farmer",), "session-harness")
    codec = InternalContextCodec(secret)
    token = codec.issue(actor, request_id="request-a", session_id="session-harness", turn_id="turn-a", tool_call_id="call-a", method="GET", path="/auth/session")
    response = client.get("/auth/session", headers={"X-Internal-Actor-Context": token, "X-Session-ID": "session-harness"})
    assert response.status_code == 200
    assert response.json()["actor"]["farmer_id"] == "farmer-a"
    assert client.get("/auth/session", headers={"X-Internal-Actor-Context": token, "X-Session-ID": "session-harness"}).status_code == 401
