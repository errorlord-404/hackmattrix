from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True)
class MoistureRuleResult:
    status: str
    target_moisture_percent: float
    what: str
    why: str
    when: str
    expected_benefit: str
    alternatives: list[str]
    confidence: float
    application_adjustment_percent: int | None = None
    lower_moisture_percent: float | None = None
    upper_moisture_percent: float | None = None
    catalog_crop: str | None = None
    catalog_stage: str | None = None
    decision_mode: str = "weather_aware"


@dataclass(frozen=True)
class OfflineMoistureBand:
    """Configurable local-demo screening band, never a controller setting."""

    crop: str
    stage: str
    lower_percent: float
    target_percent: float
    upper_percent: float


# This intentionally small catalogue makes the offline demo deterministic.
# These are configurable screening bands, not agronomy prescriptions or pump
# settings.  A verified crop/soil calibration must replace them before use in
# a real irrigation controller.
OFFLINE_MOISTURE_CATALOG: dict[str, tuple[float, float, float]] = {
    "tomato": (30.0, 40.0, 50.0),
    "potato": (27.0, 35.0, 45.0),
    "paddy": (30.0, 35.0, 45.0),
    "wheat": (25.0, 35.0, 45.0),
    "generic": (27.0, 35.0, 45.0),
}


def offline_moisture_band(crop_name: str | None, current_stage: str | None) -> OfflineMoistureBand:
    crop_key = (crop_name or "generic").strip().lower()
    crop_key = next((key for key in OFFLINE_MOISTURE_CATALOG if key != "generic" and key in crop_key), "generic")
    lower, target, upper = OFFLINE_MOISTURE_CATALOG[crop_key]
    stage = (current_stage or "unknown").strip().lower().replace(" ", "_")
    if stage in {"flowering", "fruiting", "grain_filling"}:
        lower, target, upper = lower + 2.0, target + 2.0, upper + 2.0
    return OfflineMoistureBand(crop=crop_key, stage=stage, lower_percent=lower, target_percent=target, upper_percent=upper)


def offline_irrigation_rule(
    moisture_percent: float | None, crop_name: str | None, current_stage: str | None, now: datetime | None = None,
) -> MoistureRuleResult:
    """Use only a stored sensor value and local catalogue; no forecast input."""
    now = now or datetime.now(timezone.utc)
    band = offline_moisture_band(crop_name, current_stage)
    common = dict(lower_moisture_percent=band.lower_percent, upper_moisture_percent=band.upper_percent,
                  catalog_crop=band.crop, catalog_stage=band.stage, decision_mode="offline_catalog")
    if moisture_percent is None:
        return MoistureRuleResult("insufficient_data", band.target_percent, "Do not schedule irrigation yet",
            "A current percentage moisture reading is required before the local catalogue can screen this field.",
            "After a fresh moisture reading is available", "Avoids an unsupported irrigation decision",
            ["Record a calibrated moisture reading"], 0.0, **common)
    if moisture_percent >= band.upper_percent:
        return MoistureRuleResult("above_upper_limit", band.target_percent, "Do not irrigate; inspect drainage",
            f"Latest moisture is {moisture_percent:.1f}%, at or above the local upper screening bound of {band.upper_percent:.1f}%.",
            "Inspect drainage and recheck after the next observation", "Avoids adding water above the local screening range",
            ["Inspect low spots and drainage", "Recheck the sensor placement"], 0.75, 0, **common)
    if moisture_percent >= band.target_percent:
        return MoistureRuleResult("not_required", band.target_percent, "Do not irrigate now",
            f"Latest moisture is {moisture_percent:.1f}%, at or above the local {band.target_percent:.1f}% target.",
            "Recheck after the next observation", "Avoids unnecessary water use", ["Continue monitoring moisture"], 0.8, 0, **common)
    urgency = "below the lower screening threshold" if moisture_percent < band.lower_percent else "below the local target"
    return MoistureRuleResult("recommended", band.target_percent, "Plan a farmer-confirmed irrigation",
        f"Latest moisture is {moisture_percent:.1f}%, {urgency}. The offline rule aims toward {band.target_percent:.1f}% and never treats {band.upper_percent:.1f}% as an irrigation target.",
        (now + timedelta(hours=6)).isoformat().replace("+00:00", "Z"), "Moves moisture toward the local screening target",
        ["Use the farmer's calibrated application method", "Recheck moisture before any further application"], 0.65, 100, **common)


@dataclass(frozen=True)
class CropStageActionProposal:
    """A reviewable, non-prescriptive task suggestion for a canonical stage."""

    title: str
    why: str
    due_hint: str
    source: str = "crop_stage_rule_v1"


