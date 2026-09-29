from tempfile import TemporaryDirectory
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import sqlite3
import json
from uuid import uuid4
from pathlib import Path
import hashlib

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.routers import assistants as assistants_router
from app.routers import weather as weather_router
from app.services import sarvam


def _client(tmp_dir: str) -> TestClient:
    settings.FARM_STATE_DB_DIR = tmp_dir
    settings.FARM_STATE_UPLOAD_DIR = tmp_dir
    return TestClient(app)


def _boundary() -> dict:
    return {"type": "Polygon", "coordinates": [[[73.8, 18.5], [73.81, 18.5], [73.81, 18.51], [73.8, 18.5]]]}


def _boundary_at(lon: float, lat: float) -> dict:
    return {"type": "Polygon", "coordinates": [[[lon, lat], [lon + 0.01, lat], [lon + 0.01, lat + 0.01], [lon, lat]]]}


def test_harvest_lot_is_farmer_scoped_idempotent_and_final_harvest_closes_cycle():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        farmer = {"X-Farmer-ID": "harvest_farmer"}
        other = {"X-Farmer-ID": "other_harvest_farmer"}
        field = client.post("/v1/fields", headers=farmer, json={
            "name": "Harvest field", "area_acres": 2, "boundary_geojson": _boundary(),
        }).json()
        planted = datetime.now(timezone.utc) - timedelta(days=30)
        cycle = client.post(f"/v1/fields/{field['id']}/crop-cycles", headers=farmer, json={
            "crop_name": "Tomato", "planted_at": planted.isoformat(),
        }).json()
        path = f"/v1/crop-cycles/{cycle['id']}/harvest-lots"
        body = {
            "harvested_on": datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat(),
            "quantity": 120, "unit": "kg", "grade": "A", "storage_note": "Cool shed",
            "final_harvest": True,
        }
        assert client.post(path, headers=farmer, json=body).status_code == 400
        headers = {**farmer, "Idempotency-Key": "harvest-event-001"}
        created = client.post(path, headers=headers, json=body)
        assert created.status_code == 201
        lot = created.json()
        assert lot["source"] == "farmer_reported"
        assert lot["crop_name"] == "Tomato"
        assert lot["quantity"] == 120
        assert lot["final_harvest"] is True
        replay = client.post(path, headers=headers, json=body)
        assert replay.status_code == 201
        assert replay.json()["id"] == lot["id"]
        assert client.post(path, headers=headers, json={**body, "quantity": 121}).status_code == 409
        assert client.post(path, headers={**farmer, "Idempotency-Key": "harvest-event-002"}, json=body).status_code == 409
        listed = client.get(f"/v1/fields/{field['id']}/harvest-lots", headers=farmer)
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()] == [lot["id"]]
        assert client.get(f"/v1/fields/{field['id']}/harvest-lots", headers=other).status_code == 404
        assert client.post(path, headers={**other, "Idempotency-Key": "harvest-other-001"}, json=body).status_code == 404
        timeline = client.get(f"/v1/fields/{field['id']}/timeline", headers=farmer).json()
        assert timeline[0]["status"] == "harvested"
        assert timeline[0]["current_stage"] == "harvest"
        client.close()


def test_harvest_lot_rejects_implausible_dates_and_quantity():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        farmer = {"X-Farmer-ID": "harvest_validation"}
        headers = {**farmer, "Idempotency-Key": "harvest-validation-001"}
        field = client.post("/v1/fields", headers=farmer, json={
            "name": "Field", "area_acres": 1, "boundary_geojson": _boundary(),
        }).json()
        planted = datetime.now(timezone.utc) - timedelta(days=10)
        cycle = client.post(f"/v1/fields/{field['id']}/crop-cycles", headers=farmer, json={
            "crop_name": "Wheat", "planted_at": planted.isoformat(),
        }).json()
        path = f"/v1/crop-cycles/{cycle['id']}/harvest-lots"
        base = {"quantity": 10, "unit": "quintal"}
        assert client.post(path, headers=headers, json={**base, "harvested_on": (planted - timedelta(days=1)).date().isoformat()}).status_code == 422
        assert client.post(path, headers=headers, json={**base, "harvested_on": (datetime.now(ZoneInfo("Asia/Kolkata")) + timedelta(days=2)).date().isoformat()}).status_code == 422
        assert client.post(path, headers=headers, json={**base, "quantity": 0, "harvested_on": datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()}).status_code == 422
        assert client.get(f"/v1/fields/{field['id']}/harvest-lots", headers=headers).json() == []
        client.close()


