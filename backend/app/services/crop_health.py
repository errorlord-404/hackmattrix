"""Fail-closed local crop-health inference adapter.

This adapter consumes the versioned fine-tuning checkpoint contract in ``ml/``.
It intentionally returns a review state when a model is absent, the crop is
unknown, or a specialist is not released. It does not prescribe treatment.
"""

from __future__ import annotations

import json
import sys
import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings

REPO_ROOT = Path(__file__).resolve().parents[3]
ML_ROOT = REPO_ROOT / "ml"


def _normalise_crop(value: str | None) -> str | None:
    if not value:
        return None
    crop = value.strip().lower().replace("-", "_").replace(" ", "_")
    return None if crop in {"unknown", "i_do_not_know", "none"} else crop


def _checkpoint_paths() -> tuple[Path | None, dict[str, Path]]:
    router = Path(settings.CROP_HEALTH_ROUTER_MODEL_PATH).expanduser() if settings.CROP_HEALTH_ROUTER_MODEL_PATH else None
    try:
        configured = json.loads(settings.CROP_HEALTH_SPECIALIST_MODELS_JSON)
    except json.JSONDecodeError:
        configured = {}
    specialists = {str(crop).lower(): Path(str(path)).expanduser() for crop, path in configured.items() if path}
    return router, specialists


@lru_cache(maxsize=1)
def _runtime():
    # Training/orchestration intentionally stays outside the FastAPI package so
    # it can be evaluated and released independently.
    if str(ML_ROOT) not in sys.path:
        sys.path.insert(0, str(ML_ROOT))
    from orchestration.hierarchical_inference import run_hierarchical_inference
    return run_hierarchical_inference


def model_registry_summary() -> dict[str, Any]:
    """Return safe registry metadata for the desktop diagnostics surface."""
    if settings.DIAGNOSIS_PROVIDER != "local_model_registry_demo":
        return {"status": "disabled", "research_only": True, "models": []}
    if not settings.CROP_HEALTH_MODEL_REGISTRY_PATH or not settings.CROP_HEALTH_MODEL_ROOT:
        return {"status": "unconfigured", "research_only": True, "models": []}
    if str(ML_ROOT) not in sys.path:
        sys.path.insert(0, str(ML_ROOT))
    try:
        from inference.crop_model_registry import CropModelRegistry, RegistryError
    except ImportError as exc:
        return {"status": "unavailable", "research_only": True, "models": [], "error": f"ML runtime is unavailable: {exc}"}
    registry_path = Path(settings.CROP_HEALTH_MODEL_REGISTRY_PATH).expanduser()
    model_root = Path(settings.CROP_HEALTH_MODEL_ROOT).expanduser()
    if not registry_path.is_absolute():
        registry_path = REPO_ROOT / registry_path
    if not model_root.is_absolute():
        model_root = REPO_ROOT / model_root
    try:
        return {"status": "available", **CropModelRegistry(registry_path, model_root).summary()}
    except RegistryError as exc:
        return {"status": "unavailable", "research_only": True, "models": [], "error": str(exc)}


def diagnose_image(image_path: Path, confirmed_crop: str | None = None) -> dict[str, Any]:
    """Run an approved local two-stage model, or return a safe non-diagnosis."""
    crop = _normalise_crop(confirmed_crop)
    router, specialists = _checkpoint_paths()
    provider = settings.DIAGNOSIS_PROVIDER
    base: dict[str, Any] = {
        "provider": provider,
        "crop": crop,
        "model_id": "local-hierarchical-crop-health",
        "model_version": "demo-v0.1",
        "inference_location": "local-server",
        "limitations": [
            "This prototype model is trained on controlled leaf images and is not field validated.",
            "Use a qualified agronomist before changing pesticide or fertiliser use.",
        ],
    }
    if provider == "local_tflite_demo":
        from app.services.tflite_crop_health import run_tflite_specialist
        return run_tflite_specialist(image_path, confirmed_crop)
    if provider == "local_model_registry_demo":
        if not settings.CROP_HEALTH_MODEL_REGISTRY_PATH or not settings.CROP_HEALTH_MODEL_ROOT:
            return {**base, "status": "provider_unavailable", "error": "The crop model registry bundle is not configured."}
        if str(ML_ROOT) not in sys.path:
            sys.path.insert(0, str(ML_ROOT))
        try:
            from inference.crop_model_registry import run_registry_inference
        except ImportError as exc:
            return {**base, "status": "provider_unavailable", "error": f"Local ML runtime is unavailable: {exc}"}
        registry_path = Path(settings.CROP_HEALTH_MODEL_REGISTRY_PATH).expanduser()
        model_root = Path(settings.CROP_HEALTH_MODEL_ROOT).expanduser()
        if not registry_path.is_absolute():
            registry_path = REPO_ROOT / registry_path
        if not model_root.is_absolute():
            model_root = REPO_ROOT / model_root
        selected = {item.strip() for item in settings.CROP_HEALTH_MODEL_IDS.split(",") if item.strip()}
        return run_registry_inference(
            image_path, confirmed_crop, registry_path, model_root,
            selected_model_ids=selected or None, max_count=max(1, settings.CROP_HEALTH_MODEL_MAX_COUNT),
        )
    if provider not in {"local_hierarchical_demo", "local_hierarchical"}:
        return {**base, "status": "provider_unavailable", "error": "Local crop-health inference is not enabled."}
    if not crop:
        return {**base, "status": "needs_crop_confirmation", "error": "Confirm the crop before a crop-specific disease model can run."}
    if not router or not router.exists():
        return {**base, "status": "provider_unavailable", "error": "The approved crop-router checkpoint is unavailable."}
    if crop not in specialists or not specialists[crop].exists():
        return {**base, "status": "unsupported_crop", "error": f"No approved specialist is configured for {crop}."}
    try:
        outcome = _runtime()(image_path, router, specialists, confirmed_crop=crop)
    except (ImportError, ModuleNotFoundError) as exc:
        return {**base, "status": "provider_unavailable", "error": f"Local ML runtime is unavailable: {exc}"}
    except Exception as exc:  # Input/checkpoint failures must not become advice.
        return {**base, "status": "needs_expert_review", "error": f"The image could not be safely evaluated: {exc}"}

    candidates = outcome.get("disease_candidates", [])
    top = candidates[0] if candidates else None
    if outcome.get("status") != "completed" or not top:
        return {**base, "status": "needs_expert_review", "error": outcome.get("reason") or "No safe disease result was produced.", "router_candidates": outcome.get("router_candidates", [])}
    confidence = float(top["score"])
    if confidence < settings.CROP_HEALTH_MIN_DISEASE_SCORE:
        return {**base, "status": "needs_expert_review", "error": "The disease score is too uncertain for a prototype result.", "router_candidates": outcome.get("router_candidates", []), "disease_candidates": candidates}
    return {**base, "status": "completed", "label": str(top["label"]), "confidence": confidence,
            "router_candidates": outcome.get("router_candidates", []), "disease_candidates": candidates,
            "specialist_model": outcome.get("specialist_model")}


async def diagnose_image_async(image_path: Path, confirmed_crop: str | None = None) -> dict[str, Any]:
    """Use non-blocking hosted inference and keep local CPU work off-loop."""
    if settings.DIAGNOSIS_PROVIDER == "kindwise_crop_health":
        from app.services.kindwise_crop_health import assess_image
        return await assess_image(image_path, confirmed_crop)
    return await asyncio.to_thread(diagnose_image, image_path, confirmed_crop)