def crop_stage_action_proposals(stage: str, crop_name: str) -> list[CropStageActionProposal]:
    """Return generic lifecycle actions without creating work or prescribing inputs.

    Crop-specific chemical, seed, or nutrient actions must come from a reviewed
    crop pack.  These proposals only help the farmer keep a verifiable farm
    record and observe the stage at the right time.
    """
    crop = crop_name.strip() or "crop"
    templates = {
        "land_preparation": [("Review soil-test baseline", "A recorded laboratory/Soil Health Card baseline is needed before a nutrient plan.", "Before seed/input selection")],
        "seed_treatment": [("Record seed lot and treatment label", "Traceability helps investigate a poor stand without inventing a treatment recommendation.", "Before sowing")],
        "sowing": [(f"Record {crop} sowing details", "Planting date and variety are required for a useful crop calendar and harvest-readiness review.", "Today")],
        "germination": [("Inspect emergence and capture a field note", "An early emergence check can identify gaps or poor establishment for review.", "Within the next few days")],
        "vegetative": [("Walk the field and record visible pest, weed, or stress signs", "Photo and observation history are more useful than a generic treatment instruction.", "This week")],
        "flowering": [("Check crop health and moisture at flowering", "This is a stage-sensitive period; confirm conditions before any input decision.", "Today or after the next sensor reading")],
        "fruiting": [("Capture representative crop-health photos", "A consistent photo record supports review of visible disease or pest symptoms.", "This week")],
        "grain_filling": [("Review moisture and weather before grain filling", "Stage and location-matched conditions should be reviewed before irrigation changes.", "After the next fresh reading")],
        "maturity": [("Plan harvest and logistics requirements", "Harvest readiness, labor, machinery, storage, and market checks need farmer confirmation.", "Before harvest")],
        "harvest": [("Record harvested quantity and quality notes", "A dated farmer record supports ledger and market-realisation review.", "At harvest")],
    }
    return [CropStageActionProposal(title=title, why=why, due_hint=due) for title, why, due in templates.get(stage, [])]