def test_farmer_databases_are_isolated():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        created = client.post("/v1/fields", headers={"X-Farmer-ID": "farmer_a"}, json={
            "name": "A field", "area_acres": 2, "boundary_geojson": _boundary(),
        })
        assert created.status_code == 201
        assert client.get("/v1/fields", headers={"X-Farmer-ID": "farmer_a"}).json()
        assert client.get("/v1/fields", headers={"X-Farmer-ID": "farmer_b"}).json() == []


def test_storage_status_uses_the_farmer_scoped_sqlite_store():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        response = client.get("/v1/storage-status", headers={"X-Farmer-ID": "farmer_a"})
        assert response.status_code == 200
        assert response.json()["farmer_id"] == "farmer_a"
        assert response.json()["farm_state"] == "available"
        assert response.json()["farm_state_store"] == "server_local_sqlite"
        client.close()


def test_confirmed_field_task_creates_one_farmer_visible_alert():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        farmer = {"X-Farmer-ID": "task_alert_farmer"}
        headers = {**farmer, "Idempotency-Key": "task-alert-001"}
        field = client.post("/v1/fields", headers=farmer, json={
            "name": "Task field", "area_acres": 1, "boundary_geojson": _boundary(),
        }).json()
        body = {"field_id": field["id"], "title": "Inspect leaf damage", "source": "farmer_confirmed:agent"}
        created = client.post("/v1/tasks", headers=headers, json=body)
        assert created.status_code == 201
        alerts = client.get("/v1/alerts?status=open", headers=headers).json()
        assert len(alerts) == 1
        assert alerts[0]["kind"] == "field_task_created"
        assert alerts[0]["title"] == "New field action"
        assert "Inspect leaf damage" in alerts[0]["message"]
        replay = client.post("/v1/tasks", headers=headers, json=body)
        assert replay.status_code == 201
        assert len(client.get("/v1/alerts?status=open", headers=headers).json()) == 1
        assert client.get("/v1/alerts?status=open", headers={"X-Farmer-ID": "other_task_alert_farmer"}).json() == []
        client.close()


def test_forecast_alerts_are_persisted_once_and_keep_read_status(monkeypatch):
    async def fixture_weather(_lat: float, _lon: float) -> dict:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        forecast_day = (now + timedelta(days=1)).date().isoformat()
        return {
            "provider": "weather_fixture",
            "observed_at": now.isoformat(),
            "fetched_at": now.isoformat(),
            "freshness_seconds": 0,
            "current": {},
            "hourly": [],
            "daily": [{"observed_at": forecast_day, "precipitation_probability": 82}],
            "warnings": [],
        }

    monkeypatch.setattr(weather_router, "fetch_weather", fixture_weather)
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "forecast_farmer"}
        field = client.post("/v1/fields", headers=headers, json={
            "name": "Forecast field", "area_acres": 1, "boundary_geojson": _boundary(),
        }).json()

        first = client.get(f"/v1/weather/alerts?field_id={field['id']}", headers=headers)
        assert first.status_code == 200
        assert len(first.json()) == 1
        alerts = client.get("/v1/alerts?status=open", headers=headers).json()
        assert len(alerts) == 1
        assert alerts[0]["kind"] == "heavy_rain_probability"
        assert alerts[0]["source"] == "weather_fixture"

        client.patch(f"/v1/alerts/{alerts[0]['id']}", headers={**headers, "Idempotency-Key": "forecast-read-001"}, json={"status": "read"})
        replay = client.get(f"/v1/weather/alerts?field_id={field['id']}", headers=headers)
        assert replay.status_code == 200
        assert client.get("/v1/alerts?status=open", headers=headers).json() == []
        assert len(client.get("/v1/alerts?status=read", headers=headers).json()) == 1
        client.close()


