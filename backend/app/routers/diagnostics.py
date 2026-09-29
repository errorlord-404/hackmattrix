from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.config import settings
from app.farm_state.dependencies import get_farm_store
from app.farm_state.store import FarmStateStore
from app.farm_state.store import json_value
from app.models.gov_scheme import GovScheme
from app.models.machinery_rental import MachineryRental
from app.models.marketplace_listing import MarketplaceListing
from app.services.crop_health import model_registry_summary
from app.schemas.onboarding import OnboardingStatusResponse


router = APIRouter(prefix="/v1", tags=["diagnostics"])


def _count(store: FarmStateStore, table: str, where: str = "") -> int:
    row = store.one(f"SELECT COUNT(*) AS total FROM {table}{where}")
    return int(row["total"] if row else 0)


@router.get("/onboarding-status", response_model=OnboardingStatusResponse)
def onboarding_status(request: Request, store: FarmStateStore = Depends(get_farm_store)):
    """Summarize missing setup for the bound farmer without creating state."""
    profile = store.one(
        "SELECT preferred_language, latitude, longitude FROM profile WHERE id = ?",
        (store.farmer_key,),
    )
    fields = store.all(
        "SELECT boundary_geojson, current_crop FROM fields WHERE active = 1 ORDER BY created_at"
    )
    quality_counts = {"approximate": 0, "farmer_drawn_unverified": 0, "unclassified": 0}
    with_crop = 0
    for field in fields:
        if field["current_crop"] and field["current_crop"].strip():
            with_crop += 1
        boundary = json_value(field["boundary_geojson"], {})
        properties = boundary.get("properties", {}) if isinstance(boundary, dict) else {}
        quality = properties.get("quality") if isinstance(properties, dict) else None
        if quality == "approximate_point_buffer":
            quality_counts["approximate"] += 1
        elif quality == "farmer_drawn_unverified":
            quality_counts["farmer_drawn_unverified"] += 1
        else:
            quality_counts["unclassified"] += 1

    active_cycle_row = store.one(
        "SELECT COUNT(DISTINCT crop_cycles.field_id) AS total FROM crop_cycles "
        "JOIN fields ON fields.id = crop_cycles.field_id "
        "WHERE crop_cycles.status = 'active' AND fields.active = 1"
    )
    active_cycles = int(active_cycle_row["total"] if active_cycle_row else 0)

    has_coordinates = bool(profile and profile["latitude"] is not None and profile["longitude"] is not None)
    if not profile:
        next_step = "create_profile"
    elif not has_coordinates:
        next_step = "set_location"
    elif not fields:
        next_step = "create_field"
    elif quality_counts["approximate"] or quality_counts["unclassified"]:
        next_step = "review_boundary"
    elif not with_crop:
        next_step = "choose_crop"
    elif not active_cycles:
        next_step = "start_crop_cycle"
    else:
        next_step = "ready"

    latest_sensor = store.one("SELECT MAX(observed_at) AS observed_at FROM sensor_readings")
    limitations = ["Field boundary quality labels are farmer-supplied and are not survey verification."]
    if not settings.SARVAM_API_KEY.strip():
        limitations.append("Voice and translation are not configured.")
    if not getattr(request.app.state, "reference_db_available", False):
        limitations.append("Shared crop, scheme, and provider references may be unavailable.")
    if not latest_sensor or not latest_sensor["observed_at"]:
        limitations.append("No sensor observation is recorded; do not infer current soil moisture.")
    return OnboardingStatusResponse(
        profile={
            "exists": bool(profile),
            "has_coordinates": has_coordinates,
            "preferred_language": profile["preferred_language"] if profile else None,
        },
        fields={
            "active_count": len(fields),
            "with_crop_count": with_crop,
            "with_active_cycle_count": active_cycles,
            "approximate_boundaries": quality_counts["approximate"],
            "farmer_drawn_unverified_boundaries": quality_counts["farmer_drawn_unverified"],
            "unclassified_boundaries": quality_counts["unclassified"],
        },
        latest_sensor_observed_at=latest_sensor["observed_at"] if latest_sensor else None,
        voice_configured=bool(settings.SARVAM_API_KEY.strip()),
        reference_database_available=bool(getattr(request.app.state, "reference_db_available", False)),
        next_setup_step=next_step,
        limitations=limitations,
    )


@router.get("/diagnostics")
async def diagnostics(request: Request, store: FarmStateStore = Depends(get_farm_store)):
    """Return safe, farmer-scoped readiness information for the demo shell.

    This endpoint intentionally omits filesystem paths, secrets, and provider
    credentials. Counts are operational hints, not a claim that records are
    live or verified.
    """
    reference_available = bool(getattr(request.app.state, "reference_db_available", False))
    counts = {
        "fields": _count(store, "fields", " WHERE active = 1"),
        "open_tasks": _count(store, "field_tasks", " WHERE status = 'open'"),
        "open_alerts": _count(store, "alerts", " WHERE status = 'open'"),
        "soil_tests": _count(store, "soil_tests"),
        "sensor_readings": _count(store, "sensor_readings"),
        "device_packets": _count(store, "device_telemetry_packets"),
    }

    reference_counts = {"schemes": 0, "machinery": 0, "marketplace": 0}
    reference_error = None
    if reference_available:
        try:
            reference_counts = {
                "schemes": await GovScheme.count(),
                "machinery": await MachineryRental.count(),
                "marketplace": await MarketplaceListing.count(),
            }
        except Exception as exc:  # pragma: no cover - depends on Mongo availability
            reference_available = False
            reference_error = str(exc)

    components = {
        "farm_state": {"status": "available", "mode": "server_local_sqlite"},
        "reference_database": {
            "status": "available" if reference_available else "unavailable",
            "counts": reference_counts,
            "error": reference_error,
        },
        "codex": {"status": "desktop_managed", "message": "Codex status is reported by the Electron harness."},
        "sarvam": {
            "status": "configured" if settings.SARVAM_API_KEY.strip() else "unconfigured",
            "message": "Speech and translation routes are ready." if settings.SARVAM_API_KEY.strip() else "Set SARVAM_API_KEY to enable voice services.",
        },
        "optional_providers": {
            "weather": settings.WEATHER_PROVIDER,
            "diagnosis": settings.DIAGNOSIS_PROVIDER,
        },
        "crop_models": model_registry_summary(),
    }
    degraded = []
    if not reference_available:
        degraded.append("reference_database")
    if not settings.SARVAM_API_KEY.strip():
        degraded.append("sarvam")
    return {
        "status": "ready" if not degraded else "degraded",
        "farmer_state": counts,
        "components": components,
        "degraded_components": degraded,
        "demo_data_policy": "Counts may include local_demo records; verify source and freshness before acting.",
    }
