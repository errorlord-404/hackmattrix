from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def _client(tmp_dir: str) -> TestClient:
    settings.FARM_STATE_DB_DIR = tmp_dir
    return TestClient(app)


def _boundary() -> dict:
    return {"type": "Polygon", "coordinates": [[[73.8, 18.5], [73.81, 18.5], [73.81, 18.51], [73.8, 18.5]]]}


def test_authenticated_telemetry_persists_valid_samples_and_replays_sequence(monkeypatch):
    with TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "DEVICE_INGESTION_CREDENTIALS_JSON", '{"soil-node-a17f":{"token":"test-secret","farmer_id":"farmer_a","field_ids":["field-1"]}}')
        client = _client(tmp)
        field = client.post("/v1/fields", headers={"X-Farmer-ID": "farmer_a"}, json={
            "id": "ignored", "name": "North", "area_acres": 2, "boundary_geojson": _boundary(),
        }).json()
        # Credentials deliberately use the actual farmer field ID, never an arbitrary device-supplied scope.
        monkeypatch.setattr(settings, "DEVICE_INGESTION_CREDENTIALS_JSON", '{{"soil-node-a17f":{{"token":"test-secret","farmer_id":"farmer_a","field_ids":["{}"]}}}}'.format(field["id"]))
        payload = {
            "device_id": "soil-node-a17f", "field_id": field["id"], "boot_id": "boot-001", "sequence": 1,
            "observed_at": "2026-09-07T10:20:30Z", "firmware_version": "0.1.0",
            "samples": [
                {"probe_id": "sen0604-01", "measurement": "moisture", "value": 31.4, "unit": "percent", "modbus_address": 1, "crc_ok": True},
                {"probe_id": "sen0605-02", "measurement": "nitrogen", "value": 55, "unit": "mg/kg", "modbus_address": 2, "crc_ok": False},
            ], "transport": {"rssi_dbm": -67, "queued_seconds": 0},
        }
        headers = {"Authorization": "Bearer test-secret"}
        first = client.post("/v1/device-ingestion/observations", headers=headers, json=payload)
        replay = client.post("/v1/device-ingestion/observations", headers=headers, json=payload)
        assert first.status_code == replay.status_code == 201
        assert first.json()["accepted_sample_count"] == 1
        assert first.json()["rejected_sample_count"] == 1
        assert replay.json()["packet_id"] == first.json()["packet_id"]
        readings = client.get(f"/v1/fields/{field['id']}/observations/latest", headers={"X-Farmer-ID": "farmer_a"}).json()
        assert readings[0]["measurement"] == "moisture"
        assert readings[0]["unit"] == "%"
        health = client.get("/v1/device-ingestion/devices", headers={"X-Farmer-ID": "farmer_a"})
        assert health.status_code == 200
        assert health.json()[0]["device_id"] == "soil-node-a17f"
        client.close()


def test_device_ingestion_rejects_unprovisioned_or_forbidden_field(monkeypatch):
    with TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "DEVICE_INGESTION_CREDENTIALS_JSON", "{}")
        client = _client(tmp)
        payload = {"device_id": "unknown-node", "field_id": "field-1", "boot_id": "boot-001", "sequence": 1,
                   "observed_at": "2026-09-07T10:20:30Z", "firmware_version": "0.1.0",
                   "samples": [{"probe_id": "probe", "measurement": "moisture", "value": 31, "unit": "%", "modbus_address": 1, "crc_ok": True}]}
        response = client.post("/v1/device-ingestion/observations", headers={"Authorization": "Bearer nope"}, json=payload)
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "device_not_provisioned"
        client.close()
