from __future__ import annotations

import json
from collections.abc import Generator
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status

from app.auth.dependencies import require_actor_scope
from kisansathi_auth.claims import ActorScope
from app.core.config import settings
from app.farm_state.rules import crop_stage_action_proposals, irrigation_rule, soil_interpretation
from app.farm_state.store import FarmStateStore, get_idempotent_response, iso_now, json_text, json_value, safe_scope_key, save_idempotent_response
from app.services.weather import WeatherProviderError, fetch_weather
from app.schemas.farm_state import AlertPatch, AlertResponse, CropCycleCreate, CropCycleResponse, CropOptionResponse, CropStageActionProposalResponse, CropStageEventResponse, CropStageUpdate, DashboardResponse, FieldCreate, FieldPatch, FieldResponse, FieldTaskCreate, FieldTaskPatch, FieldTaskResponse, IrrigationEventCreate, IrrigationEventResponse, IrrigationPlanResponse, LedgerEntryCreate, LedgerEntryPatch, LedgerEntryResponse, LedgerSummaryResponse, MapFieldResponse, ObservationResponse, ProfileResponse, ProfileUpdate, Provenance, Recommendation, ReminderCreate, ReminderResponse, ReportCreate, ReportResponse, SensorReadingCreate, SoilHealthResponse, SoilTestCreate, SoilTestResponse, StorageStatusResponse, WeatherAlertResponse, WeatherData

router = APIRouter(prefix="/v1", tags=["farm-state"])


