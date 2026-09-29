from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import ServiceSettings


def _client(tmp_path) -> TestClient:
    from app.core import config

    config.settings.farm_state_db_dir = tmp_path / "db"
    config.settings.farm_state_upload_dir = tmp_path / "uploads"
    return TestClient(create_app(ServiceSettings(dev_mode=True)))


def test_image_requires_owned_field_and_returns_truthful_inconclusive_result(tmp_path) -> None:
    client = _client(tmp_path)
    field = client.post("/v1/fields", json={"name": "North", "area_acres": 1.0, "boundary_geojson": {"type": "Polygon", "coordinates": [[[77.0, 28.0], [77.1, 28.0], [77.1, 28.1], [77.0, 28.0]]]}, "current_crop": "rice"})
    assert field.status_code == 201
    field_id = field.json()["id"]
    image = client.post("/v1/media/image", content=b"\x89PNG\r\n\x1a\nplaceholder", headers={"Content-Type": "image/png", "X-Field-ID": field_id, "X-Crop-Name": "rice", "Idempotency-Key": "image-request-1"})
    assert image.status_code == 200
    assert image.json()["status"] == "inconclusive"
    assert image.json()["code"] == "cv_release_unavailable"
    assert image.json()["diagnosis"] is None


def test_image_rejects_magic_byte_mismatch_and_voice_is_explicitly_unavailable(tmp_path) -> None:
    client = _client(tmp_path)
    mismatch = client.post("/v1/media/image", content=b"not-an-image", headers={"Content-Type": "image/png", "X-Field-ID": "missing", "X-Crop-Name": "rice"})
    assert mismatch.status_code == 404
    voice = client.post("/v1/media/voice", content=b"RIFF\x00\x00\x00\x00WAVE", headers={"Content-Type": "audio/wav", "Idempotency-Key": "voice-request-1", "Accept-Language": "hi-IN"})
    assert voice.status_code == 200
    assert voice.json()["status"] == "unavailable"
    assert voice.json()["transcript"] is None


def test_image_idempotency_replays_authoritative_result(tmp_path) -> None:
    client = _client(tmp_path)
    field = client.post("/v1/fields", json={"name": "South", "area_acres": 1.0, "boundary_geojson": {"type": "Polygon", "coordinates": [[[77.0, 28.0], [77.1, 28.0], [77.1, 28.1], [77.0, 28.0]]]}, "current_crop": "wheat"}).json()
    headers = {"Content-Type": "image/png", "X-Field-ID": field["id"], "X-Crop-Name": "wheat", "Idempotency-Key": "image-request-2"}
    first = client.post("/v1/media/image", content=b"\x89PNG\r\n\x1a\nfirst", headers=headers)
    second = client.post("/v1/media/image", content=b"\x89PNG\r\n\x1a\nfirst", headers=headers)
    assert first.json() == second.json()
