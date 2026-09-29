from __future__ import annotations

import json
from datetime import date, datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status

from app.core.config import settings
from app.farm_state.dependencies import get_farm_store
from app.farm_state.rules import crop_stage_action_proposals, irrigation_rule, soil_interpretation
from app.services.tomato_simulator import SOURCE as TOMATO_DEMO_SOURCE
from app.services.tomato_simulator import TICK_INTERVAL_SECONDS, advance_values, initial_values, observations as tomato_observations
from app.models.crop import Crop
from app.models.market_price import MarketPrice
from app.services.crop_planning import compare_crop_options
from app.farm_state.store import (
    FarmStateStore,
    get_idempotent_response,
    iso_now,
    json_text,
    json_value,
    save_idempotent_response,
)
from app.schemas.farm_state import (
    AlertPatch,
    AlertResponse,
    CropCycleCreate,
    CropCycleResponse,
    CropStageEventResponse,
    CropStageActionProposalResponse,
    CropOptionResponse,
    CropStageUpdate,
    DashboardResponse,
    FieldCreate,
    FieldPatch,
    FieldResponse,
    FieldTaskCreate,
    FieldTaskPatch,
    FieldTaskResponse,
    HarvestLotCreate,
    HarvestLotResponse,
    LedgerEntryCreate,
    LedgerEntryPatch,
    LedgerEntryResponse,
    LedgerSummaryResponse,
    IrrigationEventCreate,
    IrrigationEventResponse,
    IrrigationPlanResponse,
    MapFieldResponse,
    ProfileResponse,
    ProfileUpdate,
    Recommendation,
    ReminderCreate,
    ReminderResponse,
    ReportCreate,
    ReportResponse,
    SensorReadingCreate,
    SoilHealthResponse,
    SoilTestCreate,
    SoilTestResponse,
    StorageStatusResponse,
    ObservationResponse,
    TomatoDemoResponse,
    TomatoDemoStart,
    TomatoDemoWeatherFixture,
)

router = APIRouter(prefix="/v1", tags=["farm-state"])
TOMATO_DEMO_WEATHER_SOURCE = "simulation:tomato-weather-fixture:v1"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


@router.get("/storage-status", response_model=StorageStatusResponse)
def get_storage_status(
    request: Request,
    store: FarmStateStore = Depends(get_farm_store),
):
    """Expose the active farmer-store boundary without leaking a filesystem path."""
    return StorageStatusResponse(
        farmer_id=store.farmer_key,
        reference_database="available" if getattr(request.app.state, "reference_db_available", False) else "unavailable",
    )


@router.post("/demo/load")
def load_demo_data(request: Request, store: FarmStateStore = Depends(get_farm_store)):
    """Create the minimal local demo farmer fixture after explicit UI confirmation."""
    if store.farmer_key != "demo" or request.headers.get("X-Demo-Confirm") != "true":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "demo_confirmation_required", "message": "Demo loading is limited to the demo farmer and requires explicit confirmation.", "retryable": False})
    now = iso_now()
    profile = store.one("SELECT id FROM profile WHERE id = ?", (store.farmer_key,))
    if not profile:
        store.execute(
            "INSERT INTO profile(id, name, phone, location, preferred_language, latitude, longitude, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (store.farmer_key, "Demo Farmer", None, "Pune, Maharashtra (local demo)", "en", 18.5204, 73.8567, now, now),
        )
        store.execute("INSERT OR IGNORE INTO preferences(profile_id, notifications_enabled, notification_preferences, updated_at) VALUES (?, 1, ?, ?)", (store.farmer_key, json_text({"enabled": True, "channels": ["in_app"]}), now))
    if not store.one("SELECT id FROM fields WHERE active = 1 LIMIT 1"):
        for field_id, name, area, coordinates in (
            ("demo-upper-field", "Upper Field", 2.0, [[[73.8500, 18.5200], [73.8540, 18.5200], [73.8540, 18.5240], [73.8500, 18.5240], [73.8500, 18.5200]]]),
            ("demo-lower-field", "Lower Field", 1.5, [[[73.8620, 18.5260], [73.8660, 18.5260], [73.8660, 18.5300], [73.8620, 18.5300], [73.8620, 18.5260]]]),
        ):
            boundary = {"type": "Polygon", "coordinates": coordinates}
            ring = coordinates[0]
            lat = sum(point[1] for point in ring) / len(ring)
            lon = sum(point[0] for point in ring) / len(ring)
            store.execute(
                "INSERT INTO fields(id, name, area_acres, boundary_geojson, centroid_lat, centroid_lon, current_crop, status, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
                (field_id, name, area, json_text(boundary), lat, lon, None, "unknown", now, now),
            )
    field_count = store.one("SELECT COUNT(*) AS total FROM fields WHERE active = 1")
    return {"status": "loaded", "farmer_id": store.farmer_key, "fields": int(field_count["total"] if field_count else 0), "message": "Local demo farmer data is ready. Reference records still require the launcher seed."}


@router.get("/audit")
def list_audit_events(limit: int = Query(default=100, ge=1, le=500), store: FarmStateStore = Depends(get_farm_store)):
    """Return an append-only, non-sensitive write history for the active farmer."""
    rows = store.all("SELECT id, action, entity, created_at FROM audit_events ORDER BY created_at DESC LIMIT ?", (limit,))
    return {"events": [dict(row) for row in rows], "retention": "local_farmer_store"}


@router.get("/export")
def export_farmer_snapshot(store: FarmStateStore = Depends(get_farm_store)):
    """Return a bounded JSON backup of farmer-owned state for manual export."""
    tables = (
        "profile", "preferences", "fields", "crop_cycles", "crop_stage_events",
        "field_tasks", "ledger_entries", "soil_tests", "sensor_readings",
        "field_observations", "irrigation_plans", "irrigation_events", "reminders",
        "weather_snapshots", "weather_alerts", "alerts", "audit_events",
    )
    snapshot = {table: [dict(row) for row in store.all(f"SELECT * FROM {table} LIMIT 1000")] for table in tables}
    return {"format": "kisansathi-farm-export-v1", "farmer_id": store.farmer_key, "exported_at": iso_now(), "tables": snapshot}


def _require_field(store: FarmStateStore, field_id: str):
    row = store.one("SELECT * FROM fields WHERE id = ? AND active = 1", (field_id,))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found")
    return row


def _centroid(boundary: dict[str, Any]) -> tuple[float | None, float | None]:
    geometry = boundary.get("geometry", boundary)
    points: list[tuple[float, float]] = []

    def visit(value: Any) -> None:
        if isinstance(value, list) and len(value) >= 2 and all(isinstance(item, (int, float)) for item in value[:2]):
            points.append((float(value[0]), float(value[1])))
            return
        if isinstance(value, list):
            for item in value:
                visit(item)

    visit(geometry.get("coordinates"))
    if not points:
        return None, None
    return sum(point[1] for point in points) / len(points), sum(point[0] for point in points) / len(points)


def _field_response(row) -> FieldResponse:
    return FieldResponse(
        id=row["id"],
        name=row["name"],
        area_acres=row["area_acres"],
        boundary_geojson=json_value(row["boundary_geojson"], {}),
        centroid_lat=row["centroid_lat"],
        centroid_lon=row["centroid_lon"],
        current_crop=row["current_crop"],
        status=row["status"],
        active=bool(row["active"]),
        created_at=_parse_datetime(row["created_at"]),
        updated_at=_parse_datetime(row["updated_at"]),
    )


def _observation_response(row) -> ObservationResponse:
    return ObservationResponse(
        id=row["id"],
        field_id=row["field_id"],
        measurement=row["measurement"],
        value=row["value"],
        unit=row["unit"],
        observed_at=_parse_datetime(row["observed_at"]),
        fetched_at=_parse_datetime(row["fetched_at"]),
        source=row["source"],
        confidence=row["confidence"],
    )


def _tomato_demo_row(store: FarmStateStore, field_id: str):
    return store.one("SELECT * FROM tomato_demo_state WHERE field_id = ?", (field_id,))


