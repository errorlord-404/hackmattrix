"""Populate the local SQLite store for the ``demo`` farmer with labelled UI fixtures.

The values exercise prototype screens only. They are explicitly local demo data,
not observations from hardware, an agronomist prescription, or a farm ledger.
The script uses the public REST contract and can safely be rerun.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from urllib.error import HTTPError
from urllib.request import Request, urlopen


API = f"{os.getenv('KISANSATHI_FARM_STATE_API_URL', os.getenv('KISANSATHI_BACKEND_URL', 'http://127.0.0.1:8001')).rstrip('/')}/v1"
FARMER_ID = "demo"
SOURCE = "local_demo_farmer_seed_not_live"
OBSERVED_AT = "2026-09-09T08:00:00+00:00"


def request(method: str, path: str, payload: dict | None = None, key: str | None = None):
    headers = {"X-Farmer-ID": FARMER_ID, "Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if key:
        headers["Idempotency-Key"] = key
    try:
        with urlopen(Request(f"{API}{path}", data=data, headers=headers, method=method), timeout=10) as response:
            return json.loads(response.read().decode())
    except HTTPError as error:
        body = error.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} failed ({error.code}): {body}") from error


def post_once(path: str, payload: dict, key: str):
    return request("POST", path, payload, key)


def main() -> None:
    try:
        profile = request("GET", "/profile")
    except RuntimeError as error:
        if "(404)" not in str(error):
            raise
        profile = {}
    request(
        "PUT", "/profile",
        {
            "name": "Demo Farmer",
            "phone": profile.get("phone"),
            "location": "Pune, Maharashtra (local demo)",
            "preferred_language": "en",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "notification_preferences": {"enabled": True, "channels": ["in_app"]},
        },
        "local-demo-profile-v1",
    )
    fields = request("GET", "/fields")
    if not fields:
        fields = [
            request("POST", "/fields", {
                "name": "Upper Field", "area_acres": 2.0,
                "boundary_geojson": {"type": "Polygon", "coordinates": [[[73.8500, 18.5200], [73.8540, 18.5200], [73.8540, 18.5240], [73.8500, 18.5240], [73.8500, 18.5200]]]},
                "current_crop": None,
            }),
            request("POST", "/fields", {
                "name": "Lower Field", "area_acres": 1.5,
                "boundary_geojson": {"type": "Polygon", "coordinates": [[[73.8620, 18.5260], [73.8660, 18.5260], [73.8660, 18.5300], [73.8620, 18.5300], [73.8620, 18.5260]]]},
                "current_crop": None,
            }),
        ]
    elif not any(item.get("name") == "Lower Field" for item in fields):
        fields.append(request("POST", "/fields", {
            "name": "Lower Field", "area_acres": 1.5,
            "boundary_geojson": {"type": "Polygon", "coordinates": [[[73.8620, 18.5260], [73.8660, 18.5260], [73.8660, 18.5300], [73.8620, 18.5300], [73.8620, 18.5260]]] },
            "current_crop": None,
        }))
    field = fields[0]
    field_id = field["id"]
    crop = "Paddy (local demo reference)"
    request("PATCH", f"/fields/{field_id}", {"current_crop": crop}, "local-demo-field-crop-v1")

    timeline = request("GET", f"/fields/{field_id}/timeline")
    if not any(item.get("crop_name") == crop and item.get("status") == "active" for item in timeline):
        post_once(
            f"/fields/{field_id}/crop-cycles",
            {"crop_name": crop, "planted_at": OBSERVED_AT, "initial_stage": "vegetative"},
            "local-demo-crop-cycle-v1",
        )

    soil = request("GET", f"/fields/{field_id}/soil-health")
    if (soil.get("latest_test") or {}).get("source") != SOURCE:
        post_once(
            f"/fields/{field_id}/soil-tests",
            {
                "observed_at": OBSERVED_AT, "ph": 6.7, "organic_carbon": 0.62,
                "nitrogen": 280, "phosphorus": 22, "potassium": 185, "ec": 0.42,
                "moisture_percent": 34, "source": SOURCE, "confidence": 0.0,
            },
            "local-demo-soil-test-v1",
        )

    measurements = [
        ("moisture", 34.0, "%"), ("temperature", 26.0, "°C"),
        ("humidity", 61.0, "%"), ("ph", 6.7, "pH"), ("ec", 0.42, "mS/cm"),
        ("nitrogen", 280.0, "mg/kg"), ("phosphorus", 22.0, "mg/kg"), ("potassium", 185.0, "mg/kg"),
    ]
    latest = {item["measurement"]: item for item in request("GET", f"/fields/{field_id}/observations/latest")}
    for measurement, value, unit in measurements:
        if latest.get(measurement, {}).get("source") == SOURCE:
            continue
        post_once(
            "/sensor-readings",
            {"field_id": field_id, "measurement": measurement,
             "value": value, "unit": unit, "observed_at": OBSERVED_AT, "source": SOURCE, "confidence": 0.0},
            f"local-demo-sensor-{measurement}-v1",
        )

    tasks = request("GET", f"/tasks?field_id={field_id}")
    if not any(item["title"] == "Demo: inspect crop canopy (not a field instruction)" for item in tasks):
        post_once(
            "/tasks",
            {"field_id": field_id, "title": "Demo: inspect crop canopy (not a field instruction)",
             "source": SOURCE},
            "local-demo-task-v1",
        )
    reminders = request("GET", "/reminders")
    if not any(item["title"] == "Demo: review soil readings" for item in reminders):
        post_once(
            "/reminders",
            {"field_id": field_id, "reminder_type": "review", "scheduled_for": "2026-09-10T08:00:00+00:00",
             "title": "Demo: review soil readings"},
            "local-demo-reminder-v1",
        )
    entries = request("GET", f"/ledger/entries?field_id={field_id}")
    ledger_records = [
        ("expense", "inputs", "Demo: seed-input record (not a transaction)", 1200.0),
        ("income", "sale", "Demo: harvest-income record (not a sale)", 2400.0),
    ]
    known_titles = {item["title"] for item in entries}
    for entry_type, category, title, amount in ledger_records:
        if title in known_titles:
            continue
        post_once(
            "/ledger/entries",
            {"field_id": field_id, "entry_type": entry_type, "category": category, "title": title,
             "amount_inr": amount, "occurred_at": str(date.today()), "crop_name": crop,
             "note": "LOCAL DEMO FIXTURE ONLY — not a financial transaction.", "source": SOURCE},
            f"local-demo-ledger-{entry_type}-v1",
        )
    print(f"Local demo farmer data is ready for field {field['name']} ({field_id}).")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Demo farmer seed failed: {error}", file=sys.stderr)
        raise SystemExit(1)
