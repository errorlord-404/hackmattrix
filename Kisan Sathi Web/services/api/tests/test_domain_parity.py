from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.farm_state.store import FarmStateStore, get_idempotent_response, request_hash
from app.main import create_app
from app.routers.domain import get_farm_store
from app.settings import ServiceSettings


@pytest.fixture()
def store(tmp_path):
    value = FarmStateStore(farmer_id="farmer-a", tenant_id="tenant-a", db_dir=tmp_path / "db")
    yield value
    value.close()


@pytest.fixture()
def client(store):
    app = create_app(ServiceSettings(dev_mode=True))
    app.dependency_overrides[get_farm_store] = lambda: store
    with TestClient(app) as value:
        yield value


def test_store_contract_hash_is_canonical_and_scoped(store):
    assert request_hash({"b": 2, "a": 1}) == request_hash({"a": 1, "b": 2})
    store.execute("INSERT INTO idempotency_records(key,request_hash,response_status,response_body,created_at) VALUES(?,?,?,?,?)", ("contract-key", request_hash({"a": 1}), 201, '{"id":"one"}', "2026-01-01T00:00:00Z"))
    assert get_idempotent_response(store, "contract-key", {"a": 1}) == {"id": "one"}
    with pytest.raises(ValueError, match="different request"):
        get_idempotent_response(store, "contract-key", {"a": 2})


def test_profile_field_and_observation_writes_replay_authoritative_records(client):
    profile = {"name": "Asha", "preferred_language": "en", "notification_preferences": {"enabled": True, "channels": ["in_app"]}}
    first = client.put("/v1/profile", headers={"Idempotency-Key": "profile-001"}, json=profile)
    replay = client.put("/v1/profile", headers={"Idempotency-Key": "profile-001"}, json=profile)
    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()
    field_payload = {"name": "North", "area_acres": 2, "boundary_geojson": {"type": "Polygon", "coordinates": [[[73.8, 18.5], [73.9, 18.5], [73.9, 18.6], [73.8, 18.5]]]}}
    field = client.post("/v1/fields", headers={"Idempotency-Key": "field-001"}, json=field_payload)
    assert field.status_code == 201
    reading = {"field_id": field.json()["id"], "measurement": "moisture", "value": 12, "unit": "%", "observed_at": "2026-01-01T00:00:00Z", "source": "test"}
    first_reading = client.post("/v1/sensor-readings", headers={"Idempotency-Key": "reading-001"}, json=reading)
    replay_reading = client.post("/v1/sensor-readings", headers={"Idempotency-Key": "reading-001"}, json=reading)
    assert first_reading.json() == replay_reading.json()
    assert client.get("/v1/fields/%s/irrigation-plan" % field.json()["id"]).json()["status"] == "recommended"
    assert client.get("/v1/alerts").json()[0]["kind"] == "low_moisture"


def test_changed_idempotency_payload_is_conflict_and_invalid_boundary_is_validation_error(client):
    assert client.put("/v1/profile", headers={"Idempotency-Key": "profile-002"}, json={"name": "Asha"}).status_code == 200
    conflict = client.put("/v1/profile", headers={"Idempotency-Key": "profile-002"}, json={"name": "Ravi"})
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "idempotency_key_conflict"
    invalid = client.post("/v1/fields", json={"name": "bad", "area_acres": 1, "boundary_geojson": {"type": "Point", "coordinates": [1, 2]}})
    assert invalid.status_code == 422


def test_legacy_farmer_header_is_not_a_store_selector_and_safety_routes_are_absent(client):
    rejected = client.get("/v1/storage-status", headers={"X-Farmer-ID": "another-farmer"})
    assert rejected.status_code == 400
    assert rejected.json()["detail"]["code"] == "legacy_identity_selector_rejected"
    assert client.post("/v1/pump/start").status_code == 404
    assert client.post("/v1/payments").status_code == 404


def test_reference_routes_are_explicitly_degraded_without_mongo(client):
    response = client.get("/crops")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "reference_database_unavailable"