def get_farm_store(request: Request, actor: ActorScope = Depends(require_actor_scope)) -> Generator[FarmStateStore, None, None]:
    """Resolve the SQLite partition from immutable verified actor claims.

    The legacy browser-selected X-Farmer-ID header is rejected rather than
    allowing it to choose a database. Future auth dependencies can override
    this dependency with an immutable ActorScope-derived store.
    """
    if request.headers.get("X-Farmer-ID") is not None:
        raise HTTPException(status_code=400, detail={"code": "legacy_identity_selector_rejected", "message": "Farmer identity is server-scoped and cannot be selected by a request header.", "retryable": False})
    try:
        store = FarmStateStore(tenant_id=actor.tenant_id, farmer_id=actor.farmer_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_scope", "message": str(exc), "retryable": False}) from exc
    try:
        yield store
    finally:
        store.close()


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _date(value: str | None) -> date | None: return date.fromisoformat(value) if value else None


def _error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": "idempotency_key_conflict", "message": str(exc), "retryable": False})


def _cached(store: FarmStateStore, key: str | None, payload: Any) -> Any | None:
    try: return get_idempotent_response(store, key, payload)
    except ValueError as exc: raise _error(exc) from exc


def _field(store: FarmStateStore, field_id: str, *, include_inactive: bool = False):
    sql = "SELECT * FROM fields WHERE id = ?" + ("" if include_inactive else " AND active = 1")
    row = store.one(sql, (field_id,))
    if not row: raise HTTPException(status_code=404, detail={"code": "field_not_found", "message": "Field not found", "retryable": False})
    return row


def _centroid(boundary: dict[str, Any]) -> tuple[float | None, float | None]:
    geometry = boundary.get("geometry", boundary); points: list[tuple[float, float]] = []
    def visit(value: Any) -> None:
        if isinstance(value, list) and len(value) >= 2 and all(isinstance(x, (int, float)) for x in value[:2]): points.append((float(value[0]), float(value[1])))
        elif isinstance(value, list):
            for item in value: visit(item)
    visit(geometry.get("coordinates")); return ((sum(x[1] for x in points) / len(points), sum(x[0] for x in points) / len(points)) if points else (None, None))


def _field_response(row: Any) -> FieldResponse:
    return FieldResponse(id=row["id"], name=row["name"], area_acres=row["area_acres"], boundary_geojson=json_value(row["boundary_geojson"], {}), centroid_lat=row["centroid_lat"], centroid_lon=row["centroid_lon"], current_crop=row["current_crop"], status=row["status"], active=bool(row["active"]), created_at=_dt(row["created_at"]), updated_at=_dt(row["updated_at"]))


def _observation(row: Any) -> ObservationResponse:
    return ObservationResponse(id=row["id"], field_id=row["field_id"], measurement=row["measurement"], value=row["value"], unit=row["unit"], observed_at=_dt(row["observed_at"]), fetched_at=_dt(row["fetched_at"]), source=row["source"], confidence=row["confidence"])


def _soil(row: Any) -> SoilTestResponse:
    return SoilTestResponse(id=row["id"], field_id=row["field_id"], observed_at=_dt(row["observed_at"]), ph=row["ph"], organic_carbon=row["organic_carbon"], nitrogen=row["nitrogen"], phosphorus=row["phosphorus"], potassium=row["potassium"], ec=row["ec"], moisture_percent=row["moisture_percent"], source=row["source"], confidence=row["confidence"], fetched_at=_dt(row["fetched_at"]))


def _alert(row: Any) -> AlertResponse:
    return AlertResponse(id=row["id"], field_id=row["field_id"], kind=row["kind"], title=row["title"], message=row["message"], severity=row["severity"], status=row["status"], source=row["source"], created_at=_dt(row["created_at"]), updated_at=_dt(row["updated_at"]))


def _task(row: Any) -> FieldTaskResponse:
    return FieldTaskResponse(id=row["id"], field_id=row["field_id"], title=row["title"], due_at=_dt(row["due_at"]), status=row["status"], source=row["source"] or "farmer_confirmed", created_at=_dt(row["created_at"]))


def _ledger(row: Any) -> LedgerEntryResponse:
    return LedgerEntryResponse(id=row["id"], field_id=row["field_id"], entry_type=row["entry_type"], category=row["category"], title=row["title"], amount_inr=row["amount_inr"], occurred_at=_date(row["occurred_at"]), crop_name=row["crop_name"], note=row["note"], source=row["source"], status=row["status"], created_at=_dt(row["created_at"]), voided_at=_dt(row["voided_at"]))


@router.get("/storage-status", response_model=StorageStatusResponse)
def storage_status(request: Request, store: FarmStateStore = Depends(get_farm_store)) -> StorageStatusResponse:
    return StorageStatusResponse(farmer_id=store.farmer_id, reference_database="available" if getattr(request.app.state, "reference_db_available", False) else "unavailable")


@router.get("/profile", response_model=ProfileResponse)
def get_profile(store: FarmStateStore = Depends(get_farm_store)) -> ProfileResponse:
    row = store.one("SELECT p.*, COALESCE(pref.notifications_enabled,1) notifications_enabled, COALESCE(pref.notification_preferences,'{}') notification_preferences FROM profile p LEFT JOIN preferences pref ON pref.profile_id=p.id WHERE p.id=?", (store.farmer_id,))
    if not row: raise HTTPException(status_code=404, detail={"code": "profile_not_found", "message": "Profile not found", "retryable": False})
    preferences = json_value(row["notification_preferences"], {})
    return ProfileResponse(farmer_id=row["id"], name=row["name"], phone=row["phone"], location=row["location"], preferred_language=row["preferred_language"], latitude=row["latitude"], longitude=row["longitude"], notification_preferences={"enabled": bool(row["notifications_enabled"]), "channels": preferences.get("channels", ["in_app"])}, updated_at=_dt(row["updated_at"]))


@router.put("/profile", response_model=ProfileResponse)
def update_profile(payload: ProfileUpdate, idempotency_key: str | None = Header(None, alias="Idempotency-Key"), store: FarmStateStore = Depends(get_farm_store)):
    payload_data = payload.model_dump(mode="json"); cached = _cached(store, idempotency_key, payload_data)
    if cached is not None: return ProfileResponse.model_validate(cached)
    now = iso_now(); store.execute("INSERT INTO profile(id,name,phone,location,preferred_language,latitude,longitude,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,phone=excluded.phone,location=excluded.location,preferred_language=excluded.preferred_language,latitude=excluded.latitude,longitude=excluded.longitude,updated_at=excluded.updated_at", (store.farmer_id, payload.name, payload.phone, payload.location, payload.preferred_language, payload.latitude, payload.longitude, now, now))
    store.execute("INSERT INTO preferences(profile_id,notifications_enabled,notification_preferences,updated_at) VALUES(?,?,?,?) ON CONFLICT(profile_id) DO UPDATE SET notifications_enabled=excluded.notifications_enabled,notification_preferences=excluded.notification_preferences,updated_at=excluded.updated_at", (store.farmer_id, int(payload.notification_preferences.enabled), json_text({"channels": payload.notification_preferences.channels}), now))
    result = get_profile(store); save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json")); return result


@router.get("/fields", response_model=list[FieldResponse])
def list_fields(include_inactive: bool = False, store: FarmStateStore = Depends(get_farm_store)):
    return [_field_response(row) for row in store.all("SELECT * FROM fields" + ("" if include_inactive else " WHERE active=1") + " ORDER BY created_at")]


@router.post("/fields", response_model=FieldResponse, status_code=201)
def create_field(payload: FieldCreate, idempotency_key: str | None = Header(None, alias="Idempotency-Key"), store: FarmStateStore = Depends(get_farm_store)):
    payload_data = payload.model_dump(mode="json"); cached = _cached(store, idempotency_key, payload_data)
    if cached is not None: return FieldResponse.model_validate(cached)
    field_id = str(uuid4()); now = iso_now(); lat, lon = _centroid(payload.boundary_geojson)
    store.execute("INSERT INTO fields(id,name,area_acres,boundary_geojson,centroid_lat,centroid_lon,current_crop,status,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,'unknown',1,?,?)", (field_id, payload.name, payload.area_acres, json_text(payload.boundary_geojson), lat, lon, payload.current_crop, now, now))
    result = _field_response(store.one("SELECT * FROM fields WHERE id=?", (field_id,))); save_idempotent_response(store, idempotency_key, payload_data, result.model_dump(mode="json"), 201); return result


@router.get("/fields/map", response_model=list[MapFieldResponse])
def fields_map(store: FarmStateStore = Depends(get_farm_store)):
    result = []
    for row in store.all("SELECT * FROM fields WHERE active=1 ORDER BY created_at"):
        moisture = store.one("SELECT value FROM sensor_readings WHERE field_id=? AND measurement='moisture' ORDER BY observed_at DESC LIMIT 1", (row["id"],)); cycle = store.one("SELECT current_stage FROM crop_cycles WHERE field_id=? AND status='active' ORDER BY updated_at DESC LIMIT 1", (row["id"],)); alerts = store.one("SELECT COUNT(*) count FROM alerts WHERE field_id=? AND status='open'", (row["id"],))
        result.append(MapFieldResponse(id=row["id"], name=row["name"], area_acres=row["area_acres"], boundary_geojson=json_value(row["boundary_geojson"], {}), centroid_lat=row["centroid_lat"], centroid_lon=row["centroid_lon"], current_crop=row["current_crop"], current_stage=cycle["current_stage"] if cycle else None, latest_moisture_percent=moisture["value"] if moisture else None, alert_count=alerts["count"]))
    return result


@router.get("/fields/{field_id}", response_model=FieldResponse)
def get_field(field_id: str, store: FarmStateStore = Depends(get_farm_store)): return _field_response(_field(store, field_id))


@router.patch("/fields/{field_id}", response_model=FieldResponse)
def patch_field(field_id: str, payload: FieldPatch, idempotency_key: str | None = Header(None, alias="Idempotency-Key"), store: FarmStateStore = Depends(get_farm_store)):
    data = payload.model_dump(mode="json", exclude_unset=True); cached = _cached(store, idempotency_key, data)
    if cached is not None: return FieldResponse.model_validate(cached)
    row = _field(store, field_id); updates = payload.model_dump(exclude_unset=True)
    if updates:
        centroid = _centroid(updates["boundary_geojson"]) if "boundary_geojson" in updates else (row["centroid_lat"], row["centroid_lon"]); sets = []; values: list[Any] = []
        for key, value in updates.items(): sets.append(f"{key if key != 'active' else 'active'}=?"); values.append(json_text(value) if key == "boundary_geojson" else int(value) if key == "active" else value)
        sets += ["centroid_lat=?", "centroid_lon=?", "updated_at=?"]; values += [centroid[0], centroid[1], iso_now(), field_id]; store.execute(f"UPDATE fields SET {','.join(sets)} WHERE id=?", values)
    result = _field_response(store.one("SELECT * FROM fields WHERE id=?", (field_id,))); save_idempotent_response(store, idempotency_key, data, result.model_dump(mode="json")); return result


@router.delete("/fields/{field_id}", status_code=204)
def delete_field(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    _field(store, field_id); store.execute("UPDATE fields SET active=0,updated_at=? WHERE id=?", (iso_now(), field_id)); return Response(status_code=204)


def _cycle(store: FarmStateStore, row: Any) -> CropCycleResponse:
    events = store.all("SELECT * FROM crop_stage_events WHERE crop_cycle_id=? ORDER BY occurred_at", (row["id"],))
    return CropCycleResponse(id=row["id"], field_id=row["field_id"], crop_name=row["crop_name"], planted_at=_dt(row["planted_at"]), expected_harvest_date=_date(row["expected_harvest_date"]), current_stage=row["current_stage"], status=row["status"], stage_events=[CropStageEventResponse(id=x["id"], stage=x["stage"], occurred_at=_dt(x["occurred_at"]), note=x["note"]) for x in events], created_at=_dt(row["created_at"]), updated_at=_dt(row["updated_at"]))


@router.post("/fields/{field_id}/crop-cycles", response_model=CropCycleResponse, status_code=201)
def create_cycle(field_id: str, payload: CropCycleCreate, idempotency_key: str | None = Header(None, alias="Idempotency-Key"), store: FarmStateStore = Depends(get_farm_store)):
    _field(store, field_id); data = payload.model_dump(mode="json"); cached = _cached(store, idempotency_key, data)
    if cached is not None: return CropCycleResponse.model_validate(cached)
    cycle_id, now = str(uuid4()), iso_now(); store.execute("INSERT INTO crop_cycles(id,field_id,crop_name,planted_at,expected_harvest_date,current_stage,status,created_at,updated_at) VALUES(?,?,?,?,?,?,'active',?,?)", (cycle_id, field_id, payload.crop_name, payload.planted_at.isoformat(), payload.expected_harvest_date.isoformat() if payload.expected_harvest_date else None, payload.initial_stage, now, now)); store.execute("INSERT INTO crop_stage_events(id,crop_cycle_id,stage,occurred_at,note,created_at) VALUES(?,?,?,?,?,?)", (str(uuid4()), cycle_id, payload.initial_stage, payload.planted_at.isoformat(), None, now))
    result = _cycle(store, store.one("SELECT * FROM crop_cycles WHERE id=?", (cycle_id,))); save_idempotent_response(store, idempotency_key, data, result.model_dump(mode="json"), 201); return result


@router.get("/fields/{field_id}/timeline", response_model=list[CropCycleResponse])
def field_timeline(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    _field(store, field_id); return [_cycle(store, x) for x in store.all("SELECT * FROM crop_cycles WHERE field_id=? ORDER BY planted_at DESC", (field_id,))]


@router.get("/fields/{field_id}/action-proposals", response_model=list[CropStageActionProposalResponse])
def action_proposals(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    _field(store, field_id); result = []
    for cycle in store.all("SELECT * FROM crop_cycles WHERE field_id=? AND status='active'", (field_id,)):
        for proposal in crop_stage_action_proposals(cycle["current_stage"], cycle["crop_name"]): result.append(CropStageActionProposalResponse(field_id=field_id, crop_cycle_id=cycle["id"], crop_name=cycle["crop_name"], stage=cycle["current_stage"], title=proposal.title, why=proposal.why, due_hint=proposal.due_hint, source=proposal.source))
    return result


@router.patch("/crop-cycles/{cycle_id}/stage", response_model=CropCycleResponse)
def update_stage(cycle_id: str, payload: CropStageUpdate, idempotency_key: str | None = Header(None, alias="Idempotency-Key"), store: FarmStateStore = Depends(get_farm_store)):
    row = store.one("SELECT * FROM crop_cycles WHERE id=?", (cycle_id,));
    if not row: raise HTTPException(status_code=404, detail={"code": "crop_cycle_not_found", "message": "Crop cycle not found", "retryable": False})
    data = payload.model_dump(mode="json"); cached = _cached(store, idempotency_key, data)
    if cached is not None: return CropCycleResponse.model_validate(cached)
    now = iso_now(); occurred = payload.occurred_at.isoformat() if payload.occurred_at else now; store.execute("UPDATE crop_cycles SET current_stage=?,updated_at=? WHERE id=?", (payload.stage, now, cycle_id)); store.execute("INSERT INTO crop_stage_events(id,crop_cycle_id,stage,occurred_at,note,created_at) VALUES(?,?,?,?,?,?)", (str(uuid4()), cycle_id, payload.stage, occurred, payload.note, now)); result = _cycle(store, store.one("SELECT * FROM crop_cycles WHERE id=?", (cycle_id,))); save_idempotent_response(store, idempotency_key, data, result.model_dump(mode="json")); return result


@router.post("/fields/{field_id}/soil-tests", response_model=SoilTestResponse, status_code=201)
def create_soil_test(field_id: str, payload: SoilTestCreate, idempotency_key: str | None = Header(None, alias="Idempotency-Key"), store: FarmStateStore = Depends(get_farm_store)):
    _field(store, field_id); data = payload.model_dump(mode="json"); cached = _cached(store, idempotency_key, data)
    if cached is not None: return SoilTestResponse.model_validate(cached)
    test_id, now = str(uuid4()), iso_now(); values = [test_id, field_id, payload.observed_at.isoformat(), payload.ph, payload.organic_carbon, payload.nitrogen, payload.phosphorus, payload.potassium, payload.ec, payload.moisture_percent, payload.source, now, payload.confidence]; store.execute("INSERT INTO soil_tests(id,field_id,observed_at,ph,organic_carbon,nitrogen,phosphorus,potassium,ec,moisture_percent,source,fetched_at,confidence) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", values); result = _soil(store.one("SELECT * FROM soil_tests WHERE id=?", (test_id,))); save_idempotent_response(store, idempotency_key, data, result.model_dump(mode="json"), 201); return result


@router.get("/fields/{field_id}/soil-health", response_model=SoilHealthResponse)
def soil_health(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    _field(store, field_id); latest = store.one("SELECT * FROM soil_tests WHERE field_id=? ORDER BY observed_at DESC LIMIT 1", (field_id,)); observations = store.all("SELECT * FROM sensor_readings WHERE field_id=? ORDER BY observed_at DESC LIMIT 20", (field_id,)); values = dict(latest) if latest else {}; state, recommendations = soil_interpretation(values); provenance = [Provenance(source=x["source"], observed_at=_dt(x["observed_at"]), fetched_at=_dt(x["fetched_at"]), freshness_seconds=max(0, int((datetime.now(timezone.utc)-(_dt(x["fetched_at"]) or datetime.now(timezone.utc)).astimezone(timezone.utc)).total_seconds())), confidence=x["confidence"]) for x in ([latest] if latest else [])]; return SoilHealthResponse(field_id=field_id, latest_test=_soil(latest) if latest else None, latest_observations=[_observation(x) for x in observations], status=state, recommendations=[Recommendation(**x) for x in recommendations], provenance=provenance)


@router.post("/sensor-readings", response_model=ObservationResponse, status_code=201)
def create_sensor_reading(payload: SensorReadingCreate, idempotency_key: str | None = Header(None, alias="Idempotency-Key"), store: FarmStateStore = Depends(get_farm_store)):
    _field(store, payload.field_id); data = payload.model_dump(mode="json"); cached = _cached(store, idempotency_key, data)
    if cached is not None: return ObservationResponse.model_validate(cached)
    reading_id, now = str(uuid4()), iso_now(); store.execute("INSERT INTO sensor_readings(id,field_id,device_id,measurement,value,unit,observed_at,source,fetched_at,confidence) VALUES(?,?,?,?,?,?,?,?,?,?)", (reading_id, payload.field_id, payload.device_id, payload.measurement, payload.value, payload.unit, payload.observed_at.isoformat(), payload.source, now, payload.confidence))
    if payload.measurement == "moisture" and payload.value < 20:
        store.execute("INSERT INTO alerts(id,field_id,kind,title,message,severity,status,dedupe_key,source,created_at,updated_at) VALUES(?,?,?,?,?,'warning','open',?,?,?,?) ON CONFLICT(dedupe_key) DO UPDATE SET message=excluded.message,updated_at=excluded.updated_at", (str(uuid4()), payload.field_id, "low_moisture", "Low soil moisture", f"Latest recorded moisture is {payload.value:.1f}%.", f"low-moisture:{payload.field_id}", "rule:irrigation", now, now))
    result = _observation(store.one("SELECT * FROM sensor_readings WHERE id=?", (reading_id,))); save_idempotent_response(store, idempotency_key, data, result.model_dump(mode="json"), 201); return result


@router.get("/fields/{field_id}/observations/latest", response_model=list[ObservationResponse])
def latest_observations(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    _field(store, field_id); return [_observation(x) for x in store.all("SELECT s.* FROM sensor_readings s JOIN (SELECT measurement,MAX(observed_at) latest FROM sensor_readings WHERE field_id=? GROUP BY measurement) l ON s.measurement=l.measurement AND s.observed_at=l.latest WHERE s.field_id=?", (field_id, field_id))]


@router.get("/fields/{field_id}/observations/history", response_model=list[ObservationResponse])
def observation_history(field_id: str, limit: int = Query(100, ge=1, le=500), store: FarmStateStore = Depends(get_farm_store)):
    _field(store, field_id); return [_observation(x) for x in store.all("SELECT * FROM sensor_readings WHERE field_id=? ORDER BY observed_at DESC LIMIT ?", (field_id, limit))]


@router.get("/fields/{field_id}/crop-options", response_model=list[CropOptionResponse])
def crop_options(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    field = _field(store, field_id)
    crop = field["current_crop"] or ""
    if not crop:
        return []
    return [CropOptionResponse(crop_name=crop, checks={"field_crop_recorded": True, "reference_evidence": None}, missing_evidence=["Reference crop suitability evidence is unavailable until the catalog is connected."], conflicts=[], status="candidate_needs_review")]


def _irrigation_plan(field_id: str, store: FarmStateStore) -> IrrigationPlanResponse:
    field = _field(store, field_id); cycle = store.one("SELECT * FROM crop_cycles WHERE field_id=? AND status='active' ORDER BY updated_at DESC LIMIT 1", (field_id,)); latest = store.one("SELECT * FROM sensor_readings WHERE field_id=? AND measurement='moisture' ORDER BY observed_at DESC LIMIT 1", (field_id,)); event = store.one("SELECT id FROM irrigation_events WHERE field_id=? AND occurred_at >= datetime('now','-24 hours') LIMIT 1", (field_id,)); rain = None
    if field["centroid_lat"] is not None:
        weather = store.one("SELECT payload FROM weather_snapshots WHERE ABS(latitude-?)<.01 AND ABS(longitude-?)<.01 ORDER BY fetched_at DESC LIMIT 1", (field["centroid_lat"], field["centroid_lon"]));
        if weather:
            days = json_value(weather["payload"], {}).get("daily", []); rain = days[0].get("precipitation_probability") if days else None
    rule = irrigation_rule(latest["value"] if latest else None, rain, cycle["current_stage"] if cycle else None, bool(event)); now = datetime.now(timezone.utc)
    recommendation = Recommendation(what=rule.what, why=rule.why, when=rule.when, cost_estimate="Not estimated: water source, field geometry, and local rates are not supplied", expected_benefit=rule.expected_benefit, alternatives=rule.alternatives, confidence=rule.confidence)
    return IrrigationPlanResponse(id=f"advice-{field_id}", field_id=field_id, status=rule.status, recommended_window_start=now if rule.status == "recommended" else None, recommended_window_end=None, target_moisture_percent=rule.target_moisture_percent, estimated_volume_liters=None, estimated_duration_minutes=None, recommendation=recommendation, assumptions=["Advice is a screening rule from the latest recorded observation.", "This endpoint never controls irrigation equipment or records water applied."], created_at=now)


@router.get("/fields/{field_id}/irrigation-plan", response_model=IrrigationPlanResponse)
def irrigation_plan(field_id: str, store: FarmStateStore = Depends(get_farm_store)): return _irrigation_plan(field_id, store)


@router.post("/irrigation-events", response_model=IrrigationEventResponse, status_code=201)
def create_irrigation_event(payload: IrrigationEventCreate, idempotency_key: str | None = Header(None, alias="Idempotency-Key"), store: FarmStateStore = Depends(get_farm_store)):
    _field(store, payload.field_id); data = payload.model_dump(mode="json"); cached = _cached(store, idempotency_key, data)
    if cached is not None: return IrrigationEventResponse.model_validate(cached)
    event_id = str(uuid4()); store.execute("INSERT INTO irrigation_events(id,field_id,occurred_at,volume_liters,duration_minutes,method,note,source) VALUES(?,?,?,?,?,?,?,?)", (event_id, payload.field_id, payload.occurred_at.isoformat(), payload.volume_liters, payload.duration_minutes, payload.method, payload.note, "farmer_recorded")); result = IrrigationEventResponse(id=event_id, source="farmer_recorded", **payload.model_dump()); save_idempotent_response(store, idempotency_key, data, result.model_dump(mode="json"), 201); return result


@router.get("/irrigation-events", response_model=list[IrrigationEventResponse])
def irrigation_events(field_id: str | None = None, limit: int = Query(30, ge=1, le=200), store: FarmStateStore = Depends(get_farm_store)):
    if field_id: _field(store, field_id)
    if field_id: rows = store.all("SELECT * FROM irrigation_events WHERE field_id=? ORDER BY occurred_at DESC LIMIT ?", (field_id, limit))
    else: rows = store.all("SELECT * FROM irrigation_events ORDER BY occurred_at DESC LIMIT ?", (limit,))
    return [IrrigationEventResponse(id=x["id"], field_id=x["field_id"], occurred_at=_dt(x["occurred_at"]), volume_liters=x["volume_liters"], duration_minutes=x["duration_minutes"], method=x["method"], note=x["note"], source=x["source"]) for x in rows]


@router.post("/reminders", response_model=ReminderResponse, status_code=201)
def create_reminder(payload: ReminderCreate, idempotency_key: str | None = Header(None, alias="Idempotency-Key"), store: FarmStateStore = Depends(get_farm_store)):
    if payload.field_id: _field(store, payload.field_id)
    data = payload.model_dump(mode="json"); cached = _cached(store, idempotency_key, data)
    if cached is not None: return ReminderResponse.model_validate(cached)
    reminder_id, now = str(uuid4()), iso_now(); store.execute("INSERT INTO reminders(id,field_id,reminder_type,scheduled_for,status,title,created_at) VALUES(?,?,?,?,'scheduled',?,?)", (reminder_id, payload.field_id, payload.reminder_type, payload.scheduled_for.isoformat(), payload.title, now)); result = ReminderResponse(id=reminder_id, status="scheduled", created_at=_dt(now), **payload.model_dump()); save_idempotent_response(store, idempotency_key, data, result.model_dump(mode="json"), 201); return result


@router.get("/reminders", response_model=list[ReminderResponse])
def reminders(store: FarmStateStore = Depends(get_farm_store)):
    return [ReminderResponse(id=x["id"], field_id=x["field_id"], reminder_type=x["reminder_type"], scheduled_for=_dt(x["scheduled_for"]), status=x["status"], title=x["title"], created_at=_dt(x["created_at"])) for x in store.all("SELECT * FROM reminders ORDER BY scheduled_for LIMIT 500")]


@router.post("/tasks", response_model=FieldTaskResponse, status_code=201)
def create_task(payload: FieldTaskCreate, idempotency_key: str | None = Header(None, alias="Idempotency-Key"), store: FarmStateStore = Depends(get_farm_store)):
    _field(store, payload.field_id); data = payload.model_dump(mode="json"); cached = _cached(store, idempotency_key, data)
    if cached is not None: return FieldTaskResponse.model_validate(cached)
    task_id, now = str(uuid4()), iso_now(); store.execute("INSERT INTO field_tasks(id,field_id,title,due_at,status,source,created_at) VALUES(?,?,?,?,'open',?,?)", (task_id, payload.field_id, payload.title, payload.due_at.isoformat() if payload.due_at else None, payload.source, now)); result = _task(store.one("SELECT * FROM field_tasks WHERE id=?", (task_id,))); save_idempotent_response(store, idempotency_key, data, result.model_dump(mode="json"), 201); return result


@router.get("/tasks", response_model=list[FieldTaskResponse])
def tasks(field_id: str | None = None, status_filter: str | None = Query(None, alias="status"), limit: int = Query(100, ge=1, le=500), store: FarmStateStore = Depends(get_farm_store)):
    if field_id: _field(store, field_id)
    if status_filter and status_filter not in {"open", "completed", "cancelled"}: raise HTTPException(status_code=422, detail={"code": "invalid_status", "message": "status must be open, completed, or cancelled", "retryable": False})
    conditions = []; values: list[Any] = []
    if field_id: conditions.append("field_id=?"); values.append(field_id)
    if status_filter: conditions.append("status=?"); values.append(status_filter)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""; values.append(limit); return [_task(x) for x in store.all(f"SELECT * FROM field_tasks{where} ORDER BY created_at DESC LIMIT ?", values)]


@router.patch("/tasks/{task_id}", response_model=FieldTaskResponse)
def patch_task(task_id: str, payload: FieldTaskPatch, idempotency_key: str | None = Header(None, alias="Idempotency-Key"), store: FarmStateStore = Depends(get_farm_store)):
    data = payload.model_dump(mode="json"); cached = _cached(store, idempotency_key, data)
    if cached is not None: return FieldTaskResponse.model_validate(cached)
    if not store.one("SELECT id FROM field_tasks WHERE id=?", (task_id,)): raise HTTPException(status_code=404, detail={"code": "task_not_found", "message": "Task not found", "retryable": False})
    store.execute("UPDATE field_tasks SET status=? WHERE id=?", (payload.status, task_id)); result = _task(store.one("SELECT * FROM field_tasks WHERE id=?", (task_id,))); save_idempotent_response(store, idempotency_key, data, result.model_dump(mode="json")); return result


@router.post("/ledger/entries", response_model=LedgerEntryResponse, status_code=201)
def create_ledger(payload: LedgerEntryCreate, idempotency_key: str | None = Header(None, alias="Idempotency-Key"), store: FarmStateStore = Depends(get_farm_store)):
    if payload.field_id: _field(store, payload.field_id)
    data = payload.model_dump(mode="json"); cached = _cached(store, idempotency_key, data)
    if cached is not None: return LedgerEntryResponse.model_validate(cached)
    entry_id, now = str(uuid4()), iso_now(); store.execute("INSERT INTO ledger_entries(id,field_id,entry_type,category,title,amount_inr,occurred_at,crop_name,note,source,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?, 'active',?)", (entry_id, payload.field_id, payload.entry_type, payload.category, payload.title, payload.amount_inr, payload.occurred_at.isoformat(), payload.crop_name, payload.note, payload.source, now)); result = _ledger(store.one("SELECT * FROM ledger_entries WHERE id=?", (entry_id,))); save_idempotent_response(store, idempotency_key, data, result.model_dump(mode="json"), 201); return result


@router.get("/ledger/entries", response_model=list[LedgerEntryResponse])
def list_ledger(field_id: str | None = None, entry_type: str | None = None, status_filter: str | None = Query("active", alias="status"), limit: int = Query(100, ge=1, le=500), store: FarmStateStore = Depends(get_farm_store)):
    if field_id: _field(store, field_id)
    if entry_type and entry_type not in {"income", "expense"}: raise HTTPException(status_code=422, detail={"code": "invalid_entry_type", "message": "entry_type must be income or expense", "retryable": False})
    if status_filter and status_filter not in {"active", "void"}: raise HTTPException(status_code=422, detail={"code": "invalid_status", "message": "status must be active or void", "retryable": False})
    conditions = []; values: list[Any] = []
    if field_id: conditions.append("field_id=?"); values.append(field_id)
    if entry_type: conditions.append("entry_type=?"); values.append(entry_type)
    if status_filter: conditions.append("status=?"); values.append(status_filter)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""; values.append(limit); return [_ledger(x) for x in store.all(f"SELECT * FROM ledger_entries{where} ORDER BY occurred_at DESC,created_at DESC LIMIT ?", values)]


@router.get("/ledger/summary", response_model=LedgerSummaryResponse)
def ledger_summary(store: FarmStateStore = Depends(get_farm_store)):
    row = store.one("SELECT COALESCE(SUM(CASE WHEN entry_type='income' THEN amount_inr ELSE 0 END),0) income, COALESCE(SUM(CASE WHEN entry_type='expense' THEN amount_inr ELSE 0 END),0) expense, COUNT(*) count FROM ledger_entries WHERE status='active'"); income, expense = float(row["income"]), float(row["expense"]); return LedgerSummaryResponse(income_inr=income, expense_inr=expense, balance_inr=income-expense, active_entry_count=row["count"])


@router.patch("/ledger/entries/{entry_id}", response_model=LedgerEntryResponse)
def patch_ledger(entry_id: str, payload: LedgerEntryPatch, idempotency_key: str | None = Header(None, alias="Idempotency-Key"), store: FarmStateStore = Depends(get_farm_store)):
    data = payload.model_dump(mode="json"); cached = _cached(store, idempotency_key, data)
    if cached is not None: return LedgerEntryResponse.model_validate(cached)
    if not store.one("SELECT id FROM ledger_entries WHERE id=?", (entry_id,)): raise HTTPException(status_code=404, detail={"code": "ledger_entry_not_found", "message": "Ledger entry not found", "retryable": False})
    voided = iso_now() if payload.status == "void" else None; store.execute("UPDATE ledger_entries SET status=?,voided_at=? WHERE id=?", (payload.status, voided, entry_id)); result = _ledger(store.one("SELECT * FROM ledger_entries WHERE id=?", (entry_id,))); save_idempotent_response(store, idempotency_key, data, result.model_dump(mode="json")); return result


@router.get("/alerts", response_model=list[AlertResponse])
def alerts(status_filter: str | None = Query(None, alias="status"), limit: int = Query(100, ge=1, le=500), store: FarmStateStore = Depends(get_farm_store)):
    if status_filter: rows = store.all("SELECT * FROM alerts WHERE status=? ORDER BY created_at DESC LIMIT ?", (status_filter, limit))
    else: rows = store.all("SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?", (limit,))
    return [_alert(x) for x in rows]


@router.patch("/alerts/{alert_id}", response_model=AlertResponse)
def patch_alert(alert_id: str, payload: AlertPatch, idempotency_key: str | None = Header(None, alias="Idempotency-Key"), store: FarmStateStore = Depends(get_farm_store)):
    data = payload.model_dump(mode="json"); cached = _cached(store, idempotency_key, data)
    if cached is not None: return AlertResponse.model_validate(cached)
    if not store.one("SELECT id FROM alerts WHERE id=?", (alert_id,)): raise HTTPException(status_code=404, detail={"code": "alert_not_found", "message": "Alert not found", "retryable": False})
    store.execute("UPDATE alerts SET status=?,updated_at=? WHERE id=?", (payload.status, iso_now(), alert_id)); result = _alert(store.one("SELECT * FROM alerts WHERE id=?", (alert_id,))); save_idempotent_response(store, idempotency_key, data, result.model_dump(mode="json")); return result


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(request: Request, store: FarmStateStore = Depends(get_farm_store)):
    fields = fields_map(store); rows = store.all("SELECT * FROM alerts WHERE status='open' ORDER BY created_at DESC LIMIT 200"); weather = store.one("SELECT payload FROM weather_snapshots ORDER BY fetched_at DESC LIMIT 1"); warnings = []
    if not weather: warnings.append("Weather is unavailable until a provider-backed weather request succeeds.")
    else: weather = WeatherData.model_validate(json_value(weather["payload"], {}))
    return DashboardResponse(generated_at=datetime.now(timezone.utc), fields=fields, weather=weather, market_summary=[], alerts=[_alert(x) for x in rows], data_warnings=warnings)


@router.get("/audit")
def audit(limit: int = Query(100, ge=1, le=500), store: FarmStateStore = Depends(get_farm_store)):
    return {"events": [dict(x) for x in store.all("SELECT id,action,entity,created_at FROM audit_events ORDER BY created_at DESC LIMIT ?", (limit,))], "retention": "tenant_farmer_sqlite_store"}


@router.get("/export")
def export_snapshot(store: FarmStateStore = Depends(get_farm_store)):
    excluded_tables = {"schema_migrations", "ledger_entries"}
    tables = [x["name"] for x in store.all("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    return {"format": "kisansathi-farm-export-v2", "schema_version": 1, "tenant_id": store.tenant_id, "farmer_id": store.farmer_id, "exported_at": iso_now(), "excluded_tables": sorted(excluded_tables - set(tables)), "tables": {table: [dict(row) for row in store.all(f"SELECT * FROM [{table}] LIMIT 10000")] for table in tables if table not in excluded_tables}}


@router.post("/reports", response_model=ReportResponse, status_code=201)
def create_report(payload: ReportCreate, idempotency_key: str | None = Header(None, alias="Idempotency-Key"), store: FarmStateStore = Depends(get_farm_store)):
    data = payload.model_dump(mode="json"); cached = _cached(store, idempotency_key, data)
    if cached is not None: return ReportResponse.model_validate(cached)
    report_id, now = str(uuid4()), iso_now(); snapshot = {"fields": [dict(x) for x in store.all("SELECT id,name,area_acres,current_crop,status FROM fields WHERE active=1")], "open_alerts": [dict(x) for x in store.all("SELECT id,field_id,kind,title,severity FROM alerts WHERE status='open'")], "generated_from": "standalone_farm_state_sqlite"}; store.execute("INSERT INTO reports(id,report_type,from_date,to_date,status,input_snapshot,artifact,created_at,updated_at) VALUES(?,?,?,?, 'completed',?,?,?,?,?)", (report_id, payload.report_type, payload.from_date.isoformat() if payload.from_date else None, payload.to_date.isoformat() if payload.to_date else None, json_text(snapshot), json_text(snapshot), now, now)); result = ReportResponse(id=report_id, report_type=payload.report_type, from_date=payload.from_date, to_date=payload.to_date, status="completed", input_snapshot=snapshot, artifact=snapshot, created_at=_dt(now), updated_at=_dt(now)); save_idempotent_response(store, idempotency_key, data, result.model_dump(mode="json"), 201); return result


@router.get("/reports", response_model=list[ReportResponse])
def reports(store: FarmStateStore = Depends(get_farm_store)):
    return [ReportResponse(id=x["id"], report_type=x["report_type"], from_date=_date(x["from_date"]), to_date=_date(x["to_date"]), status=x["status"], input_snapshot=json_value(x["input_snapshot"], {}), artifact=json_value(x["artifact"]), created_at=_dt(x["created_at"]), updated_at=_dt(x["updated_at"])) for x in store.all("SELECT * FROM reports ORDER BY created_at DESC LIMIT 500")]


@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(report_id: str, store: FarmStateStore = Depends(get_farm_store)):
    row = store.one("SELECT * FROM reports WHERE id=?", (report_id,));
    if not row: raise HTTPException(status_code=404, detail={"code": "report_not_found", "message": "Report not found", "retryable": False})
    return ReportResponse(id=row["id"], report_type=row["report_type"], from_date=_date(row["from_date"]), to_date=_date(row["to_date"]), status=row["status"], input_snapshot=json_value(row["input_snapshot"], {}), artifact=json_value(row["artifact"]), created_at=_dt(row["created_at"]), updated_at=_dt(row["updated_at"]))


def _cached_weather(store: FarmStateStore, lat: float, lon: float) -> dict[str, Any] | None:
    row = store.one("SELECT payload,fetched_at FROM weather_snapshots WHERE ABS(latitude-?)<.01 AND ABS(longitude-?)<.01 ORDER BY fetched_at DESC LIMIT 1", (lat, lon))
    if not row: return None
    payload = json_value(row["payload"], {}); fetched = _dt(payload.get("fetched_at"))
    if not fetched or (datetime.now(timezone.utc)-fetched).total_seconds() > settings.weather_cache_seconds: return None
    payload["freshness_seconds"] = max(0, int((datetime.now(timezone.utc)-fetched).total_seconds())); return payload


@router.get("/weather", response_model=WeatherData)
async def weather(lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180), store: FarmStateStore = Depends(get_farm_store)):
    cached = _cached_weather(store, lat, lon)
    if cached: return WeatherData.model_validate(cached)
    try: payload = await fetch_weather(lat, lon)
    except WeatherProviderError as exc: raise HTTPException(status_code=503, detail={"code": "weather_provider_unavailable", "message": str(exc), "retryable": True}) from exc
    store.execute("INSERT INTO weather_snapshots(id,latitude,longitude,provider,observed_at,fetched_at,payload,freshness_seconds) VALUES(?,?,?,?,?,?,?,?)", (str(uuid4()), lat, lon, payload["provider"], payload["observed_at"], payload["fetched_at"], json_text(payload), payload["freshness_seconds"])); return WeatherData.model_validate(payload)


@router.get("/weather/alerts", response_model=list[WeatherAlertResponse])
async def weather_alerts(field_id: str, store: FarmStateStore = Depends(get_farm_store)):
    field = _field(store, field_id)
    if field["centroid_lat"] is None or field["centroid_lon"] is None: return []
    payload = _cached_weather(store, field["centroid_lat"], field["centroid_lon"])
    if not payload: return []
    observed = _dt(payload.get("observed_at")) or datetime.now(timezone.utc); fetched = _dt(payload.get("fetched_at")) or datetime.now(timezone.utc); provenance = Provenance(source=payload["provider"], observed_at=observed, fetched_at=fetched, freshness_seconds=payload.get("freshness_seconds", 0))
    return [WeatherAlertResponse(id=f"weather-rain-{field_id}-{item.get('observed_at')}", field_id=field_id, alert_type="heavy_rain_probability", title="Rain likely in forecast window", description=f"Forecast precipitation probability is {item.get('precipitation_probability'):.0f}% for {item.get('observed_at')}.", severity="warning", provenance=provenance) for item in payload.get("daily", []) if item.get("precipitation_probability") is not None and item["precipitation_probability"] >= 70]


@router.get("/diagnostics")
def diagnostics(request: Request, store: FarmStateStore = Depends(get_farm_store)):
    tables = {name: int(store.one(f"SELECT COUNT(*) count FROM [{name}]")["count"]) for name in ("fields", "soil_tests", "sensor_readings", "field_tasks", "alerts")}
    return {"status": "ready", "farmer_id": store.farmer_id, "farm_state": tables, "reference_database": "available" if getattr(request.app.state, "reference_db_available", False) else "unavailable", "model_mode": "placeholder_only", "warnings": ["Crop models are placeholders until an approved release manifest is available."]}