def test_diagnostics_reports_farmer_counts_without_leaking_paths():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "diagnostic_farmer"}
        created = client.post("/v1/fields", headers=headers, json={
            "name": "Diagnostic field", "area_acres": 1, "boundary_geojson": _boundary(),
        })
        assert created.status_code == 201
        response = client.get("/v1/diagnostics", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["farmer_state"]["fields"] == 1
        assert payload["components"]["farm_state"]["status"] == "available"
        assert "path" not in response.text.lower()
        assert "diagnostic_farmer" not in response.text
        assert response.headers.get("X-Request-ID")
        client.close()


def test_onboarding_status_is_read_only_farmer_scoped_and_tracks_setup_steps():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "onboarding_farmer"}
        other_headers = {"X-Farmer-ID": "other_onboarding_farmer"}

        initial = client.get("/v1/onboarding-status", headers=headers)
        assert initial.status_code == 200
        assert initial.json()["next_setup_step"] == "create_profile"
        assert initial.json()["profile"]["exists"] is False
        assert initial.json()["fields"]["active_count"] == 0
        assert "onboarding_farmer" not in initial.text
        assert "path" not in initial.text.lower()

        assert client.put("/v1/profile", headers=headers, json={"name": "Asha"}).status_code == 200
        assert client.get("/v1/onboarding-status", headers=headers).json()["next_setup_step"] == "set_location"
        assert client.put("/v1/profile", headers=headers, json={
            "name": "Asha", "latitude": 18.5, "longitude": 73.8,
        }).status_code == 200
        assert client.get("/v1/onboarding-status", headers=headers).json()["next_setup_step"] == "create_field"

        approximate = {"type": "Feature", "properties": {"quality": "approximate_point_buffer"}, "geometry": _boundary()}
        created = client.post("/v1/fields", headers=headers, json={
            "name": "East", "area_acres": 2, "boundary_geojson": approximate,
        })
        assert created.status_code == 201
        status = client.get("/v1/onboarding-status", headers=headers).json()
        assert status["next_setup_step"] == "review_boundary"
        assert status["fields"]["approximate_boundaries"] == 1
        assert status["latest_sensor_observed_at"] is None

        drawn = {"type": "Feature", "properties": {"quality": "farmer_drawn_unverified"}, "geometry": _boundary()}
        assert client.patch(f"/v1/fields/{created.json()['id']}", headers=headers, json={
            "boundary_geojson": drawn,
        }).status_code == 200
        assert client.get("/v1/onboarding-status", headers=headers).json()["next_setup_step"] == "choose_crop"
        assert client.patch(f"/v1/fields/{created.json()['id']}", headers=headers, json={
            "current_crop": "Tomato",
        }).status_code == 200
        assert client.get("/v1/onboarding-status", headers=headers).json()["next_setup_step"] == "start_crop_cycle"
        assert client.post(f"/v1/fields/{created.json()['id']}/crop-cycles", headers=headers, json={
            "crop_name": "Tomato", "planted_at": "2026-09-18T06:00:00Z",
        }).status_code == 201
        ready = client.get("/v1/onboarding-status", headers=headers).json()
        assert ready["next_setup_step"] == "ready"
        assert ready["fields"]["with_active_cycle_count"] == 1

        other = client.get("/v1/onboarding-status", headers=other_headers).json()
        assert other["next_setup_step"] == "create_profile"
        assert other["fields"]["active_count"] == 0
        client.close()


def test_export_and_audit_are_farmer_scoped():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "export_farmer"}
        created = client.post("/v1/fields", headers=headers, json={
            "name": "Export field", "area_acres": 1, "boundary_geojson": _boundary(),
        })
        assert created.status_code == 201
        audit = client.get("/v1/audit", headers=headers)
        assert audit.status_code == 200
        assert audit.json()["events"]
        snapshot = client.get("/v1/export", headers=headers)
        assert snapshot.status_code == 200
        assert snapshot.json()["format"] == "kisansathi-farm-export-v1"
        assert snapshot.json()["tables"]["fields"][0]["name"] == "Export field"
        other = client.get("/v1/export", headers={"X-Farmer-ID": "other_export_farmer"}).json()
        assert other["tables"]["fields"] == []
        client.close()


def test_demo_loader_requires_confirmation_and_is_idempotent():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        denied = client.post("/v1/demo/load", headers={"X-Farmer-ID": "demo"})
        assert denied.status_code == 403
        first = client.post("/v1/demo/load", headers={"X-Farmer-ID": "demo", "X-Demo-Confirm": "true"})
        second = client.post("/v1/demo/load", headers={"X-Farmer-ID": "demo", "X-Demo-Confirm": "true"})
        assert first.status_code == second.status_code == 200
        assert first.json()["fields"] == second.json()["fields"] == 2
        other = client.post("/v1/demo/load", headers={"X-Farmer-ID": "other", "X-Demo-Confirm": "true"})
        assert other.status_code == 403
        client.close()