def irrigation_rule(
    moisture_percent: float | None,
    rain_probability: float | None,
    current_stage: str | None,
    recent_irrigation: bool = False,
    now: datetime | None = None,
    rainfall_mm_next_48h: float | None = None,
    rain_probability_next_48h: float | None = None,
) -> MoistureRuleResult:
    now = now or datetime.now(timezone.utc)
    target = 35.0
    if current_stage and current_stage.lower().replace(" ", "_") in {"flowering", "fruiting", "grain_filling"}:
        target = 40.0
    if moisture_percent is None:
        return MoistureRuleResult(
            status="insufficient_data",
            target_moisture_percent=target,
            what="Do not schedule irrigation yet",
            why="A current soil-moisture observation is required before calculating water need.",
            when="After a fresh moisture reading is available",
            expected_benefit="Avoids an unsupported irrigation decision",
            alternatives=["Record a sensor reading or field observation"],
            confidence=0.0,
        )
    # A forecast probability only says rain may occur. A waterlogging-aware
    # decision needs an expected amount across the next two days as well.
    # These are intentionally broad screening thresholds, not crop-specific
    # hydrology or an irrigation-controller command.
    heavy_rain_soon = (
        rainfall_mm_next_48h is not None
        and rainfall_mm_next_48h >= 25
        and (rain_probability_next_48h is None or rain_probability_next_48h >= 70)
    )
    # Probability alone is not enough to postpone irrigation for a critically
    # dry root zone. A crop/soil-specific water balance may later refine these
    # screening bounds once the required field parameters are recorded.
    critical = target - 15.0
    if moisture_percent < critical:
        if heavy_rain_soon:
            return MoistureRuleResult(
                status="reduce_for_heavy_rain",
                target_moisture_percent=target,
                what="Avoid a full irrigation; use only a small emergency split if plants show water stress",
                why=(f"Moisture is critically low at {moisture_percent:.1f}%, but {rainfall_mm_next_48h:.1f} mm of rain is forecast "
                     "within 48 hours. A full application could increase waterlogging risk."),
                when="Inspect crop stress and drainage now; recheck moisture after the rain window",
                expected_benefit="Protects a critically dry crop while limiting extra water before heavy rain",
                alternatives=["Use at most 25% of the farmer's calibrated normal split only if wilting is observed", "Inspect drains, low spots, and runoff paths", "Recheck moisture after rainfall"],
                confidence=0.7,
                application_adjustment_percent=25,
            )
        return MoistureRuleResult(
            status="recommended",
            target_moisture_percent=target,
            what="Irrigate during the next suitable window",
            why=(f"Latest moisture is {moisture_percent:.1f}%, below the critical {critical:.1f}% screening bound. "
                 "Rain probability alone is not enough to defer a dry-field check."),
            when=(now + timedelta(hours=6)).isoformat().replace("+00:00", "Z"),
            expected_benefit="Reduces the risk of continued water stress while the forecast is monitored",
            alternatives=["Use a smaller split irrigation and recheck moisture", "Inspect drainage and sensor placement"],
            confidence=0.75 if rain_probability is not None else 0.65,
            application_adjustment_percent=100,
        )
    if moisture_percent >= target:
        if heavy_rain_soon:
            return MoistureRuleResult(
                status="protect_from_waterlogging",
                target_moisture_percent=target,
                what="Do not irrigate; prepare drainage for forecast heavy rain",
                why=(f"Moisture is {moisture_percent:.1f}%, and {rainfall_mm_next_48h:.1f} mm is forecast within 48 hours. "
                     "Additional irrigation would increase waterlogging risk."),
                when="Inspect drainage before the rain window and recheck moisture afterward",
                expected_benefit="Avoids adding water before a potentially saturating rainfall event",
                alternatives=["Clear field drains if safe", "Check low-lying areas after rainfall"],
                confidence=0.85,
                application_adjustment_percent=0,
            )
        return MoistureRuleResult(
            status="not_required",
            target_moisture_percent=target,
            what="Do not irrigate now",
            why=f"Latest moisture is {moisture_percent:.1f}%, at or above the {target:.1f}% target.",
            when="Recheck after the next observation",
            expected_benefit="Avoids unnecessary water use",
            alternatives=["Continue monitoring moisture"],
            confidence=0.9,
            application_adjustment_percent=0,
        )
    if recent_irrigation:
        return MoistureRuleResult(
            status="reassess_after_recent_irrigation",
            target_moisture_percent=target,
            what="Recheck moisture before another irrigation",
            why="A farmer-recorded irrigation event is recent, and the current moisture is not in the critical screening range.",
            when=(now + timedelta(hours=6)).isoformat().replace("+00:00", "Z"),
            expected_benefit="Avoids applying another irrigation before the previous application has been observed",
            alternatives=["Record a fresh moisture reading", "Inspect for runoff, leaks, or uneven wetting"],
            confidence=0.7,
            application_adjustment_percent=0,
        )
    # A small deficit may be deferred on a strong location-matched forecast;
    # the critical bound above prevents this probability-only path from
    # postponing water for a dry field.
    if heavy_rain_soon:
        return MoistureRuleResult(
            status="defer_for_heavy_rain",
            target_moisture_percent=target,
            what="Defer irrigation and prepare for heavy-rain drainage",
            why=(f"Moisture is {moisture_percent:.1f}%, below target, but {rainfall_mm_next_48h:.1f} mm is forecast "
                 "within 48 hours. Extra water before this event could cause waterlogging."),
            when="Recheck moisture and field drainage after the rain window",
            expected_benefit="Avoids unnecessary water and reduces waterlogging risk",
            alternatives=["Inspect drains and low spots", "Irrigate only if rainfall misses the field and moisture remains below target"],
            confidence=0.85,
            application_adjustment_percent=0,
        )
    if rain_probability is not None and rain_probability >= 60:
        return MoistureRuleResult(
            status="defer_for_rain",
            target_moisture_percent=target,
            what="Defer irrigation and monitor the forecast",
            why=f"Moisture is {moisture_percent:.1f}%, but forecast rain probability is {rain_probability:.0f}%.",
            when="Recheck after the forecast rain window",
            expected_benefit="Reduces avoidable irrigation before expected rain",
            alternatives=["Irrigate only if the rain does not arrive and moisture remains below target"],
            confidence=0.8,
            application_adjustment_percent=0,
        )
    return MoistureRuleResult(
        status="recommended",
        target_moisture_percent=target,
        what="Irrigate during the next suitable window",
        why=f"Latest moisture is {moisture_percent:.1f}%, below the {target:.1f}% target, with no strong rain deferral signal.",
        when=(now + timedelta(hours=12)).isoformat().replace("+00:00", "Z"),
        expected_benefit="Moves root-zone moisture toward the crop-stage target",
        alternatives=["Use a smaller split irrigation and recheck moisture"],
        confidence=0.75 if rain_probability is not None else 0.6,
        application_adjustment_percent=100,
    )


def soil_interpretation(values: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    recommendations: list[dict[str, Any]] = []
    if values.get("ph") is not None and (values["ph"] < 5.5 or values["ph"] > 8.0):
        recommendations.append({
            "what": "Review soil pH correction with a local agronomist",
            "why": f"Recorded pH is {values['ph']:.2f}, outside the broad 5.5–8.0 screening range.",
            "when": "Before the next nutrient application",
            "cost_estimate": "Not estimated: product and local rates are not supplied",
            "expected_benefit": "Improves nutrient availability after validated correction",
            "alternatives": ["Repeat a calibrated soil test"],
            "confidence": 0.65,
        })
    if values.get("nitrogen") is not None and values["nitrogen"] < 280:
        recommendations.append({
            "what": "Investigate a nitrogen deficiency",
            "why": f"Recorded nitrogen is {values['nitrogen']:.1f}, below the configured screening threshold of 280.",
            "when": "Before selecting a fertilizer dose",
            "cost_estimate": "Not estimated: fertilizer product and area rate are not supplied",
            "expected_benefit": "Supports a targeted nutrient plan",
            "alternatives": ["Confirm with a laboratory test and crop-specific recommendation"],
            "confidence": 0.6,
        })
    status = "attention_required" if recommendations else "within_screening_ranges"
    return status, recommendations