def _tomato_demo_response(store: FarmStateStore, field_id: str) -> TomatoDemoResponse:
    if not settings.TOMATO_DEMO_ENABLED:
        return TomatoDemoResponse(enabled=False, field_id=field_id, running=False, source=TOMATO_DEMO_SOURCE)
    row = _tomato_demo_row(store, field_id)
    if not row:
        return TomatoDemoResponse(enabled=settings.TOMATO_DEMO_ENABLED, field_id=field_id, running=False, source=TOMATO_DEMO_SOURCE)
    rows = store.all(
        """SELECT sr.* FROM sensor_readings sr
        JOIN (SELECT measurement, MAX(observed_at) latest FROM sensor_readings
              WHERE field_id = ? AND source = ? GROUP BY measurement) x
          ON x.measurement = sr.measurement AND x.latest = sr.observed_at
        WHERE sr.field_id = ? AND sr.source = ? ORDER BY sr.measurement""",
        (field_id, TOMATO_DEMO_SOURCE, field_id, TOMATO_DEMO_SOURCE),
    )
    fixture = store.one(
        "SELECT provider FROM weather_snapshots WHERE provider LIKE ? ORDER BY fetched_at DESC LIMIT 1",
        (f"{TOMATO_DEMO_WEATHER_SOURCE}:{field_id}:%",),
    )
    fixture_name = fixture["provider"].rsplit(":", 1)[-1] if fixture else None
    return TomatoDemoResponse(
        enabled=settings.TOMATO_DEMO_ENABLED,
        field_id=field_id,
        running=bool(row["running"]),
        scenario=row["scenario"],
        seed=row["seed"],
        tick_count=row["tick_count"],
        irrigation_ticks_remaining=row["irrigation_ticks_remaining"],
        observed_at=_parse_datetime(row["observed_at"]),
        updated_at=_parse_datetime(row["updated_at"]),
        source=TOMATO_DEMO_SOURCE,
        forecast_fixture=fixture_name if fixture_name in {"ordinary-rain", "heavy-rain"} else None,
        observations=[_observation_response(item) for item in rows],
    )


def _require_tomato_demo() -> None:
    if not settings.TOMATO_DEMO_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tomato demo mode is disabled")


def _write_tomato_observations(store: FarmStateStore, field_id: str, values: dict[str, float], observed_at: str) -> None:
    for item in tomato_observations(values):
        store.execute(
            """INSERT INTO sensor_readings(id, field_id, device_id, measurement, value, unit, observed_at, source, fetched_at, confidence)
            VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid4()), field_id, item["measurement"], item["value"], item["unit"], observed_at, TOMATO_DEMO_SOURCE, observed_at, 0.55),
        )


def _advance_tomato_demo(store: FarmStateStore, field_id: str, *, force: bool = False) -> None:
    if not settings.TOMATO_DEMO_ENABLED:
        return
    row = _tomato_demo_row(store, field_id)
    if not row or not row["running"]:
        return
    now_dt = datetime.now(timezone.utc)
    last_tick = _parse_datetime(row["last_tick_at"])
    if not force and last_tick and now_dt - last_tick < timedelta(seconds=TICK_INTERVAL_SECONDS):
        return
    values, remaining = advance_values(
        json_value(row["values_json"], {}), row["scenario"], row["seed"], row["tick_count"] + 1,
        row["irrigation_ticks_remaining"],
    )
    now = now_dt.isoformat().replace("+00:00", "Z")
    _write_tomato_observations(store, field_id, values, now)
    store.execute(
        """UPDATE tomato_demo_state SET values_json = ?, tick_count = ?, irrigation_ticks_remaining = ?,
        observed_at = ?, last_tick_at = ?, updated_at = ? WHERE field_id = ?""",
        (json_text(values), row["tick_count"] + 1, remaining, now, now, now, field_id),
    )


def _soil_response(row) -> SoilTestResponse:
    return SoilTestResponse(
        id=row["id"],
        field_id=row["field_id"],
        observed_at=_parse_datetime(row["observed_at"]),
        ph=row["ph"],
        organic_carbon=row["organic_carbon"],
        nitrogen=row["nitrogen"],
        phosphorus=row["phosphorus"],
        potassium=row["potassium"],
        ec=row["ec"],
        moisture_percent=row["moisture_percent"],
        source=row["source"],
        confidence=row["confidence"],
        fetched_at=_parse_datetime(row["fetched_at"]),
    )


@router.get("/fields/{field_id}/tomato-demo", response_model=TomatoDemoResponse)
def get_tomato_demo(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    """Return the local Tomato simulator state and advance it when a tick is due."""
    _require_field(store, field_id)
    if not settings.TOMATO_DEMO_ENABLED:
        return _tomato_demo_response(store, field_id)
    _advance_tomato_demo(store, field_id)
    return _tomato_demo_response(store, field_id)


@router.post("/fields/{field_id}/tomato-demo/start", response_model=TomatoDemoResponse)
def start_tomato_demo(
    field_id: str,
    payload: TomatoDemoStart,
    store: FarmStateStore = Depends(get_farm_store),
):
    _require_tomato_demo()
    _require_field(store, field_id)
    now = iso_now()
    values = initial_values(payload.scenario, payload.seed)
    store.execute(
        """INSERT INTO tomato_demo_state(field_id, running, scenario, seed, tick_count, values_json,
        irrigation_ticks_remaining, observed_at, last_tick_at, updated_at)
        VALUES (?, 1, ?, ?, 0, ?, 0, ?, ?, ?)
        ON CONFLICT(field_id) DO UPDATE SET running = 1, scenario = excluded.scenario, seed = excluded.seed,
        tick_count = 0, values_json = excluded.values_json, irrigation_ticks_remaining = 0,
        observed_at = excluded.observed_at, last_tick_at = excluded.last_tick_at, updated_at = excluded.updated_at""",
        (field_id, payload.scenario, payload.seed, json_text(values), now, now, now),
    )
    _write_tomato_observations(store, field_id, values, now)
    return _tomato_demo_response(store, field_id)


def _tomato_weather_fixture_payload(scenario: str, now_dt: datetime) -> dict[str, Any]:
    """Create labelled forecast evidence; never represent it as a live provider result."""
    if scenario == "heavy-rain":
        rainfall = [16.0, 14.0]
        probability = [95.0, 90.0]
    else:
        rainfall = [2.0, 1.0]
        probability = [70.0, 60.0]
    hourly = [
        {
            "observed_at": (now_dt + timedelta(hours=index + 1)).isoformat().replace("+00:00", "Z"),
            "precipitation_probability": probability[index],
            "precipitation_mm": rainfall[index],
            "temperature_c": None,
            "weather_code": None,
        }
        for index in range(len(rainfall))
    ]
    now = now_dt.isoformat().replace("+00:00", "Z")
    return {
        "provider": "simulation:tomato-weather-fixture:v1",
        "observed_at": now,
        "fetched_at": now,
        "freshness_seconds": 0,
        "current": {"temperature_c": None, "relative_humidity_percent": None, "precipitation_mm": None, "weather_code": None, "wind_speed_kmh": None},
        "hourly": hourly,
        "daily": [],
        "warnings": ["Demo forecast fixture; not a live weather provider result."],
    }


@router.post("/fields/{field_id}/tomato-demo/weather-fixture", response_model=TomatoDemoResponse)
def set_tomato_demo_weather_fixture(
    field_id: str,
    payload: TomatoDemoWeatherFixture,
    store: FarmStateStore = Depends(get_farm_store),
):
    """Set or clear a field-scoped forecast fixture for a repeatable demo."""
    _require_tomato_demo()
    field = _require_field(store, field_id)
    if field["centroid_lat"] is None or field["centroid_lon"] is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A field boundary is required before setting a weather demo fixture")
    source_prefix = f"{TOMATO_DEMO_WEATHER_SOURCE}:{field_id}:"
    store.execute("DELETE FROM weather_snapshots WHERE provider LIKE ?", (f"{source_prefix}%",))
    if payload.scenario != "clear":
        source = f"{source_prefix}{payload.scenario}"
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat().replace("+00:00", "Z")
        weather_payload = _tomato_weather_fixture_payload(payload.scenario, now_dt)
        weather_payload.update({"latitude": field["centroid_lat"], "longitude": field["centroid_lon"]})
        store.execute(
            """INSERT INTO weather_snapshots(id, latitude, longitude, provider, observed_at, fetched_at, payload, freshness_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid4()), field["centroid_lat"], field["centroid_lon"], source, now, now, json_text(weather_payload), 0),
        )
    return _tomato_demo_response(store, field_id)