def test_low_moisture_creates_one_deduplicated_alert_and_plan():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "farmer_a"}
        field = client.post("/v1/fields", headers=headers, json={
            "name": "A field", "area_acres": 2, "boundary_geojson": _boundary(),
        }).json()
        field_id = field["id"]
        payload = {
            "field_id": field_id, "measurement": "moisture", "value": 19,
            "unit": "percent", "observed_at": "2026-08-18T00:00:00Z", "source": "sensor:test",
        }
        assert client.post("/v1/sensor-readings", headers=headers, json=payload).status_code == 201
        payload["observed_at"] = "2026-08-18T01:00:00Z"
        assert client.post("/v1/sensor-readings", headers=headers, json=payload).status_code == 201
        alerts = client.get("/v1/alerts", headers=headers).json()
        assert len(alerts) == 1
        plan = client.get(f"/v1/fields/{field_id}/irrigation-plan", headers=headers)
        assert plan.status_code == 200
        assert plan.json()["status"] == "recommended"
        assert "Do not" not in plan.json()["recommendation"]["what"]
        second_plan = client.get(f"/v1/fields/{field_id}/irrigation-plan", headers=headers)
        assert second_plan.status_code == 200
        client.close()
        connection = sqlite3.connect(f"{tmp}/farmer_a.sqlite3")
        try:
            assert connection.execute("SELECT COUNT(*) FROM irrigation_plans").fetchone()[0] == 0
        finally:
            connection.close()


def test_irrigation_plan_uses_only_weather_cached_near_the_requested_field():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "farmer_a"}
        first = client.post("/v1/fields", headers=headers, json={
            "name": "Near field", "area_acres": 2, "boundary_geojson": _boundary_at(73.8, 18.5),
        }).json()
        second = client.post("/v1/fields", headers=headers, json={
            "name": "Far field", "area_acres": 2, "boundary_geojson": _boundary_at(76.8, 21.5),
        }).json()
        assert client.post("/v1/sensor-readings", headers=headers, json={
            "field_id": first["id"], "measurement": "moisture", "value": 31, "unit": "percent",
            "observed_at": "2026-09-07T00:00:00Z", "source": "sensor:test",
        }).status_code == 201
        connection = sqlite3.connect(f"{tmp}/farmer_a.sqlite3")
        try:
            far_payload = json.dumps({"hourly": [{"precipitation_probability": 95}]})
            connection.execute(
                """INSERT INTO weather_snapshots(id, latitude, longitude, provider, observed_at, fetched_at, payload, freshness_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid4()), second["centroid_lat"], second["centroid_lon"], "test", "2026-09-07T00:00:00Z",
                 "2026-09-07T00:00:00Z", far_payload, 900),
            )
            connection.commit()
        finally:
            connection.close()
        no_match = client.get(f"/v1/fields/{first['id']}/irrigation-plan", headers=headers).json()
        assert no_match["status"] == "recommended"
        assert any("No cached weather snapshot matched" in item for item in no_match["assumptions"])
        connection = sqlite3.connect(f"{tmp}/farmer_a.sqlite3")
        try:
            matching_payload = json.dumps({"hourly": [
                {"precipitation_probability": 95, "precipitation_mm": 16},
                {"precipitation_probability": 90, "precipitation_mm": 14},
            ]})
            connection.execute(
                """INSERT INTO weather_snapshots(id, latitude, longitude, provider, observed_at, fetched_at, payload, freshness_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid4()), first["centroid_lat"], first["centroid_lon"], "test", "2026-09-07T01:00:00Z",
                 "2026-09-07T01:00:00Z", matching_payload, 900),
            )
            connection.commit()
        finally:
            connection.close()
        matched = client.get(f"/v1/fields/{first['id']}/irrigation-plan", headers=headers).json()
        assert matched["status"] == "defer_for_heavy_rain"
        assert matched["application_adjustment_percent"] == 0
        assert any("for this field location" in item for item in matched["assumptions"])
        assert any("30.0 mm over the next 48 hours" in item for item in matched["assumptions"])


