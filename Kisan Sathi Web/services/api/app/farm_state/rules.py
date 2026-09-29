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


@dataclass(frozen=True)
class CropStageActionProposal:
    title: str
    why: str
    due_hint: str
    source: str = "crop_stage_rule_v1"


def crop_stage_action_proposals(stage: str, crop_name: str) -> list[CropStageActionProposal]:
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
    return [CropStageActionProposal(title=t, why=w, due_hint=d) for t, w, d in templates.get(stage, [])]


def irrigation_rule(moisture_percent: float | None, rain_probability: float | None, current_stage: str | None, recent_irrigation: bool = False, now: datetime | None = None) -> MoistureRuleResult:
    now = now or datetime.now(timezone.utc)
    target = 40.0 if current_stage and current_stage.lower().replace(" ", "_") in {"flowering", "fruiting", "grain_filling"} else 35.0
    if moisture_percent is None:
        return MoistureRuleResult("insufficient_data", target, "Do not schedule irrigation yet", "A current soil-moisture observation is required before calculating water need.", "After a fresh moisture reading is available", "Avoids an unsupported irrigation decision", ["Record a sensor reading or field observation"], 0.0)
    critical = target - 15.0
    if moisture_percent < critical:
        return MoistureRuleResult("recommended", target, "Irrigate during the next suitable window", f"Latest moisture is {moisture_percent:.1f}%, below the critical {critical:.1f}% screening bound. Rain probability alone is not enough to defer a dry-field check.", (now + timedelta(hours=6)).isoformat().replace("+00:00", "Z"), "Reduces the risk of continued water stress while the forecast is monitored", ["Use a smaller split irrigation and recheck moisture", "Inspect drainage and sensor placement"], 0.75 if rain_probability is not None else 0.65)
    if moisture_percent >= target:
        return MoistureRuleResult("not_required", target, "Do not irrigate now", f"Latest moisture is {moisture_percent:.1f}%, at or above the {target:.1f}% target.", "Recheck after the next observation", "Avoids unnecessary water use", ["Continue monitoring moisture"], 0.9)
    if recent_irrigation:
        return MoistureRuleResult("reassess_after_recent_irrigation", target, "Recheck moisture before another irrigation", "A farmer-recorded irrigation event is recent, and the current moisture is not in the critical screening range.", (now + timedelta(hours=6)).isoformat().replace("+00:00", "Z"), "Avoids applying another irrigation before the previous application has been observed", ["Record a fresh moisture reading", "Inspect for runoff, leaks, or uneven wetting"], 0.7)
    if rain_probability is not None and rain_probability >= 60:
        return MoistureRuleResult("defer_for_rain", target, "Defer irrigation and monitor the forecast", f"Moisture is {moisture_percent:.1f}%, but forecast rain probability is {rain_probability:.0f}%.", "Recheck after the forecast rain window", "Reduces avoidable irrigation before expected rain", ["Irrigate only if the rain does not arrive and moisture remains below target"], 0.8)
    return MoistureRuleResult("recommended", target, "Irrigate during the next suitable window", f"Latest moisture is {moisture_percent:.1f}%, below the {target:.1f}% target, with no strong rain deferral signal.", (now + timedelta(hours=12)).isoformat().replace("+00:00", "Z"), "Moves root-zone moisture toward the crop-stage target", ["Use a smaller split irrigation and recheck moisture"], 0.75 if rain_probability is not None else 0.6)


def soil_interpretation(values: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    recommendations: list[dict[str, Any]] = []
    if values.get("ph") is not None and (values["ph"] < 5.5 or values["ph"] > 8.0):
        recommendations.append({"what": "Review soil pH correction with a local agronomist", "why": f"Recorded pH is {values['ph']:.2f}, outside the broad 5.5–8.0 screening range.", "when": "Before the next nutrient application", "cost_estimate": "Not estimated: product and local rates are not supplied", "expected_benefit": "Improves nutrient availability after validated correction", "alternatives": ["Repeat a calibrated soil test"], "confidence": 0.65})
    if values.get("nitrogen") is not None and values["nitrogen"] < 280:
        recommendations.append({"what": "Investigate a nitrogen deficiency", "why": f"Recorded nitrogen is {values['nitrogen']:.1f}, below the configured screening threshold of 280.", "when": "Before selecting a fertilizer dose", "cost_estimate": "Not estimated: fertilizer product and area rate are not supplied", "expected_benefit": "Supports a targeted nutrient plan", "alternatives": ["Confirm with a laboratory test and crop-specific recommendation"], "confidence": 0.6})
    return ("attention_required" if recommendations else "within_screening_ranges", recommendations)
