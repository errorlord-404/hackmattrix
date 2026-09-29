from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient

from app.core import config
from app.main import create_app


def _setup_app(settings, tmp_path):
    config.settings.farm_state_db_dir = tmp_path / "db"
    config.settings.farm_state_upload_dir = tmp_path / "uploads"
    return create_app(settings)


def _field(client: TestClient) -> dict:
    response = client.post(
        "/v1/fields",
        json={
            "name": "Vision field",
            "area_acres": 1.0,
            "boundary_geojson": {"type": "Polygon", "coordinates": [[[77.0, 28.0], [77.1, 28.0], [77.1, 28.1], [77.0, 28.0]]]},
            "current_crop": "tomato",
        },
    )
    assert response.status_code == 201
    return response.json()


def _candidate(client: TestClient, field_id: str, image: bytes = b"\x89PNG\r\n\x1a\nvision") -> tuple[dict, dict]:
    uploaded = client.post(
        "/v1/media/image",
        content=image,
        headers={"Content-Type": "image/png", "X-Field-ID": field_id, "X-Crop-Name": "tomato"},
    )
    assert uploaded.status_code == 200
    upload = uploaded.json()
    body = {
        "upload_id": upload["upload_id"],
        "content_sha256": hashlib.sha256(image).hexdigest(),
        "release_id": "research-candidate",
        "preprocessing_version": "candidate-v1",
        "candidate": {"label": "Tomato___healthy"},
    }
    return body, upload


def test_candidate_checksum_mismatch_is_rejected(settings, tmp_path):
    app = _setup_app(settings, tmp_path)
    with TestClient(app) as client:
        field = _field(client)
        body, _ = _candidate(client, field["id"])
        body["content_sha256"] = "0" * 64
        response = client.post(
            "/v1/vision/finalize",
            json=body,
            headers={"X-Field-ID": field["id"], "X-Crop-Name": "tomato", "Idempotency-Key": "vision-checksum-1"},
        )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "upload_checksum_mismatch"


def test_candidate_replay_is_non_authoritative_and_idempotent(settings, tmp_path):
    app = _setup_app(settings, tmp_path)
    with TestClient(app) as client:
        field = _field(client)
        body, _ = _candidate(client, field["id"])
        headers = {"X-Field-ID": field["id"], "X-Crop-Name": "tomato", "Idempotency-Key": "vision-replay-1"}
        first = client.post("/v1/vision/finalize", json=body, headers=headers)
        second = client.post("/v1/vision/finalize", json=body, headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["authoritative"] is False
    assert first.json()["status"] == "needs_expert_review"
