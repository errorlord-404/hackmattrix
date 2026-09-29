from __future__ import annotations

from fastapi.testclient import TestClient
import hashlib

from app.main import create_app


def test_crop_disease_catalogue_is_authenticated_and_available(settings):
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/v1/crop-disease/crops")
    assert response.status_code == 200
    assert "rice" in response.json()["crops"]
    assert "tomato" in response.json()["crops"]


def test_crop_disease_predict_requires_image_content_type(settings):
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.post("/v1/crop-disease/predict?crop=tomato", content=b"not-an-image", headers={"content-type": "application/octet-stream"})
    assert response.status_code == 415


def test_browser_vision_descriptor_fails_closed_without_approved_release(settings):
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/v1/vision/descriptor")
    assert response.status_code == 200
    assert response.json()["activationAllowed"] is False
    assert response.json()["status"] == "unavailable"


def test_browser_candidate_finalization_is_non_authoritative_and_idempotent(settings, tmp_path):
    from app.core import config
    config.settings.farm_state_db_dir = tmp_path / "db"
    config.settings.farm_state_upload_dir = tmp_path / "uploads"
    app = create_app(settings)
    with TestClient(app) as client:
        field = client.post("/v1/fields", json={"name": "Vision", "area_acres": 1.0, "boundary_geojson": {"type": "Polygon", "coordinates": [[[77.0, 28.0], [77.1, 28.0], [77.1, 28.1], [77.0, 28.0]]]}, "current_crop": "tomato"}).json()
        image = b"\x89PNG\r\n\x1a\nvision"
        uploaded = client.post("/v1/media/image", content=image, headers={"Content-Type": "image/png", "X-Field-ID": field["id"], "X-Crop-Name": "tomato"}).json()
        body = {"upload_id": uploaded["upload_id"], "content_sha256": hashlib.sha256(image).hexdigest(), "release_id": "research-candidate", "preprocessing_version": "candidate-v1", "candidate": {"label": "Tomato___healthy"}}
        headers = {"X-Field-ID": field["id"], "X-Crop-Name": "tomato", "Idempotency-Key": "vision-finalize-1"}
        first = client.post("/v1/vision/finalize", json=body, headers=headers)
        second = client.post("/v1/vision/finalize", json=body, headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["authoritative"] is False
    assert first.json()["status"] == "needs_expert_review"
