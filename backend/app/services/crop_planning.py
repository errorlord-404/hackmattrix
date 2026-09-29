"""Transparent crop-option evidence comparison; intentionally not a predictor."""

from __future__ import annotations

from typing import Any


def _normalise(value: str | None) -> str:
    return " ".join((value or "").strip().lower().replace("_", " ").replace("-", " ").split())


def _matches(value: str | None, options: list[str]) -> bool | None:
    if not value or not options:
        return None
    wanted = _normalise(value)
    normalised = {_normalise(option) for option in options}
    return wanted in normalised or "any" in normalised


def compare_crop_options(
    crops: list[Any], *, season: str, previous_crop: str | None, soil_type: str | None
) -> list[dict[str, Any]]:
    """Return sourced candidates and missing evidence without a profitability claim."""
    results: list[dict[str, Any]] = []
    for crop in crops:
        season_match = _matches(season, [crop.season] if getattr(crop, "season", None) else [])
        rotation_match = _matches(previous_crop, list(getattr(crop, "previous_crop_compatibility", []) or []))
        soil_match = _matches(soil_type, list(getattr(crop, "soil_compatibility", []) or []))
        checks = {
            "season": season_match,
            "previous_crop_rotation": rotation_match,
            "soil_type": soil_match,
        }
        missing = [name for name, result in checks.items() if result is None]
        conflicts = [name for name, result in checks.items() if result is False]
        results.append({
            "crop_name": crop.name,
            "season": getattr(crop, "season", None),
            "reference_price_per_quintal": getattr(crop, "avg_price_per_quintal", None),
            "price_source": getattr(crop, "source", None),
            "source_url": getattr(crop, "source_url", None),
            "checks": checks,
            "missing_evidence": missing,
            "conflicts": conflicts,
            "status": "candidate_needs_review" if not conflicts else "not_recommended_with_current_inputs",
        })
    return results
