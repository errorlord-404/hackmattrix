"""Pure orchestration policy between a crop router and specialist disease models.

This contains no model inference or treatment advice. It makes uncertain routing
visible so a UI can ask the farmer to confirm the crop instead of silently
running the wrong specialist.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CropCandidate:
    crop: str
    score: float


@dataclass(frozen=True)
class RouteDecision:
    status: str
    crop: str | None
    specialist_id: str | None
    reason: str
    requires_farmer_confirmation: bool


def select_specialist(
    candidates: list[CropCandidate],
    specialists: dict[str, str],
    *,
    confirmed_crop: str | None = None,
    minimum_score: float = 0.75,
    minimum_margin: float = 0.12,
) -> RouteDecision:
    """Pick a compatible specialist or explicitly request confirmation/stop."""
    if confirmed_crop:
        specialist = specialists.get(confirmed_crop)
        if specialist:
            return RouteDecision("routed", confirmed_crop, specialist, "Farmer-confirmed crop has a supported specialist.", False)
        return RouteDecision("unsupported_crop", confirmed_crop, None, "The confirmed crop has no released disease specialist.", False)
    ordered = sorted(candidates, key=lambda item: item.score, reverse=True)
    if not ordered:
        return RouteDecision("needs_crop_confirmation", None, None, "No crop-router candidate was supplied.", True)
    winner = ordered[0]
    runner_up = ordered[1].score if len(ordered) > 1 else 0.0
    if winner.score < minimum_score or winner.score - runner_up < minimum_margin:
        return RouteDecision("needs_crop_confirmation", winner.crop, None, "Crop-router result is ambiguous; ask the farmer before diagnosis.", True)
    specialist = specialists.get(winner.crop)
    if not specialist:
        return RouteDecision("unsupported_crop", winner.crop, None, "Crop was identified but no released specialist is available.", False)
    return RouteDecision("routed", winner.crop, specialist, "High-confidence supported crop route.", False)
