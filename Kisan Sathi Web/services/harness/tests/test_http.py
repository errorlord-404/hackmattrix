from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import HarnessSettings, create_app
from kisansathi_auth.claims import ActorScope
from kisansathi_auth.csrf import CsrfTokenCodec
from kisansathi_auth.session import SessionCodec


def _client() -> tuple[TestClient, str]:
    settings = HarnessSettings(
        environment="development",
        session_secret="development-session-secret-change-me-32",
        csrf_secret="development-csrf-secret-change-me-32",
        session_kid="primary",
        session_ttl_seconds=3600,
        csrf_ttl_seconds=3600,
        provider_configured=False,
        provider_error="provider is not configured",
        event_store_path=None,
    )
    client = TestClient(create_app(settings))
    actor = ActorScope("user-1", "tenant-1", "farmer-1", ("farmer",), "session-1")
    session = SessionCodec({"primary": settings.session_secret}, active_kid="primary").encode(actor)
    csrf = CsrfTokenCodec(settings.csrf_secret).issue(actor.session_id)
    client.cookies.set("kisansathi_session", session)
    client.cookies.set("kisansathi_csrf", csrf)
    return client, csrf


def test_harness_health_and_authenticated_turn():
    client, csrf = _client()
    assert client.get("/healthz").json()["status"] == "ok"
    assert client.get("/readyz").json()["status"] == "ready"

    created = client.post("/sessions", headers={"X-CSRF-Token": csrf})
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    streamed = client.post(
        f"/sessions/{session_id}/turns",
        headers={"X-CSRF-Token": csrf},
        json={"messages": [{"role": "user", "content": "hello"}]},
    )
    assert streamed.status_code == 200
    events = [json.loads(line) for line in streamed.text.splitlines() if line]
    assert events[-1]["kind"] == "turnCompleted"
    assert events[-1]["payload"]["status"] == "ok"


def test_harness_rejects_missing_session_cookie():
    client = TestClient(create_app())
    response = client.get("/capabilities")
    assert response.status_code == 401
