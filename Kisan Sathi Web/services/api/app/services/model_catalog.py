"""Fail-closed runtime view of the hierarchical crop model catalog.

Research candidates are deliberately visible for planning but never returned as
loadable artifacts. Only entries marked approved can participate in routing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class ModelCatalogError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CropCandidate:
    crop: str
    score: float


@dataclass(frozen=True, slots=True)
class RouteDecision:
    status: str
    crop: str | None
    specialist_id: str | None
    reason: str
    requires_farmer_confirmation: bool


class HierarchicalModelCatalog:
    def __init__(self, document: dict[str, Any]) -> None:
        self.document = document
        self.models = tuple(document.get("models", ()))
        self.coverage = tuple(document.get("coverage", {}).get("crop_ids", ()))
        identifiers = [entry for entry in self.models if entry.get("role") == "crop_identifier"]
        if len(identifiers) != 1:
            raise ModelCatalogError("model catalog must contain exactly one crop identifier")
        self.identifier = identifiers[0]
        self.specialists = {
            entry["crop"]: entry
            for entry in self.models
            if entry.get("role") == "disease_specialist" and entry.get("crop") in self.coverage
        }
        if set(self.specialists) != set(self.coverage):
            raise ModelCatalogError("model catalog specialist coverage is incomplete")

    @classmethod
    def from_path(cls, path: Path) -> "HierarchicalModelCatalog":
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ModelCatalogError("model catalog is unavailable") from exc
        if not isinstance(document, dict) or document.get("schema_version") != "2.0":
            raise ModelCatalogError("model catalog version is unsupported")
        return cls(document)

    @staticmethod
    def _approved(entry: dict[str, Any]) -> bool:
        artifacts = entry.get("artifacts", {})
        return bool(
            entry.get("status") == "approved"
            and artifacts.get("release_manifest")
            and artifacts.get("model", {}).get("path")
            and artifacts.get("labels", {}).get("path")
        )

    def public_capabilities(self) -> dict[str, Any]:
        approved_identifier = self._approved(self.identifier)
        crops = [
            {
                "crop": crop,
                "status": entry["status"],
                "client_eligible": self._approved(entry) and bool(entry["runtime"]["browser_backends"]),
                "server_eligible": self._approved(entry) and bool(entry["runtime"]["server"]),
                "lazy_load": bool(entry["runtime"]["lazy_load"]),
            }
            for crop, entry in sorted(self.specialists.items())
        ]
        approved_specialists = sum(item["client_eligible"] or item["server_eligible"] for item in crops)
        return {
            "architecture": "crop_identifier_then_crop_specialist",
            "mode": "active" if approved_identifier and approved_specialists else "scaffold",
            "identifier_status": self.identifier["status"],
            "approved_identifier": approved_identifier,
            "coverage_id": self.document["coverage"]["coverage_id"],
            "coverage_count": len(self.coverage),
            "approved_specialist_count": approved_specialists,
            "browser_order": ["webgpu", "wasm"],
            "fallback": "server_then_expert_review",
            "crops": crops,
        }

    def select_specialist(
        self,
        candidates: Iterable[CropCandidate],
        *,
        confirmed_crop: str | None = None,
        minimum_score: float = 0.75,
        minimum_margin: float = 0.12,
    ) -> RouteDecision:
        if confirmed_crop:
            specialist = self.specialists.get(confirmed_crop)
            if specialist is None:
                return RouteDecision("unsupported_crop", confirmed_crop, None, "The confirmed crop is outside this catalog.", False)
            if not self._approved(specialist):
                return RouteDecision("needs_expert_review", confirmed_crop, None, "The confirmed crop has no approved disease specialist.", False)
            return RouteDecision("routed", confirmed_crop, specialist["model_id"], "Farmer-confirmed crop has an approved specialist.", False)

        if not self._approved(self.identifier):
            return RouteDecision("needs_crop_confirmation", None, None, "No approved crop identifier is available; ask the farmer to confirm the crop.", True)
        ordered = sorted(candidates, key=lambda item: item.score, reverse=True)
        if not ordered:
            return RouteDecision("needs_crop_confirmation", None, None, "The crop identifier returned no candidate.", True)
        winner = ordered[0]
        runner_up = ordered[1].score if len(ordered) > 1 else 0.0
        if winner.score < minimum_score or winner.score - runner_up < minimum_margin:
            return RouteDecision("needs_crop_confirmation", winner.crop, None, "The crop identifier is ambiguous.", True)
        specialist = self.specialists.get(winner.crop)
        if specialist is None or not self._approved(specialist):
            return RouteDecision("needs_expert_review", winner.crop, None, "The identified crop has no approved disease specialist.", False)
        return RouteDecision("routed", winner.crop, specialist["model_id"], "High-confidence crop route has an approved specialist.", False)
