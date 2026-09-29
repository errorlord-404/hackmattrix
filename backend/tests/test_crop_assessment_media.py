from __future__ import annotations

from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.routers import assistants as assistants_router


def _client(directory: str) -> TestClient:
    settings.FARM_STATE_DB_DIR = directory
    settings.FARM_STATE_UPLOAD_DIR = directory
    return TestClient(app)


def _field(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/v1/fields", headers=headers, json={
        "name": "Tomato plot", "area_acres": 1,
        "boundary_geojson": {"type": "Polygon", "coordinates": [[[73.8, 18.5], [73.81, 18.5], [73.81, 18.51], [73.8, 18.5]]]},
        "current_crop": "tomato",
    })
    assert response.status_code == 201
    return response.json()["id"]


def test_staged_media_requires_matching_approved_consent_for_kindwise(monkeypatch):
    async def fake_provider(_path, crop):
        return {"status": "completed", "provider": "kindwise_crop_health", "crop": crop,
                "label": "early blight", "confidence": 0.8, "disease_candidates": [{"label": "early blight", "score": 0.8}]}

    with TemporaryDirectory() as directory:
        monkeypatch.setattr(settings, "DIAGNOSIS_PROVIDER", "kindwise_crop_health")
        monkeypatch.setattr(assistants_router, "diagnose_image_async", fake_provider)
        client = _client(directory); headers = {"X-Farmer-ID": "demo"}; field_id = _field(client, headers)
        staged = client.post("/v1/media/images", headers=headers, data={"field_id": field_id}, files={"file": ("leaf.png", b"\x89PNG\r\n\x1a\nfixture", "image/png")})
        assert staged.status_code == 201
        upload_id = staged.json()["upload_id"]
        denied = client.post("/v1/diagnoses/from-upload", headers=headers, json={"upload_id": upload_id, "consent_receipt_id": "missing", "confirmed_crop": "tomato"})
        assert denied.status_code == 403
        consent = client.post(f"/v1/media/images/{upload_id}/consents", headers=headers, json={"provider": "kindwise_crop_health", "decision": "approved"})
        assert consent.status_code == 201
        diagnosis = client.post("/v1/diagnoses/from-upload", headers=headers, json={"upload_id": upload_id, "consent_receipt_id": consent.json()["consent_receipt_id"], "confirmed_crop": "tomato"})
        assert diagnosis.status_code == 201
        body = diagnosis.json()
        assert body["label"] == "early blight"
        assert body["context_snapshot"]["field_id"] == field_id
        assert body["evidence"]["context"] == []
        client.close()


def test_staged_media_is_farmer_namespace_scoped():
    with TemporaryDirectory() as directory:
        client = _client(directory); farmer_a = {"X-Farmer-ID": "farmer_a"}; farmer_b = {"X-Farmer-ID": "farmer_b"}
        upload = client.post("/v1/media/images", headers=farmer_a, files={"file": ("leaf.png", b"\x89PNG\r\n\x1a\nfixture", "image/png")})
        assert upload.status_code == 201
        assert client.post(f"/v1/media/images/{upload.json()['upload_id']}/consents", headers=farmer_b, json={"provider": "kindwise_crop_health", "decision": "approved"}).status_code == 404
        client.close()


def test_direct_upload_cannot_bypass_hosted_provider_consent(monkeypatch):
    async def provider_should_not_run(*_args):
        raise AssertionError("hosted provider must not receive direct upload")

    with TemporaryDirectory() as directory:
        monkeypatch.setattr(settings, "DIAGNOSIS_PROVIDER", "kindwise_crop_health")
        monkeypatch.setattr(assistants_router, "diagnose_image_async", provider_should_not_run)
        client = _client(directory)
        response = client.post("/v1/diagnoses", headers={"X-Farmer-ID": "demo"}, files={"file": ("leaf.png", b"\x89PNG\r\n\x1a\nfixture", "image/png")})
        assert response.status_code == 409
        assert "consent" in response.json()["detail"]
        client.close()