def test_sensor_reading_idempotency_replays_without_duplicate_readings():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "farmer_a", "Idempotency-Key": "sensor-reading-1"}
        field = client.post("/v1/fields", headers={"X-Farmer-ID": "farmer_a"}, json={
            "name": "A field", "area_acres": 2, "boundary_geojson": _boundary(),
        }).json()
        payload = {
            "field_id": field["id"], "measurement": "moisture", "value": 22,
            "unit": "percent", "observed_at": "2026-08-18T00:00:00Z", "source": "sensor:test",
        }
        first = client.post("/v1/sensor-readings", headers=headers, json=payload)
        second = client.post("/v1/sensor-readings", headers=headers, json=payload)
        assert first.status_code == second.status_code == 201
        assert first.json()["id"] == second.json()["id"]


def test_sensor_reading_normalises_known_units_and_rejects_unknown_moisture_units():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "farmer_a"}
        field = client.post("/v1/fields", headers=headers, json={
            "name": "A field", "area_acres": 2, "boundary_geojson": _boundary(),
        }).json()
        valid = client.post("/v1/sensor-readings", headers=headers, json={
            "field_id": field["id"], "measurement": "moisture", "value": 31,
            "unit": "percent", "observed_at": "2026-09-07T00:00:00Z", "source": "sensor:test",
        })
        assert valid.status_code == 201
        assert valid.json()["unit"] == "%"
        invalid = client.post("/v1/sensor-readings", headers=headers, json={
            "field_id": field["id"], "measurement": "moisture", "value": 31,
            "unit": "raw_adc", "observed_at": "2026-09-07T00:01:00Z", "source": "sensor:test",
        })
        assert invalid.status_code == 422
        assert "compatible with %" in invalid.text


def test_crop_stages_are_normalized_to_the_canonical_lifecycle_keys():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "farmer_a"}
        field = client.post("/v1/fields", headers=headers, json={
            "name": "A field", "area_acres": 2, "boundary_geojson": _boundary(),
        }).json()
        cycle = client.post(f"/v1/fields/{field['id']}/crop-cycles", headers=headers, json={
            "crop_name": "wheat", "planted_at": "2026-09-01T00:00:00Z", "initial_stage": "Grain Filling",
        })
        assert cycle.status_code == 201
        assert cycle.json()["current_stage"] == "grain_filling"
        updated = client.patch(f"/v1/crop-cycles/{cycle.json()['id']}/stage", headers=headers, json={"stage": "Harvesting"})
        assert updated.status_code == 200
        assert updated.json()["current_stage"] == "harvest"
        unsupported = client.patch(f"/v1/crop-cycles/{cycle.json()['id']}/stage", headers=headers, json={"stage": "tuber formation"})
        assert unsupported.status_code == 422


def test_crop_stage_action_proposals_are_reviewable_and_never_create_tasks():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "farmer_a"}
        field = client.post("/v1/fields", headers=headers, json={
            "name": "Action field", "area_acres": 2, "boundary_geojson": _boundary(),
        }).json()
        cycle = client.post(f"/v1/fields/{field['id']}/crop-cycles", headers=headers, json={
            "crop_name": "tomato", "planted_at": "2026-09-01T00:00:00Z", "initial_stage": "flowering",
        }).json()
        proposed = client.get(f"/v1/fields/{field['id']}/action-proposals", headers=headers)
        assert proposed.status_code == 200
        item = proposed.json()[0]
        assert item["crop_cycle_id"] == cycle["id"]
        assert item["stage"] == "flowering"
        assert item["requires_farmer_confirmation"] is True
        assert client.get(f"/v1/tasks?field_id={field['id']}&status=open", headers=headers).json() == []
        client.post("/v1/tasks", headers=headers, json={"field_id": field["id"], "title": item["title"]})
        assert client.get(f"/v1/fields/{field['id']}/action-proposals", headers=headers).json() == []