@router.post("/fields/{field_id}/tomato-demo/tick", response_model=TomatoDemoResponse)
def tick_tomato_demo(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    _require_tomato_demo()
    _require_field(store, field_id)
    _advance_tomato_demo(store, field_id, force=True)
    return _tomato_demo_response(store, field_id)


@router.post("/fields/{field_id}/tomato-demo/irrigate", response_model=TomatoDemoResponse)
def irrigate_tomato_demo(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    _require_tomato_demo()
    _require_field(store, field_id)
    row = _tomato_demo_row(store, field_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Start Tomato demo mode before simulating irrigation")
    store.execute(
        "UPDATE tomato_demo_state SET irrigation_ticks_remaining = 3, updated_at = ? WHERE field_id = ?",
        (iso_now(), field_id),
    )
    return _tomato_demo_response(store, field_id)


@router.post("/fields/{field_id}/tomato-demo/stop", response_model=TomatoDemoResponse)
def stop_tomato_demo(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    _require_tomato_demo()
    _require_field(store, field_id)
    row = _tomato_demo_row(store, field_id)
    if row:
        store.execute("UPDATE tomato_demo_state SET running = 0, updated_at = ? WHERE field_id = ?", (iso_now(), field_id))
    return _tomato_demo_response(store, field_id)


def _alert_response(row) -> AlertResponse:
    return AlertResponse(
        id=row["id"],
        field_id=row["field_id"],
        kind=row["kind"],
        title=row["title"],
        message=row["message"],
        severity=row["severity"],
        status=row["status"],
        source=row["source"],
        created_at=_parse_datetime(row["created_at"]),
        updated_at=_parse_datetime(row["updated_at"]),
    )


def _upsert_alert(
    store: FarmStateStore,
    *,
    field_id: str | None,
    kind: str,
    title: str,
    message: str,
    severity: str,
    dedupe_key: str,
    source: str,
) -> None:
    now = iso_now()
    store.execute(
        """
        INSERT INTO alerts(id, field_id, kind, title, message, severity, status, dedupe_key, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?)
        ON CONFLICT(dedupe_key) DO UPDATE SET
            message=excluded.message, severity=excluded.severity, updated_at=excluded.updated_at
        """,
        (str(uuid4()), field_id, kind, title, message, severity, dedupe_key, source, now, now),
    )


@router.get("/profile", response_model=ProfileResponse)
def get_profile(store: FarmStateStore = Depends(get_farm_store)):
    row = store.one(
        """
        SELECT p.*, COALESCE(pref.notifications_enabled, 1) AS notifications_enabled,
               COALESCE(pref.notification_preferences, '{}') AS notification_preferences
        FROM profile p LEFT JOIN preferences pref ON pref.profile_id = p.id WHERE p.id = ?
        """,
        (store.farmer_key,),
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    preferences = json_value(row["notification_preferences"], {})
    return ProfileResponse(
        farmer_id=row["id"],
        name=row["name"],
        phone=row["phone"],
        location=row["location"],
        preferred_language=row["preferred_language"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        notification_preferences={
            "enabled": bool(row["notifications_enabled"]),
            "channels": preferences.get("channels", ["in_app"]),
        },
        updated_at=_parse_datetime(row["updated_at"]),
    )


@router.put("/profile", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: FarmStateStore = Depends(get_farm_store),
):
    payload_data = payload.model_dump(mode="json")
    try:
        cached = get_idempotent_response(store, idempotency_key, payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
    if cached is not None:
        return ProfileResponse.model_validate(cached)
    now = iso_now()
    store.execute(
        """
        INSERT INTO profile(id, name, phone, location, preferred_language, latitude, longitude, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET name=excluded.name, phone=excluded.phone, location=excluded.location,
          preferred_language=excluded.preferred_language, latitude=excluded.latitude, longitude=excluded.longitude,
          updated_at=excluded.updated_at
        """,
        (store.farmer_key, payload.name, payload.phone, payload.location, payload.preferred_language,
         payload.latitude, payload.longitude, now, now),
    )
    store.execute(
        """
        INSERT INTO preferences(profile_id, notifications_enabled, notification_preferences, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(profile_id) DO UPDATE SET notifications_enabled=excluded.notifications_enabled,
          notification_preferences=excluded.notification_preferences, updated_at=excluded.updated_at
        """,
        (store.farmer_key, int(payload.notification_preferences.enabled),
         json_text({"channels": payload.notification_preferences.channels}), now),
    )
    result = get_profile(store)
    save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"))
    return result


@router.get("/fields", response_model=list[FieldResponse])
def list_fields(
    include_inactive: bool = Query(default=False),
    store: FarmStateStore = Depends(get_farm_store),
):
    sql = "SELECT * FROM fields"
    if not include_inactive:
        sql += " WHERE active = 1"
    sql += " ORDER BY created_at"
    return [_field_response(row) for row in store.all(sql)]


@router.post("/fields", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
def create_field(
    payload: FieldCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: FarmStateStore = Depends(get_farm_store),
):
    payload_data = payload.model_dump(mode="json")
    try:
        cached = get_idempotent_response(store, idempotency_key, payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
    if cached is not None:
        return FieldResponse.model_validate(cached)
    field_id = str(uuid4())
    now = iso_now()
    centroid_lat, centroid_lon = _centroid(payload.boundary_geojson)
    store.execute(
        """
        INSERT INTO fields(id, name, area_acres, boundary_geojson, centroid_lat, centroid_lon, current_crop, status, active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'unknown', 1, ?, ?)
        """,
        (field_id, payload.name, payload.area_acres, json_text(payload.boundary_geojson), centroid_lat, centroid_lon,
         payload.current_crop, now, now),
    )
    result = _field_response(store.one("SELECT * FROM fields WHERE id = ?", (field_id,)))
    save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"), status.HTTP_201_CREATED)
    return result


@router.get("/fields/map", response_model=list[MapFieldResponse])
def map_fields(store: FarmStateStore = Depends(get_farm_store)):
    results: list[MapFieldResponse] = []
    for field in store.all("SELECT * FROM fields WHERE active = 1 ORDER BY created_at"):
        moisture = store.one(
            "SELECT value FROM sensor_readings WHERE field_id = ? AND measurement = 'moisture' ORDER BY observed_at DESC LIMIT 1",
            (field["id"],),
        )
        cycle = store.one(
            "SELECT current_stage FROM crop_cycles WHERE field_id = ? AND status = 'active' ORDER BY updated_at DESC LIMIT 1",
            (field["id"],),
        )
        alert_count = store.one(
            "SELECT COUNT(*) AS count FROM alerts WHERE field_id = ? AND status = 'open'", (field["id"],)
        )["count"]
        results.append(MapFieldResponse(
            id=field["id"], name=field["name"], area_acres=field["area_acres"],
            boundary_geojson=json_value(field["boundary_geojson"], {}),
            centroid_lat=field["centroid_lat"], centroid_lon=field["centroid_lon"],
            current_crop=field["current_crop"], current_stage=cycle["current_stage"] if cycle else None,
            latest_moisture_percent=moisture["value"] if moisture else None,
            alert_count=alert_count,
        ))
    return results


@router.get("/fields/{field_id}", response_model=FieldResponse)
def get_field(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    return _field_response(_require_field(store, field_id))


@router.patch("/fields/{field_id}", response_model=FieldResponse)
def patch_field(
    field_id: str,
    payload: FieldPatch,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: FarmStateStore = Depends(get_farm_store),
):
    payload_data = payload.model_dump(mode="json", exclude_unset=True)
    try:
        cached = get_idempotent_response(store, idempotency_key, payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
    if cached is not None:
        return FieldResponse.model_validate(cached)
    row = _require_field(store, field_id)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        result = _field_response(row)
        save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"))
        return result
    boundary = updates.get("boundary_geojson")
    centroid = _centroid(boundary) if boundary is not None else (row["centroid_lat"], row["centroid_lon"])
    columns = []
    values: list[Any] = []
    for key, value in updates.items():
        if key == "boundary_geojson":
            columns.append("boundary_geojson = ?")
            values.append(json_text(value))
        elif key == "active":
            columns.append("active = ?")
            values.append(int(value))
        else:
            columns.append(f"{key} = ?")
            values.append(value)
    columns.extend(["centroid_lat = ?", "centroid_lon = ?", "updated_at = ?"])
    values.extend([centroid[0], centroid[1], iso_now(), field_id])
    store.execute(f"UPDATE fields SET {', '.join(columns)} WHERE id = ?", values)
    result = _field_response(store.one("SELECT * FROM fields WHERE id = ?", (field_id,)))
    save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"))
    return result


@router.delete("/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    _require_field(store, field_id)
    store.execute("UPDATE fields SET active = 0, updated_at = ? WHERE id = ?", (iso_now(), field_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _crop_cycle_response(store: FarmStateStore, row) -> CropCycleResponse:
    events = store.all("SELECT * FROM crop_stage_events WHERE crop_cycle_id = ? ORDER BY occurred_at", (row["id"],))
    return CropCycleResponse(
        id=row["id"], field_id=row["field_id"], crop_name=row["crop_name"],
        planted_at=_parse_datetime(row["planted_at"]), expected_harvest_date=_parse_date(row["expected_harvest_date"]),
        current_stage=row["current_stage"], status=row["status"],
        stage_events=[CropStageEventResponse(id=item["id"], stage=item["stage"], occurred_at=_parse_datetime(item["occurred_at"]), note=item["note"]) for item in events],
        created_at=_parse_datetime(row["created_at"]), updated_at=_parse_datetime(row["updated_at"]),
    )


@router.post("/fields/{field_id}/crop-cycles", response_model=CropCycleResponse, status_code=status.HTTP_201_CREATED)
def create_crop_cycle(
    field_id: str,
    payload: CropCycleCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: FarmStateStore = Depends(get_farm_store),
):
    _require_field(store, field_id)
    payload_data = payload.model_dump(mode="json")
    try:
        cached = get_idempotent_response(store, idempotency_key, payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
    if cached is not None:
        return CropCycleResponse.model_validate(cached)
    cycle_id = str(uuid4())
    now = iso_now()
    store.execute(
        """INSERT INTO crop_cycles(id, field_id, crop_name, planted_at, expected_harvest_date, current_stage, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
        (cycle_id, field_id, payload.crop_name, payload.planted_at.isoformat(),
         payload.expected_harvest_date.isoformat() if payload.expected_harvest_date else None,
         payload.initial_stage, now, now),
    )
    store.execute(
        "INSERT INTO crop_stage_events(id, crop_cycle_id, stage, occurred_at, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid4()), cycle_id, payload.initial_stage, payload.planted_at.isoformat(), "Initial stage", now),
    )
    store.execute("UPDATE fields SET current_crop = ?, status = 'active', updated_at = ? WHERE id = ?", (payload.crop_name, now, field_id))
    result = _crop_cycle_response(store, store.one("SELECT * FROM crop_cycles WHERE id = ?", (cycle_id,)))
    save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"), status.HTTP_201_CREATED)
    return result


@router.get("/fields/{field_id}/timeline", response_model=list[CropCycleResponse])
def get_field_timeline(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    _require_field(store, field_id)
    return [_crop_cycle_response(store, row) for row in store.all("SELECT * FROM crop_cycles WHERE field_id = ? ORDER BY planted_at DESC", (field_id,))]


def _harvest_lot_response(store: FarmStateStore, row) -> HarvestLotResponse:
    cycle = store.one("SELECT crop_name FROM crop_cycles WHERE id = ?", (row["crop_cycle_id"],))
    return HarvestLotResponse(
        id=row["id"], field_id=row["field_id"], crop_cycle_id=row["crop_cycle_id"],
        crop_name=cycle["crop_name"], harvested_on=_parse_date(row["harvested_on"]),
        quantity=row["quantity"], unit=row["unit"], grade=row["grade"],
        storage_note=row["storage_note"], final_harvest=bool(row["final_harvest"]),
        source=row["source"], created_at=_parse_datetime(row["created_at"]),
    )


@router.get("/fields/{field_id}/harvest-lots", response_model=list[HarvestLotResponse])
def list_harvest_lots(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    _require_field(store, field_id)
    rows = store.all(
        "SELECT * FROM harvest_lots WHERE field_id = ? ORDER BY harvested_on DESC, created_at DESC",
        (field_id,),
    )
    return [_harvest_lot_response(store, row) for row in rows]


@router.post("/crop-cycles/{cycle_id}/harvest-lots", response_model=HarvestLotResponse, status_code=status.HTTP_201_CREATED)
def record_harvest_lot(
    cycle_id: str,
    payload: HarvestLotCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: FarmStateStore = Depends(get_farm_store),
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key is required for a harvest record")
    payload_data = {"crop_cycle_id": cycle_id, **payload.model_dump(mode="json")}
    try:
        cached = get_idempotent_response(store, idempotency_key, payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
    if cached is not None:
        return HarvestLotResponse.model_validate(cached)
    cycle = store.one("SELECT * FROM crop_cycles WHERE id = ?", (cycle_id,))
    if not cycle:
        raise HTTPException(status_code=404, detail="Crop cycle not found")
    if cycle["status"] != "active":
        raise HTTPException(status_code=409, detail="Harvest can only be recorded for an active crop cycle")
    farm_timezone = ZoneInfo("Asia/Kolkata")
    if payload.harvested_on > datetime.now(farm_timezone).date():
        raise HTTPException(status_code=422, detail="Harvest date cannot be in the future")
    planted_at = _parse_datetime(cycle["planted_at"])
    planted_on = planted_at.astimezone(farm_timezone).date() if planted_at.tzinfo else planted_at.date()
    if payload.harvested_on < planted_on:
        raise HTTPException(status_code=422, detail="Harvest date cannot be before planting")
    lot_id = str(uuid4())
    now = iso_now()
    store.execute(
        """INSERT INTO harvest_lots(id, crop_cycle_id, field_id, harvested_on, quantity, unit,
           grade, storage_note, final_harvest, source, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'farmer_reported', ?)""",
        (lot_id, cycle_id, cycle["field_id"], payload.harvested_on.isoformat(), payload.quantity,
         payload.unit, payload.grade, payload.storage_note, int(payload.final_harvest), now),
    )
    if payload.final_harvest:
        store.execute(
            "UPDATE crop_cycles SET current_stage = 'harvest', status = 'harvested', updated_at = ? WHERE id = ?",
            (now, cycle_id),
        )
        store.execute(
            "INSERT INTO crop_stage_events(id, crop_cycle_id, stage, occurred_at, note, created_at) VALUES (?, ?, 'harvest', ?, ?, ?)",
            (str(uuid4()), cycle_id, payload.harvested_on.isoformat() + "T00:00:00Z", "Final harvest reported by farmer", now),
        )
        other_active = store.one(
            "SELECT id FROM crop_cycles WHERE field_id = ? AND status = 'active' LIMIT 1",
            (cycle["field_id"],),
        )
        if not other_active:
            store.execute(
                "UPDATE fields SET current_crop = NULL, status = 'harvested', updated_at = ? WHERE id = ?",
                (now, cycle["field_id"]),
            )
    row = store.one("SELECT * FROM harvest_lots WHERE id = ?", (lot_id,))
    result = _harvest_lot_response(store, row)
    save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"), status.HTTP_201_CREATED)
    return result


@router.get("/fields/{field_id}/action-proposals", response_model=list[CropStageActionProposalResponse])
def get_crop_stage_action_proposals(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    """Suggest stage-aware field actions without persisting or executing them."""
    _require_field(store, field_id)
    cycle = store.one(
        "SELECT * FROM crop_cycles WHERE field_id = ? AND status = 'active' ORDER BY updated_at DESC LIMIT 1",
        (field_id,),
    )
    if not cycle:
        return []
    existing_titles = {
        row["title"] for row in store.all(
            "SELECT title FROM field_tasks WHERE field_id = ? AND status = 'open'", (field_id,)
        )
    }
    return [
        CropStageActionProposalResponse(
            field_id=field_id, crop_cycle_id=cycle["id"], crop_name=cycle["crop_name"], stage=cycle["current_stage"],
            title=proposal.title, why=proposal.why, due_hint=proposal.due_hint, source=proposal.source,
        )
        for proposal in crop_stage_action_proposals(cycle["current_stage"], cycle["crop_name"])
        if proposal.title not in existing_titles
    ]


@router.patch("/crop-cycles/{cycle_id}/stage", response_model=CropCycleResponse)
def update_crop_stage(
    cycle_id: str,
    payload: CropStageUpdate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: FarmStateStore = Depends(get_farm_store),
):
    payload_data = payload.model_dump(mode="json")
    try:
        cached = get_idempotent_response(store, idempotency_key, payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
    if cached is not None:
        return CropCycleResponse.model_validate(cached)
    row = store.one("SELECT * FROM crop_cycles WHERE id = ?", (cycle_id,))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop cycle not found")
    occurred_at = payload.occurred_at or datetime.now(timezone.utc)
    now = iso_now()
    store.execute("UPDATE crop_cycles SET current_stage = ?, updated_at = ? WHERE id = ?", (payload.stage, now, cycle_id))
    store.execute(
        "INSERT INTO crop_stage_events(id, crop_cycle_id, stage, occurred_at, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid4()), cycle_id, payload.stage, occurred_at.isoformat(), payload.note, now),
    )
    result = _crop_cycle_response(store, store.one("SELECT * FROM crop_cycles WHERE id = ?", (cycle_id,)))
    save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"))
    return result


@router.post("/fields/{field_id}/soil-tests", response_model=SoilTestResponse, status_code=status.HTTP_201_CREATED)
def create_soil_test(
    field_id: str,
    payload: SoilTestCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: FarmStateStore = Depends(get_farm_store),
):
    _require_field(store, field_id)
    payload_data = payload.model_dump(mode="json")
    try:
        cached = get_idempotent_response(store, idempotency_key, payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
    if cached is not None:
        return SoilTestResponse.model_validate(cached)
    test_id = str(uuid4())
    fetched_at = iso_now()
    store.execute(
        """INSERT INTO soil_tests(id, field_id, observed_at, ph, organic_carbon, nitrogen, phosphorus, potassium, ec, moisture_percent, source, fetched_at, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (test_id, field_id, payload.observed_at.isoformat(), payload.ph, payload.organic_carbon, payload.nitrogen,
         payload.phosphorus, payload.potassium, payload.ec, payload.moisture_percent, payload.source, fetched_at, payload.confidence),
    )
    if payload.moisture_percent is not None and payload.moisture_percent < 30:
        _upsert_alert(store, field_id=field_id, kind="low_moisture", title="Low soil moisture",
                      message=f"Soil test moisture is {payload.moisture_percent:.1f}%.", severity="warning",
                      dedupe_key=f"low-moisture:{field_id}", source=payload.source)
    result = _soil_response(store.one("SELECT * FROM soil_tests WHERE id = ?", (test_id,)))
    save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"), status.HTTP_201_CREATED)
    return result


@router.get("/fields/{field_id}/soil-health", response_model=SoilHealthResponse)
def get_soil_health(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    _require_field(store, field_id)
    _advance_tomato_demo(store, field_id)
    test = store.one("SELECT * FROM soil_tests WHERE field_id = ? ORDER BY observed_at DESC LIMIT 1", (field_id,))
    observations = store.all(
        """SELECT sr.* FROM sensor_readings sr JOIN (SELECT measurement, MAX(observed_at) latest FROM sensor_readings WHERE field_id = ? GROUP BY measurement) x
        ON x.measurement = sr.measurement AND x.latest = sr.observed_at WHERE sr.field_id = ?""", (field_id, field_id)
    )
    latest_values = {}
    if test:
        latest_values.update({key: test[key] for key in ("ph", "organic_carbon", "nitrogen", "phosphorus", "potassium", "ec", "moisture_percent")})
    status_text, raw_recommendations = soil_interpretation(latest_values)
    recommendations = [Recommendation(**item) for item in raw_recommendations]
    provenance = []
    if test:
        observed = _parse_datetime(test["observed_at"])
        fetched = _parse_datetime(test["fetched_at"])
        provenance.append({"source": test["source"], "observed_at": observed, "fetched_at": fetched,
                           "freshness_seconds": max(0, int((datetime.now(timezone.utc) - fetched).total_seconds())),
                           "confidence": test["confidence"]})
    return SoilHealthResponse(field_id=field_id, latest_test=_soil_response(test) if test else None,
                              latest_observations=[_observation_response(row) for row in observations],
                              status=status_text, recommendations=recommendations, provenance=provenance)


@router.post("/sensor-readings", response_model=ObservationResponse, status_code=status.HTTP_201_CREATED)
def create_sensor_reading(
    payload: SensorReadingCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: FarmStateStore = Depends(get_farm_store),
):
    _require_field(store, payload.field_id)
    if payload.device_id and not store.one("SELECT id FROM sensor_devices WHERE id = ? AND field_id = ?", (payload.device_id, payload.field_id)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sensor device does not belong to field")
    payload_data = payload.model_dump(mode="json")
    try:
        cached = get_idempotent_response(store, idempotency_key, payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
    if cached is not None:
        return ObservationResponse.model_validate(cached)
    reading_id = str(uuid4())
    fetched_at = iso_now()
    store.execute(
        """INSERT INTO sensor_readings(id, field_id, device_id, measurement, value, unit, observed_at, source, fetched_at, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (reading_id, payload.field_id, payload.device_id, payload.measurement, payload.value, payload.unit,
         payload.observed_at.isoformat(), payload.source, fetched_at, payload.confidence),
    )
    if payload.measurement == "moisture" and payload.value < 30:
        _upsert_alert(store, field_id=payload.field_id, kind="low_moisture", title="Low soil moisture",
                      message=f"Latest sensor moisture is {payload.value:.1f}%.", severity="warning",
                      dedupe_key=f"low-moisture:{payload.field_id}", source=payload.source)
    result = _observation_response(store.one("SELECT * FROM sensor_readings WHERE id = ?", (reading_id,)))
    save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"), status.HTTP_201_CREATED)
    return result


@router.get("/fields/{field_id}/observations/latest", response_model=list[ObservationResponse])
def latest_observations(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    _require_field(store, field_id)
    _advance_tomato_demo(store, field_id)
    rows = store.all(
        """SELECT sr.* FROM sensor_readings sr JOIN (SELECT measurement, MAX(observed_at) latest FROM sensor_readings WHERE field_id = ? GROUP BY measurement) x
        ON x.measurement = sr.measurement AND x.latest = sr.observed_at WHERE sr.field_id = ? ORDER BY sr.measurement""", (field_id, field_id)
    )
    return [_observation_response(row) for row in rows]


@router.get("/fields/{field_id}/crop-options", response_model=list[CropOptionResponse])
async def crop_options(
    field_id: str,
    request: Request,
    season: str = Query(..., min_length=2, max_length=40),
    previous_crop: str | None = Query(default=None, max_length=120),
    soil_type: str | None = Query(default=None, max_length=80),
    store: FarmStateStore = Depends(get_farm_store),
):
    """Compare sourced catalog records; never invent an optimized crop choice."""
    _require_field(store, field_id)
    if not getattr(request.app.state, "reference_db_available", False):
        raise HTTPException(status_code=503, detail="Crop reference data is unavailable; do not infer crop options.")
    crops = await Crop.find_all().to_list()
    return compare_crop_options(crops, season=season, previous_crop=previous_crop, soil_type=soil_type)


@router.get("/fields/{field_id}/observations/history", response_model=list[ObservationResponse])
def observation_history(
    field_id: str,
    measurement: str = Query(default="moisture", min_length=1, max_length=32),
    limit: int = Query(default=24, ge=2, le=240),
    store: FarmStateStore = Depends(get_farm_store),
):
    """Bounded, source-preserving observation history for the farmer's trend UI."""
    _require_field(store, field_id)
    _advance_tomato_demo(store, field_id)
    rows = store.all(
        "SELECT * FROM sensor_readings WHERE field_id = ? AND measurement = ? ORDER BY observed_at DESC LIMIT ?",
        (field_id, measurement, limit),
    )
    return [_observation_response(row) for row in reversed(rows)]


def _irrigation_plan(store: FarmStateStore, field_id: str, mode: str = "weather_aware") -> IrrigationPlanResponse:
    field = _require_field(store, field_id)
    _advance_tomato_demo(store, field_id)
    moisture = store.one("SELECT value, unit, observed_at, source FROM sensor_readings WHERE field_id = ? AND measurement = 'moisture' ORDER BY observed_at DESC LIMIT 1", (field_id,))
    moisture_unit_issue = bool(moisture and moisture["unit"] != "%")
    usable_moisture = None if moisture_unit_issue else moisture
    cycle = store.one("SELECT crop_name, current_stage FROM crop_cycles WHERE field_id = ? AND status = 'active' ORDER BY updated_at DESC LIMIT 1", (field_id,))
    recent_event = store.one(
        "SELECT occurred_at, source FROM irrigation_events WHERE field_id = ? ORDER BY occurred_at DESC LIMIT 1",
        (field_id,),
    )
    now_dt = datetime.now(timezone.utc)
    recent_irrigation = False
    if recent_event:
        occurred_at = _parse_datetime(recent_event["occurred_at"])
        if occurred_at and timedelta(0) <= now_dt - occurred_at <= timedelta(hours=12):
            recent_irrigation = True
    if mode == "offline_catalog":
        from app.farm_state.rules import offline_irrigation_rule
        rule = offline_irrigation_rule(usable_moisture["value"] if usable_moisture else None, cycle["crop_name"] if cycle else field["current_crop"], cycle["current_stage"] if cycle else None, now=now_dt)
        plan_id = str(uuid4())
        now = iso_now()
        recommendation = Recommendation(what=rule.what, why=rule.why, when=rule.when, cost_estimate="Not estimated: water and energy tariffs are not configured", expected_benefit=rule.expected_benefit, alternatives=rule.alternatives, confidence=rule.confidence)
        assumptions = ["Offline local catalogue only: no weather or internet source was used.", "This configurable demo screening band is not a pump or valve setting; calibrate it for the crop and soil.", "No pump or valve is started by this read-only endpoint."]
        if moisture_unit_issue:
            assumptions.append(f"Latest moisture unit '{moisture['unit']}' is not a verified percentage; it was not used for irrigation screening.")
        elif moisture:
            assumptions.append(f"Moisture source: {moisture['source']}; observed at {moisture['observed_at']}; unit: {moisture['unit']}.")
        return IrrigationPlanResponse(id=plan_id, field_id=field_id, status=rule.status, recommended_window_start=_parse_datetime(rule.when) if rule.status == "recommended" else None, target_moisture_percent=rule.target_moisture_percent, lower_moisture_percent=rule.lower_moisture_percent, upper_moisture_percent=rule.upper_moisture_percent, catalog_crop=rule.catalog_crop, catalog_stage=rule.catalog_stage, decision_mode=rule.decision_mode, application_adjustment_percent=rule.application_adjustment_percent, recommendation=recommendation, assumptions=assumptions, created_at=_parse_datetime(now))
    rain_probability = None
    rain_probability_next_48h = None
    rainfall_mm_next_48h = None
    # A farmer can have widely separated fields. Never borrow the newest
    # forecast globally: it may belong to another field and reverse a water
    # decision. This mirrors the coordinate-tolerant lookup used by the
    # field-weather endpoint.
    weather = None
    if field["centroid_lat"] is not None and field["centroid_lon"] is not None:
        weather = store.one(
            """SELECT * FROM weather_snapshots
            WHERE ABS(latitude - ?) < 0.01 AND ABS(longitude - ?) < 0.01
            ORDER BY fetched_at DESC LIMIT 1""",
            (field["centroid_lat"], field["centroid_lon"]),
        )
    if weather:
        payload = json_value(weather["payload"], {})
        hourly = payload.get("hourly", [])
        if hourly:
            values = [item.get("precipitation_probability") for item in hourly[:24] if item.get("precipitation_probability") is not None]
            rain_probability = max(values) if values else None
            values_48h = [item.get("precipitation_probability") for item in hourly[:48] if item.get("precipitation_probability") is not None]
            rain_probability_next_48h = max(values_48h) if values_48h else None
            rainfall_values = [item.get("precipitation_mm") for item in hourly[:48] if isinstance(item.get("precipitation_mm"), (int, float))]
            rainfall_mm_next_48h = sum(rainfall_values) if rainfall_values else None
        if rainfall_mm_next_48h is None:
            daily = payload.get("daily", [])
            daily_values = [item.get("precipitation_mm") for item in daily[:2] if isinstance(item.get("precipitation_mm"), (int, float))]
            rainfall_mm_next_48h = sum(daily_values) if daily_values else None
            if rain_probability_next_48h is None:
                daily_probabilities = [item.get("precipitation_probability") for item in daily[:2] if item.get("precipitation_probability") is not None]
                rain_probability_next_48h = max(daily_probabilities) if daily_probabilities else None
    rule = irrigation_rule(
        usable_moisture["value"] if usable_moisture else None,
        rain_probability,
        cycle["current_stage"] if cycle else None,
        recent_irrigation=recent_irrigation,
        now=now_dt,
        rainfall_mm_next_48h=rainfall_mm_next_48h,
        rain_probability_next_48h=rain_probability_next_48h,
    )
    plan_id = str(uuid4())
    now = iso_now()
    recommendation = Recommendation(
        what=rule.what, why=rule.why, when=rule.when, cost_estimate="Not estimated: water and energy tariffs are not configured",
        expected_benefit=rule.expected_benefit, alternatives=rule.alternatives, confidence=rule.confidence,
    )
    assumptions = ["No pump or valve is started by this read-only endpoint.", "Target moisture is a screening rule and should be calibrated to the crop and soil."]
    if rain_probability is not None:
        assumptions.append(
            f"Forecast rain probability used: {rain_probability:.0f}% from the cached weather snapshot "
            f"for this field location, source {weather['provider']}, fetched at {weather['fetched_at']}."
        )
    else:
        assumptions.append("No cached weather snapshot matched this field location; rain was not used to defer irrigation.")
    if rainfall_mm_next_48h is not None:
        probability_note = f"; maximum 48-hour rain probability: {rain_probability_next_48h:.0f}%" if rain_probability_next_48h is not None else ""
        assumptions.append(f"Forecast rainfall amount used: {rainfall_mm_next_48h:.1f} mm over the next 48 hours{probability_note}.")
    elif weather:
        assumptions.append("The cached forecast has no usable 48-hour rainfall amount; waterlogging screening was not applied.")
    if moisture_unit_issue:
        assumptions.append(
            f"Latest moisture unit '{moisture['unit']}' is not a verified percentage; it was not used for irrigation screening."
        )
    elif moisture:
        assumptions.append(f"Moisture source: {moisture['source']}; observed at {moisture['observed_at']}; unit: {moisture['unit']}.")
    if recent_irrigation:
        assumptions.append(
            f"A farmer-recorded irrigation event occurred at {recent_event['occurred_at']}; the plan waits for a fresh moisture check before another application."
        )
    # This endpoint is explicitly read-only. Persisting a new row on every GET
    # made dashboard refreshes mutate farm state and created unbounded duplicates.
    return IrrigationPlanResponse(id=plan_id, field_id=field_id, status=rule.status,
                                  recommended_window_start=_parse_datetime(rule.when) if rule.status == "recommended" else None,
                                  target_moisture_percent=rule.target_moisture_percent, decision_mode="weather_aware",
                                  application_adjustment_percent=rule.application_adjustment_percent,
                                  recommendation=recommendation, assumptions=assumptions,
                                  created_at=_parse_datetime(now))


@router.get("/fields/{field_id}/irrigation-plan", response_model=IrrigationPlanResponse)
def get_irrigation_plan(field_id: str, mode: str = "weather_aware", store: FarmStateStore = Depends(get_farm_store)):
    if mode not in {"offline_catalog", "weather_aware"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="mode must be offline_catalog or weather_aware")
    return _irrigation_plan(store, field_id, mode=mode)


@router.post("/irrigation-events", response_model=IrrigationEventResponse, status_code=status.HTTP_201_CREATED)
def create_irrigation_event(
    payload: IrrigationEventCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: FarmStateStore = Depends(get_farm_store),
):
    _require_field(store, payload.field_id)
    payload_data = payload.model_dump(mode="json")
    try:
        cached = get_idempotent_response(store, idempotency_key, payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
    if cached is not None:
        return IrrigationEventResponse.model_validate(cached)
    event_id = str(uuid4())
    store.execute(
        "INSERT INTO irrigation_events(id, field_id, occurred_at, volume_liters, duration_minutes, method, note, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (event_id, payload.field_id, payload.occurred_at.isoformat(), payload.volume_liters, payload.duration_minutes,
         payload.method, payload.note, "farmer_recorded"),
    )
    result = IrrigationEventResponse(id=event_id, source="farmer_recorded", **payload.model_dump())
    save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"), status.HTTP_201_CREATED)
    return result


@router.post("/reminders", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
def create_reminder(
    payload: ReminderCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: FarmStateStore = Depends(get_farm_store),
):
    if payload.field_id:
        _require_field(store, payload.field_id)
    payload_data = payload.model_dump(mode="json")
    try:
        cached = get_idempotent_response(store, idempotency_key, payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
    if cached is not None:
        return ReminderResponse.model_validate(cached)
    reminder_id = str(uuid4())
    now = iso_now()
    store.execute(
        "INSERT INTO reminders(id, field_id, reminder_type, scheduled_for, status, title, created_at) VALUES (?, ?, ?, ?, 'scheduled', ?, ?)",
        (reminder_id, payload.field_id, payload.reminder_type, payload.scheduled_for.isoformat(), payload.title, now),
    )
    result = ReminderResponse(id=reminder_id, status="scheduled", created_at=_parse_datetime(now), **payload.model_dump())
    save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"), status.HTTP_201_CREATED)
    return result


@router.get("/reminders", response_model=list[ReminderResponse])
def list_reminders(store: FarmStateStore = Depends(get_farm_store)):
    return [
        ReminderResponse(
            id=row["id"], field_id=row["field_id"], reminder_type=row["reminder_type"],
            scheduled_for=_parse_datetime(row["scheduled_for"]), title=row["title"],
            status=row["status"], created_at=_parse_datetime(row["created_at"]),
        )
        for row in store.all("SELECT * FROM reminders ORDER BY scheduled_for")
    ]


def _task_response(row) -> FieldTaskResponse:
    return FieldTaskResponse(
        id=row["id"], field_id=row["field_id"], title=row["title"], due_at=_parse_datetime(row["due_at"]),
        status=row["status"], source=row["source"] or "farmer_confirmed", created_at=_parse_datetime(row["created_at"]),
    )


def _ledger_response(row) -> LedgerEntryResponse:
    return LedgerEntryResponse(
        id=row["id"], field_id=row["field_id"], entry_type=row["entry_type"], category=row["category"],
        title=row["title"], amount_inr=row["amount_inr"], occurred_at=_parse_date(row["occurred_at"]),
        crop_name=row["crop_name"], note=row["note"], source=row["source"], status=row["status"],
        created_at=_parse_datetime(row["created_at"]), voided_at=_parse_datetime(row["voided_at"]),
    )


@router.post("/tasks", response_model=FieldTaskResponse, status_code=status.HTTP_201_CREATED)
def create_field_task(
    payload: FieldTaskCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: FarmStateStore = Depends(get_farm_store),
):
    _require_field(store, payload.field_id)
    payload_data = payload.model_dump(mode="json")
    try:
        cached = get_idempotent_response(store, idempotency_key, payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
    if cached is not None:
        return FieldTaskResponse.model_validate(cached)
    task_id, now = str(uuid4()), iso_now()
    store.execute(
        "INSERT INTO field_tasks(id, field_id, title, due_at, status, source, created_at) VALUES (?, ?, ?, ?, 'open', ?, ?)",
        (task_id, payload.field_id, payload.title, payload.due_at.isoformat() if payload.due_at else None, payload.source, now),
    )
    field = _require_field(store, payload.field_id)
    due_text = f" Due {payload.due_at.isoformat()}." if payload.due_at else " No due time was set."
    _upsert_alert(
        store,
        field_id=payload.field_id,
        kind="field_task_created",
        title="New field action",
        message=f"{payload.title} was added for {field['name']}.{due_text}",
        severity="info",
        dedupe_key=f"field-task:{task_id}",
        source="field_task",
    )
    result = _task_response(store.one("SELECT * FROM field_tasks WHERE id = ?", (task_id,)))
    save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"), status.HTTP_201_CREATED)
    return result


@router.get("/irrigation-events", response_model=list[IrrigationEventResponse])
def list_irrigation_events(
    field_id: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=200),
    store: FarmStateStore = Depends(get_farm_store),
):
    """Return farmer-owned irrigation history without inferring water applied."""
    if field_id:
        _require_field(store, field_id)
        rows = store.all(
            "SELECT * FROM irrigation_events WHERE field_id = ? ORDER BY occurred_at DESC LIMIT ?",
            (field_id, limit),
        )
    else:
        rows = store.all("SELECT * FROM irrigation_events ORDER BY occurred_at DESC LIMIT ?", (limit,))
    return [
        IrrigationEventResponse(
            id=row["id"], field_id=row["field_id"], occurred_at=_parse_datetime(row["occurred_at"]),
            volume_liters=row["volume_liters"], duration_minutes=row["duration_minutes"], method=row["method"],
            note=row["note"], source=row["source"],
        )
        for row in rows
    ]


@router.get("/tasks", response_model=list[FieldTaskResponse])
def list_field_tasks(
    field_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    store: FarmStateStore = Depends(get_farm_store),
):
    if field_id:
        _require_field(store, field_id)
    if status_filter and status_filter not in {"open", "completed", "cancelled"}:
        raise HTTPException(status_code=422, detail="status must be open, completed, or cancelled")
    clauses, values = [], []
    if field_id:
        clauses.append("field_id = ?"); values.append(field_id)
    if status_filter:
        clauses.append("status = ?"); values.append(status_filter)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = store.all(f"SELECT * FROM field_tasks{where} ORDER BY CASE status WHEN 'open' THEN 0 ELSE 1 END, due_at IS NULL, due_at, created_at DESC", tuple(values))
    return [_task_response(row) for row in rows]


@router.patch("/tasks/{task_id}", response_model=FieldTaskResponse)
def patch_field_task(
    task_id: str,
    payload: FieldTaskPatch,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: FarmStateStore = Depends(get_farm_store),
):
    payload_data = payload.model_dump(mode="json")
    try:
        cached = get_idempotent_response(store, idempotency_key, payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
    if cached is not None:
        return FieldTaskResponse.model_validate(cached)
    if not store.one("SELECT id FROM field_tasks WHERE id = ?", (task_id,)):
        raise HTTPException(status_code=404, detail="Task not found")
    store.execute("UPDATE field_tasks SET status = ? WHERE id = ?", (payload.status, task_id))
    result = _task_response(store.one("SELECT * FROM field_tasks WHERE id = ?", (task_id,)))
    save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"))
    return result


@router.post("/ledger/entries", response_model=LedgerEntryResponse, status_code=status.HTTP_201_CREATED)
def create_ledger_entry(
    payload: LedgerEntryCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: FarmStateStore = Depends(get_farm_store),
):
    """Persist a confirmed farm income/expense record; this never moves money."""
    if payload.field_id:
        _require_field(store, payload.field_id)
    payload_data = payload.model_dump(mode="json")
    try:
        cached = get_idempotent_response(store, idempotency_key, payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
    if cached is not None:
        return LedgerEntryResponse.model_validate(cached)
    entry_id, now = str(uuid4()), iso_now()
    store.execute(
        """INSERT INTO ledger_entries(
            id, field_id, entry_type, category, title, amount_inr, occurred_at, crop_name, note, source, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)""",
        (
            entry_id, payload.field_id, payload.entry_type, payload.category, payload.title, payload.amount_inr,
            payload.occurred_at.isoformat(), payload.crop_name, payload.note, payload.source, now,
        ),
    )
    result = _ledger_response(store.one("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)))
    save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"), status.HTTP_201_CREATED)
    return result


@router.get("/ledger/entries", response_model=list[LedgerEntryResponse])
def list_ledger_entries(
    field_id: str | None = Query(default=None),
    entry_type: str | None = Query(default=None),
    status_filter: str | None = Query(default="active", alias="status"),
    store: FarmStateStore = Depends(get_farm_store),
):
    if field_id:
        _require_field(store, field_id)
    if entry_type and entry_type not in {"income", "expense"}:
        raise HTTPException(status_code=422, detail="entry_type must be income or expense")
    if status_filter and status_filter not in {"active", "void"}:
        raise HTTPException(status_code=422, detail="status must be active or void")
    clauses, values = [], []
    if field_id:
        clauses.append("field_id = ?"); values.append(field_id)
    if entry_type:
        clauses.append("entry_type = ?"); values.append(entry_type)
    if status_filter:
        clauses.append("status = ?"); values.append(status_filter)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = store.all(f"SELECT * FROM ledger_entries{where} ORDER BY occurred_at DESC, created_at DESC", tuple(values))
    return [_ledger_response(row) for row in rows]


@router.get("/ledger/summary", response_model=LedgerSummaryResponse)
def get_ledger_summary(store: FarmStateStore = Depends(get_farm_store)):
    row = store.one(
        """SELECT
            COALESCE(SUM(CASE WHEN entry_type = 'income' THEN amount_inr ELSE 0 END), 0) AS income_inr,
            COALESCE(SUM(CASE WHEN entry_type = 'expense' THEN amount_inr ELSE 0 END), 0) AS expense_inr,
            COUNT(*) AS active_entry_count
        FROM ledger_entries WHERE status = 'active'"""
    )
    income, expense = float(row["income_inr"]), float(row["expense_inr"])
    return LedgerSummaryResponse(income_inr=income, expense_inr=expense, balance_inr=income - expense, active_entry_count=row["active_entry_count"])


@router.patch("/ledger/entries/{entry_id}", response_model=LedgerEntryResponse)
def patch_ledger_entry(
    entry_id: str,
    payload: LedgerEntryPatch,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: FarmStateStore = Depends(get_farm_store),
):
    payload_data = payload.model_dump(mode="json")
    try:
        cached = get_idempotent_response(store, idempotency_key, payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
    if cached is not None:
        return LedgerEntryResponse.model_validate(cached)
    if not store.one("SELECT id FROM ledger_entries WHERE id = ?", (entry_id,)):
        raise HTTPException(status_code=404, detail="Ledger entry not found")
    voided_at = iso_now() if payload.status == "void" else None
    store.execute("UPDATE ledger_entries SET status = ?, voided_at = ? WHERE id = ?", (payload.status, voided_at, entry_id))
    result = _ledger_response(store.one("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)))
    save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"))
    return result


@router.get("/alerts", response_model=list[AlertResponse])
def list_alerts(status_filter: str | None = Query(default=None, alias="status"), store: FarmStateStore = Depends(get_farm_store)):
    if status_filter:
        rows = store.all("SELECT * FROM alerts WHERE status = ? ORDER BY created_at DESC", (status_filter,))
    else:
        rows = store.all("SELECT * FROM alerts ORDER BY created_at DESC")
    return [_alert_response(row) for row in rows]


@router.patch("/alerts/{alert_id}", response_model=AlertResponse)
def patch_alert(
    alert_id: str,
    payload: AlertPatch,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: FarmStateStore = Depends(get_farm_store),
):
    payload_data = payload.model_dump(mode="json")
    try:
        cached = get_idempotent_response(store, idempotency_key, payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
    if cached is not None:
        return AlertResponse.model_validate(cached)
    if not store.one("SELECT id FROM alerts WHERE id = ?", (alert_id,)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    store.execute("UPDATE alerts SET status = ?, updated_at = ? WHERE id = ?", (payload.status, iso_now(), alert_id))
    result = _alert_response(store.one("SELECT * FROM alerts WHERE id = ?", (alert_id,)))
    save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"))
    return result


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(request: Request, store: FarmStateStore = Depends(get_farm_store)):
    map_data = map_fields(store)
    alerts = [_alert_response(row) for row in store.all("SELECT * FROM alerts WHERE status = 'open' ORDER BY created_at DESC")]
    warnings: list[str] = []
    weather = None
    cached = store.one("SELECT payload FROM weather_snapshots ORDER BY fetched_at DESC LIMIT 1")
    if cached:
        from app.schemas.farm_state import WeatherData
        payload = json_value(cached["payload"], {})
        weather = WeatherData(**payload)
    else:
        warnings.append("Weather is unavailable until a provider-backed weather request succeeds.")
    market_summary: list[dict[str, Any]] = []
    crops = sorted({field.current_crop for field in map_data if field.current_crop})
    if crops and getattr(request.app.state, "reference_db_available", False):
        latest: dict[tuple[str, str], MarketPrice] = {}
        for price in await MarketPrice.find({"crop_name": {"$in": crops}}).to_list():
            key = (price.crop_name, price.mandi_name)
            previous = latest.get(key)
            if previous is None or price.date > previous.date:
                latest[key] = price
        market_summary = [
            {
                "crop_name": price.crop_name,
                "mandi_name": price.mandi_name,
                "price_per_quintal": price.price_per_quintal,
                "date": price.date.isoformat(),
                "source": price.source,
            }
            for price in sorted(latest.values(), key=lambda item: (item.crop_name, -item.price_per_quintal))
        ]
    elif crops:
        warnings.append("Shared market reference data is unavailable; no market figure is shown.")
    return DashboardResponse(generated_at=datetime.now(timezone.utc), fields=map_data, weather=weather,
                             market_summary=market_summary, alerts=alerts, data_warnings=warnings)


def _report_snapshot(store: FarmStateStore) -> dict[str, Any]:
    fields = [dict(row) for row in store.all("SELECT id, name, area_acres, current_crop, status FROM fields WHERE active = 1")]
    return {
        "fields": fields,
        "open_alerts": [dict(row) for row in store.all("SELECT id, field_id, kind, title, severity FROM alerts WHERE status = 'open'")],
        "latest_moisture": [dict(row) for row in store.all("SELECT field_id, value, unit, observed_at, source FROM sensor_readings WHERE measurement = 'moisture' ORDER BY observed_at DESC")],
        "generated_from": "local_farm_state_sqlite",
    }


@router.post("/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    store: FarmStateStore = Depends(get_farm_store),
):
    payload_data = payload.model_dump(mode="json")
    try:
        cached = get_idempotent_response(store, idempotency_key, payload_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc)}) from exc
    if cached is not None:
        return ReportResponse.model_validate(cached)
    report_id = str(uuid4())
    now = iso_now()
    snapshot = _report_snapshot(store)
    store.execute(
        "INSERT INTO reports(id, report_type, from_date, to_date, status, input_snapshot, artifact, created_at, updated_at) VALUES (?, ?, ?, ?, 'completed', ?, ?, ?, ?)",
        (report_id, payload.report_type, payload.from_date.isoformat() if payload.from_date else None,
         payload.to_date.isoformat() if payload.to_date else None, json_text(snapshot), json_text(snapshot), now, now),
    )
    store.execute("INSERT INTO report_jobs(id, report_id, status, created_at, updated_at) VALUES (?, ?, 'completed', ?, ?)", (str(uuid4()), report_id, now, now))
    result = ReportResponse(id=report_id, report_type=payload.report_type, from_date=payload.from_date, to_date=payload.to_date,
                            status="completed", input_snapshot=snapshot, artifact=snapshot,
                            created_at=_parse_datetime(now), updated_at=_parse_datetime(now))
    save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"), status.HTTP_201_CREATED)
    return result


@router.get("/reports", response_model=list[ReportResponse])
def list_reports(store: FarmStateStore = Depends(get_farm_store)):
    return [
        ReportResponse(
            id=row["id"], report_type=row["report_type"], from_date=_parse_date(row["from_date"]),
            to_date=_parse_date(row["to_date"]), status=row["status"],
            input_snapshot=json_value(row["input_snapshot"], {}), artifact=json_value(row["artifact"]),
            created_at=_parse_datetime(row["created_at"]), updated_at=_parse_datetime(row["updated_at"]),
        )
        for row in store.all("SELECT * FROM reports ORDER BY created_at DESC")
    ]


@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(report_id: str, store: FarmStateStore = Depends(get_farm_store)):
    row = store.one("SELECT * FROM reports WHERE id = ?", (report_id,))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return ReportResponse(id=row["id"], report_type=row["report_type"], from_date=_parse_date(row["from_date"]), to_date=_parse_date(row["to_date"]),
                          status=row["status"], input_snapshot=json_value(row["input_snapshot"], {}), artifact=json_value(row["artifact"]),
                          created_at=_parse_datetime(row["created_at"]), updated_at=_parse_datetime(row["updated_at"]))
