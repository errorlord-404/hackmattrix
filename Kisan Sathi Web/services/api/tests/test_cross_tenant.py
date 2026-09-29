from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import ServiceSettings


def _cookies(response) -> dict[str, str]:
    return {name: value for name, value in re.findall(r"(kisansathi_(?:session|csrf))=([^;]+)", response.headers.get("set-cookie", ""))}


def _headers(cookies: dict[str, str], *, unsafe: bool = False) -> dict[str, str]:
    headers = {"Cookie": "; ".join(f"{key}={value}" for key, value in cookies.items())}
    if unsafe:
        headers["X-CSRF-Token"] = cookies["kisansathi_csrf"]
    return headers


def _login(client: TestClient, tenant: str, farmer: str) -> dict[str, str]:
    response = client.post("/auth/test/login", json={"sub": f"user-{farmer}", "tenant_id": tenant, "farmer_id": farmer, "session_id": f"session-{farmer}"})
    assert response.status_code == 200
    return _cookies(response)


def test_claim_scoped_store_prevents_cross_tenant_field_reads_and_writes(tmp_path, monkeypatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "farm_state_db_dir", tmp_path / "db")
    monkeypatch.setattr(config.settings, "farm_state_upload_dir", tmp_path / "uploads")
    client = TestClient(create_app(ServiceSettings(dev_mode=True, auth_mode="test")))
    actor_a = _login(client, "tenant-a", "farmer-a")
    field = client.post("/v1/fields", headers={**_headers(actor_a, unsafe=True), "Idempotency-Key": "tenant-a-field"}, json={"name": "A field", "area_acres": 2, "boundary_geojson": {"type": "Polygon", "coordinates": [[[73.8, 18.5], [73.9, 18.5], [73.9, 18.6], [73.8, 18.5]]]}})
    assert field.status_code == 201
    field_id = field.json()["id"]

    actor_b = _login(client, "tenant-b", "farmer-b")
    assert client.get("/v1/fields", headers=_headers(actor_b)).json() == []
    assert client.get(f"/v1/fields/{field_id}", headers=_headers(actor_b)).status_code == 404
    assert client.patch(f"/v1/fields/{field_id}", headers={**_headers(actor_b, unsafe=True), "Idempotency-Key": "tenant-b-update"}, json={"name": "attacker"}).status_code == 404
    assert client.get("/v1/fields", headers=_headers(actor_a)).json()[0]["id"] == field_id


def test_legacy_identity_headers_are_rejected_even_with_authenticated_scope() -> None:
    client = TestClient(create_app(ServiceSettings(dev_mode=True, auth_mode="test")))
    cookies = _login(client, "tenant-a", "farmer-a")
    response = client.get("/v1/fields", headers={**_headers(cookies), "X-Farmer-ID": "farmer-attacker"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "legacy_identity_selector_rejected"
    assert client.get("/v1/fields?farmer_id=farmer-attacker", headers=_headers(cookies)).status_code == 400