def test_farmer_confirmed_field_tasks_persist_and_can_be_completed_idempotently():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "farmer_a", "Idempotency-Key": "task-create-1"}
        field = client.post("/v1/fields", headers={"X-Farmer-ID": "farmer_a"}, json={
            "name": "A field", "area_acres": 2, "boundary_geojson": _boundary(),
        }).json()
        payload = {
            "field_id": field["id"], "title": "Inspect leaf photos", "due_at": "2026-09-08T06:00:00Z",
            "source": "farmer_confirmed:crop_health",
        }
        created = client.post("/v1/tasks", headers=headers, json=payload)
        replay = client.post("/v1/tasks", headers=headers, json=payload)
        assert created.status_code == replay.status_code == 201
        assert created.json()["id"] == replay.json()["id"]
        task_id = created.json()["id"]
        listed = client.get(f"/v1/tasks?field_id={field['id']}&status=open", headers={"X-Farmer-ID": "farmer_a"})
        assert [item["id"] for item in listed.json()] == [task_id]
        completion_headers = {"X-Farmer-ID": "farmer_a", "Idempotency-Key": "task-complete-1"}
        completed = client.patch(f"/v1/tasks/{task_id}", headers=completion_headers, json={"status": "completed"})
        completion_replay = client.patch(f"/v1/tasks/{task_id}", headers=completion_headers, json={"status": "completed"})
        assert completed.status_code == completion_replay.status_code == 200
        assert completed.json()["status"] == "completed"
        assert client.get("/v1/tasks?status=open", headers={"X-Farmer-ID": "farmer_a"}).json() == []


def test_farmer_ledger_is_scoped_summarised_and_voided_without_deleting_history():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        farmer_headers = {"X-Farmer-ID": "farmer_a"}
        field = client.post("/v1/fields", headers=farmer_headers, json={
            "name": "Ledger field", "area_acres": 2, "boundary_geojson": _boundary(),
        }).json()
        expense = {
            "field_id": field["id"], "entry_type": "expense", "category": "Seed", "title": "Tomato seed",
            "amount_inr": 820, "occurred_at": "2026-09-07", "crop_name": "tomato", "source": "farmer_confirmed",
        }
        created = client.post("/v1/ledger/entries", headers={**farmer_headers, "Idempotency-Key": "ledger-entry-1"}, json=expense)
        replay = client.post("/v1/ledger/entries", headers={**farmer_headers, "Idempotency-Key": "ledger-entry-1"}, json=expense)
        assert created.status_code == replay.status_code == 201
        assert created.json()["id"] == replay.json()["id"]
        income = client.post("/v1/ledger/entries", headers=farmer_headers, json={
            "entry_type": "income", "category": "Sale", "title": "Mandi sale", "amount_inr": 2500,
            "occurred_at": "2026-09-08", "source": "farmer_confirmed",
        })
        assert income.status_code == 201
        summary = client.get("/v1/ledger/summary", headers=farmer_headers).json()
        assert summary == {
            "currency": "INR", "income_inr": 2500.0, "expense_inr": 820.0, "balance_inr": 1680.0,
            "active_entry_count": 2,
            "assumptions": [
                "Totals include only active farmer-entered INR ledger records.",
                "This is a record-keeping summary, not a financial forecast, tax statement, or credit decision.",
            ],
        }
        voided = client.patch(
            f"/v1/ledger/entries/{created.json()['id']}",
            headers={**farmer_headers, "Idempotency-Key": "ledger-void-1"}, json={"status": "void"},
        )
        assert voided.status_code == 200
        assert voided.json()["status"] == "void"
        assert client.get("/v1/ledger/entries", headers=farmer_headers).json() == [income.json()]
        assert client.get("/v1/ledger/entries?status=void", headers=farmer_headers).json()[0]["id"] == created.json()["id"]
        assert client.get("/v1/ledger/summary", headers=farmer_headers).json()["balance_inr"] == 2500.0
        assert client.get("/v1/ledger/entries", headers={"X-Farmer-ID": "farmer_b"}).json() == []


def test_irrigation_plan_rejects_legacy_non_percent_moisture_value():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "farmer_a"}
        field = client.post("/v1/fields", headers=headers, json={
            "name": "A field", "area_acres": 2, "boundary_geojson": _boundary(),
        }).json()
        connection = sqlite3.connect(f"{tmp}/farmer_a.sqlite3")
        try:
            connection.execute(
                """INSERT INTO sensor_readings(id, field_id, device_id, measurement, value, unit, observed_at, source, fetched_at, confidence)
                VALUES (?, ?, NULL, 'moisture', ?, ?, ?, ?, ?, NULL)""",
                ("legacy-moisture", field["id"], 19, "raw_adc", "2026-09-07T00:00:00Z", "legacy-device", "2026-09-07T00:00:00Z"),
            )
            connection.commit()
        finally:
            connection.close()
        plan = client.get(f"/v1/fields/{field['id']}/irrigation-plan", headers=headers).json()
        assert plan["status"] == "insufficient_data"
        assert any("not a verified percentage" in item for item in plan["assumptions"])


