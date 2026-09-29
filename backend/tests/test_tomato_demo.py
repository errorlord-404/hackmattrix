from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def _boundary(offset: float = 0) -> dict:
    return {"type": "Polygon", "coordinates": [[[73.8 + offset, 18.5], [73.81 + offset, 18.5], [73.81 + offset, 18.51], [73.8 + offset, 18.5]]]}


def test_tomato_demo_publishes_dynamic_source_labelled_values_and_irrigation_transition(monkeypatch):
    with TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "FARM_STATE_DB_DIR", tmp)
        monkeypatch.setattr(settings, "TOMATO_DEMO_ENABLED", True)
        client = TestClient(app)
        field = client.post("/v1/fields", headers={"X-Farmer-ID": "demo"}, json={"name": "Tomato", "area_acres": 1, "boundary_geojson": _boundary()}).json()
        field_id = field["id"]

        started = client.post(f"/v1/fields/{field_id}/tomato-demo/start", headers={"X-Farmer-ID": "demo"}, json={"scenario": "water-stress", "seed": 7})
        assert started.status_code == 200
        assert started.json()["running"] is True
        assert len(started.json()["observations"]) == 7
        assert {item["source"] for item in started.json()["observations"]} == {"simulation:tomato-demo:v1"}
        first_moisture = next(item["value"] for item in started.json()["observations"] if item["measurement"] == "moisture")

        ticked = client.post(f"/v1/fields/{field_id}/tomato-demo/tick", headers={"X-Farmer-ID": "demo"})
        assert ticked.json()["tick_count"] == 1
        ticked_moisture = next(item["value"] for item in ticked.json()["observations"] if item["measurement"] == "moisture")
        assert ticked_moisture < first_moisture

        client.post(f"/v1/fields/{field_id}/tomato-demo/irrigate", headers={"X-Farmer-ID": "demo"})
        irrigated = client.post(f"/v1/fields/{field_id}/tomato-demo/tick", headers={"X-Farmer-ID": "demo"})
        irrigated_moisture = next(item["value"] for item in irrigated.json()["observations"] if item["measurement"] == "moisture")
        assert irrigated_moisture > ticked_moisture

        latest = client.get(f"/v1/fields/{field_id}/observations/latest", headers={"X-Farmer-ID": "demo"})
        assert len(latest.json()) == 7
        assert all(item["source"] == "simulation:tomato-demo:v1" for item in latest.json())
        client.close()


def test_tomato_demo_is_field_scoped_and_stops_advancing(monkeypatch):
    with TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "FARM_STATE_DB_DIR", tmp)
        monkeypatch.setattr(settings, "TOMATO_DEMO_ENABLED", True)
        client = TestClient(app)
        headers = {"X-Farmer-ID": "demo"}
        first = client.post("/v1/fields", headers=headers, json={"name": "One", "area_acres": 1, "boundary_geojson": _boundary()}).json()
        second = client.post("/v1/fields", headers=headers, json={"name": "Two", "area_acres": 1, "boundary_geojson": _boundary(1)}).json()
        client.post(f"/v1/fields/{first['id']}/tomato-demo/start", headers=headers, json={"scenario": "nitrogen-low", "seed": 1})
        assert client.get(f"/v1/fields/{second['id']}/tomato-demo", headers=headers).json()["running"] is False

        stopped = client.post(f"/v1/fields/{first['id']}/tomato-demo/stop", headers=headers).json()
        assert stopped["running"] is False
        frozen = client.post(f"/v1/fields/{first['id']}/tomato-demo/tick", headers=headers).json()
        assert frozen["tick_count"] == 0
        client.close()


def test_tomato_demo_is_disabled_by_default(monkeypatch):
    with TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "FARM_STATE_DB_DIR", tmp)
        monkeypatch.setattr(settings, "TOMATO_DEMO_ENABLED", False)
        client = TestClient(app)
        field = client.post("/v1/fields", headers={"X-Farmer-ID": "demo"}, json={"name": "Tomato", "area_acres": 1, "boundary_geojson": _boundary()}).json()
        status = client.get(f"/v1/fields/{field['id']}/tomato-demo", headers={"X-Farmer-ID": "demo"})
        assert status.status_code == 200
        assert status.json()["enabled"] is False
        start = client.post(f"/v1/fields/{field['id']}/tomato-demo/start", headers={"X-Farmer-ID": "demo"}, json={"scenario": "balanced"})
        assert start.status_code == 404
        client.close()


def test_tomato_demo_heavy_rain_fixture_is_labelled_and_changes_only_its_field_plan(monkeypatch):
    with TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "FARM_STATE_DB_DIR", tmp)
        monkeypatch.setattr(settings, "TOMATO_DEMO_ENABLED", True)
        client = TestClient(app)
        headers = {"X-Farmer-ID": "demo"}
        first = client.post("/v1/fields", headers=headers, json={"name": "Tomato one", "area_acres": 1, "boundary_geojson": _boundary()}).json()
        second = client.post("/v1/fields", headers=headers, json={"name": "Tomato two", "area_acres": 1, "boundary_geojson": _boundary(1)}).json()
        client.post(f"/v1/fields/{first['id']}/tomato-demo/start", headers=headers, json={"scenario": "water-stress"})
        client.post(f"/v1/fields/{second['id']}/tomato-demo/start", headers=headers, json={"scenario": "water-stress"})

        fixture = client.post(f"/v1/fields/{first['id']}/tomato-demo/weather-fixture", headers=headers, json={"scenario": "heavy-rain"})
        assert fixture.status_code == 200
        assert fixture.json()["forecast_fixture"] == "heavy-rain"
        first_plan = client.get(f"/v1/fields/{first['id']}/irrigation-plan", headers=headers).json()
        assert first_plan["status"] == "defer_for_heavy_rain"
        assert any("simulation:tomato-weather-fixture" in item for item in first_plan["assumptions"])
        assert client.get(f"/v1/fields/{second['id']}/irrigation-plan", headers=headers).json()["status"] == "recommended"

        cleared = client.post(f"/v1/fields/{first['id']}/tomato-demo/weather-fixture", headers=headers, json={"scenario": "clear"})
        assert cleared.status_code == 200
        assert cleared.json()["forecast_fixture"] is None
        client.close()