def test_irrigation_event_history_is_farmer_and_field_scoped():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "farmer_a", "Idempotency-Key": "irrigation-event-1"}
        field = client.post("/v1/fields", headers={"X-Farmer-ID": "farmer_a"}, json={
            "name": "A field", "area_acres": 2, "boundary_geojson": _boundary(),
        }).json()
        created = client.post("/v1/irrigation-events", headers=headers, json={
            "field_id": field["id"], "occurred_at": "2026-09-08T06:00:00Z", "method": "farmer_confirmed",
        })
        assert created.status_code == 201
        history = client.get(f"/v1/irrigation-events?field_id={field['id']}", headers={"X-Farmer-ID": "farmer_a"})
        assert history.status_code == 200
        assert history.json()[0]["id"] == created.json()["id"]
        assert history.json()[0]["method"] == "farmer_confirmed"
        assert client.get("/v1/irrigation-events", headers={"X-Farmer-ID": "farmer_b"}).json() == []


def test_diagnosis_reports_provider_unavailable_when_provider_is_unconfigured():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "farmer_a", "Idempotency-Key": "diagnosis-upload-1"}
        response = client.post("/v1/diagnoses", headers=headers, files={
            "file": ("leaf.png", b"\x89PNG\r\n\x1a\nfixture", "image/png"),
        })
        assert response.status_code == 201
        assert response.json()["status"] == "provider_unavailable"
        assert response.json()["label"] is None
        assert response.json()["crop"] is None
        replay = client.post("/v1/diagnoses", headers=headers, files={
            "file": ("leaf.png", b"\x89PNG\r\n\x1a\nfixture", "image/png"),
        })
        assert replay.status_code == 201
        assert replay.json()["id"] == response.json()["id"]


def test_diagnosis_upload_preserves_trailing_image_bytes_and_is_farmer_scoped():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        image = b"\x89PNG\r\n\x1a\nfixture\r\n-\r\n"
        response = client.post("/v1/diagnoses", headers={"X-Farmer-ID": "farmer_a"}, files={
            "file": ("leaf.png", image, "image/png"),
        })
        assert response.status_code == 201
        diagnosis_id = response.json()["id"]
        assert (Path(tmp) / "farmer_a" / f"{diagnosis_id}.png").read_bytes() == image
        connection = sqlite3.connect(Path(tmp) / "farmer_a.sqlite3")
        try:
            checksum = connection.execute(
                "SELECT checksum FROM diagnosis_images WHERE request_id = ?", (diagnosis_id,)
            ).fetchone()[0]
        finally:
            connection.close()
        assert checksum == hashlib.sha256(image).hexdigest()
        assert client.get(f"/v1/diagnoses/{diagnosis_id}", headers={"X-Farmer-ID": "farmer_b"}).status_code == 404


def test_diagnosis_forwards_confirmed_crop_and_persists_model_evidence(monkeypatch):
    seen = {}

    def fake_diagnose(path, confirmed_crop):
        seen["path"] = path
        seen["crop"] = confirmed_crop
        return {
            "status": "completed", "label": "healthy", "confidence": 0.91,
            "provider": "local_hierarchical_demo", "crop": confirmed_crop,
            "model_id": "test-router", "model_version": "test-v1",
            "inference_location": "local-server", "disease_candidates": [{"label": "healthy", "score": 0.91}],
            "model_evidence": [{"model_id": "test-router", "status": "ok"}],
            "limitations": ["test-only"],
        }

    with TemporaryDirectory() as tmp:
        monkeypatch.setattr(assistants_router, "diagnose_image", fake_diagnose)
        client = _client(tmp)
        response = client.post("/v1/diagnoses", headers={"X-Farmer-ID": "farmer_a"}, data={"confirmed_crop": "tomato"}, files={
            "file": ("leaf.png", b"\x89PNG\r\n\x1a\nfixture", "image/png"),
        })
        assert response.status_code == 201
        payload = response.json()
        assert seen["crop"] == "tomato"
        assert payload["label"] == "healthy"
        assert payload["candidates"] == [{"label": "healthy", "score": 0.91}]
        assert payload["model_evidence"] == [{"model_id": "test-router", "status": "ok"}]
        assert payload["model_id"] == "test-router"


def test_diagnosis_feedback_is_consented_farmer_review_not_training_approval():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        created = client.post("/v1/diagnoses", headers={"X-Farmer-ID": "farmer_a"}, files={
            "file": ("leaf.png", b"\x89PNG\r\n\x1a\nfixture", "image/png"),
        })
        assert created.status_code == 201
        diagnosis_id = created.json()["id"]
        payload = {"correctness": "corrected", "confirmed_crop": "tomato", "label": "late_blight", "share_for_model_improvement": True}
        headers = {"X-Farmer-ID": "farmer_a", "Idempotency-Key": "diagnosis-feedback-1"}
        feedback = client.post(f"/v1/diagnoses/{diagnosis_id}/feedback", headers=headers, json=payload)
        assert feedback.status_code == 201
        assert feedback.json()["reviewer_type"] == "farmer"
        assert feedback.json()["share_for_model_improvement"] is True
        assert feedback.json()["training_eligibility"] == "requires_expert_review_and_separate_export"
        replay = client.post(f"/v1/diagnoses/{diagnosis_id}/feedback", headers=headers, json=payload)
        assert replay.status_code == 201
        assert replay.json()["id"] == feedback.json()["id"]
        assert client.post(f"/v1/diagnoses/{diagnosis_id}/feedback", headers={"X-Farmer-ID": "farmer_b"}, json=payload).status_code == 404


def test_weather_provider_failure_is_explicitly_unavailable(monkeypatch):
    with TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "WEATHER_PROVIDER", "disabled")
        client = _client(tmp)
        response = client.get("/v1/weather?lat=18.5&lon=73.8", headers={"X-Farmer-ID": "farmer_a"})
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "weather_provider_unavailable"


def test_idempotency_replays_profile_update_without_duplicate_effects():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "farmer_a", "Idempotency-Key": "profile-update-1"}
        payload = {"name": "Asha", "preferred_language": "hi"}
        first = client.put("/v1/profile", headers=headers, json=payload)
        second = client.put("/v1/profile", headers=headers, json=payload)
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["farmer_id"] == first.json()["farmer_id"]
        assert second.json()["updated_at"] == first.json()["updated_at"]


def test_idempotency_rejects_reusing_a_key_for_different_payload():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "farmer_a", "Idempotency-Key": "profile-update-2"}
        assert client.put("/v1/profile", headers=headers, json={"name": "Asha"}).status_code == 200
        conflict = client.put("/v1/profile", headers=headers, json={"name": "Ravi"})
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["code"] == "idempotency_key_conflict"


def test_sarvam_voice_tts_and_translation_contracts(monkeypatch):
    with TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "SARVAM_API_KEY", "test-key")
        monkeypatch.setattr(settings, "VOICE_PROVIDER", "sarvam")
        monkeypatch.setattr(
            assistants_router,
            "transcribe_audio",
            lambda audio, **kwargs: {"request_id": "stt-1", "transcript": "नमस्ते", "language_code": "hi-IN"},
        )
        monkeypatch.setattr(
            assistants_router,
            "synthesize_speech",
            lambda text, **kwargs: {"request_id": "tts-1", "audio_base64": "UklGRg=="},
        )
        monkeypatch.setattr(
            sarvam,
            "translate_text",
            lambda text, **kwargs: {
                "request_id": "translate-1",
                "translated_text": "Hello",
                "source_language_code": "hi-IN",
            },
        )
        client = _client(tmp)
        headers = {"X-Farmer-ID": "farmer_a", "Content-Type": "audio/webm"}
        transcribed = client.post("/v1/voice/transcribe?language_code=hi-IN", headers=headers, content=b"audio")
        assert transcribed.status_code == 200
        assert transcribed.json()["transcript"] == "नमस्ते"
        synthesized = client.post("/v1/voice/synthesize", headers={"X-Farmer-ID": "farmer_a"}, json={
            "text": "नमस्ते", "language_code": "hi-IN",
        })
        assert synthesized.status_code == 200
        assert synthesized.json()["audio_base64"] == "UklGRg=="
        translated = client.post("/v1/translate", headers={"X-Farmer-ID": "farmer_a"}, json={
            "input": "नमस्ते", "source_language_code": "hi-IN", "target_language_code": "en-IN",
        })
        assert translated.status_code == 200
        assert translated.json()["translated_text"] == "Hello"
        turn = client.post("/v1/voice/turns", headers=headers, content=b"audio")
        assert turn.status_code == 200
        assert turn.json()["status"] == "completed"
        assert turn.json()["audio_base64"] == "UklGRg=="
