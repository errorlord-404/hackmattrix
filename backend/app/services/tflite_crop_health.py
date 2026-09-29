"""Optional local TensorFlow Lite crop-health specialist adapter."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.core.config import settings


def _normalise_crop(value: str | None) -> str | None:
    crop = (value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return None if crop in {"", "unknown", "i_do_not_know", "none"} else crop


def _quality_issue(image_path: Path) -> str | None:
    """Return a transparent capture-quality reason without diagnosing pixels."""
    try:
        import numpy as np
        from PIL import Image
        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        if min(width, height) < 160:
            return "The photo is too small. Capture a closer, sharper leaf photo."
        pixels = np.asarray(image, dtype=np.float32)
        luminance = pixels.mean(axis=2)
        if float(luminance.mean()) < 28:
            return "The photo is too dark. Retake it in natural light."
        if float(luminance.mean()) > 235:
            return "The photo is overexposed. Avoid direct glare and retake it."
        if float(luminance.std()) < 10:
            return "The photo has too little visible detail. Retake it with the leaf in focus."
    except Exception:
        return "The photo could not be checked safely. Retake it as a clear JPG or PNG."
    return None


def _review_reason(candidates: list[dict[str, float | str]]) -> str | None:
    """Return an acceptance failure reason for transparent persistence/UI."""
    top = candidates[0] if candidates else None
    if not top or float(top["score"]) < settings.CROP_HEALTH_MIN_DISEASE_SCORE:
        return "The local model score is below the review threshold."
    second_score = float(candidates[1]["score"]) if len(candidates) > 1 else 0.0
    if float(top["score"]) - second_score < settings.CROP_HEALTH_MIN_DISEASE_MARGIN:
        return "The leading disease result is too close to another class. Retake the photo or request expert review."
    return None


def _crop_review_reason(candidates: list[dict[str, float | str]]) -> str | None:
    """Crop routing has its own, deliberately conservative acceptance gate."""
    top = candidates[0] if candidates else None
    if not top or float(top["score"]) < settings.CROP_HEALTH_MIN_CROP_SCORE:
        return "The crop-router score is too uncertain. Ask the farmer to identify the crop."
    second_score = float(candidates[1]["score"]) if len(candidates) > 1 else 0.0
    if float(top["score"]) - second_score < settings.CROP_HEALTH_MIN_CROP_MARGIN:
        return "The crop-router alternatives are too close. Ask the farmer to identify the crop."
    return None


def _tflite_candidates(image_path: Path, model_path: Path, labels_path: Path) -> list[dict[str, float | str]]:
    """Run an image classifier and normalize its top-k output for persistence."""
    import numpy as np
    import tensorflow as tf
    from PIL import Image

    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    if not isinstance(labels, list) or not labels or not all(isinstance(label, str) for label in labels):
        raise ValueError("TFLite labels must be a non-empty JSON list of strings")
    interpreter = tf.lite.Interpreter(model_path=str(model_path)); interpreter.allocate_tensors()
    input_info, output_info = interpreter.get_input_details()[0], interpreter.get_output_details()[0]
    _, height, width, _ = input_info["shape"]
    image = np.asarray(Image.open(image_path).convert("RGB").resize((width, height)), dtype=np.float32)[None, ...]
    scale, zero = input_info["quantization"]
    if input_info["dtype"] != np.float32:
        if not scale:
            raise ValueError("Quantized TFLite input has no scale")
        image = np.clip(np.round(image / scale + zero), 0, 255).astype(input_info["dtype"])
    interpreter.set_tensor(input_info["index"], image); interpreter.invoke()
    scores = interpreter.get_tensor(output_info["index"])[0].astype("float32")
    out_scale, out_zero = output_info["quantization"]
    if output_info["dtype"] != np.float32 and out_scale:
        scores = (scores - out_zero) * out_scale
    if len(scores) != len(labels):
        raise ValueError(f"TFLite output has {len(scores)} scores but labels contain {len(labels)} entries")
    order = np.argsort(scores)[::-1][:min(3, len(labels))]
    return [{"label": str(labels[int(index)]), "score": float(scores[int(index)])} for index in order]


def _router_available() -> tuple[Path, Path] | None:
    model = Path(settings.CROP_HEALTH_TFLITE_ROUTER_MODEL_PATH).expanduser()
    labels = Path(settings.CROP_HEALTH_TFLITE_ROUTER_LABELS_PATH).expanduser()
    return (model, labels) if model.is_file() and labels.is_file() else None


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _passed_gate(value: Any) -> bool:
    """Accept only explicit pass states in a versioned release manifest."""
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"passed", "approved"}
    return isinstance(value, dict) and _passed_gate(value.get("status"))


def _configured_model_identity() -> tuple[str, str]:
    """Describe the configured specialist from its operator-mounted manifest."""
    fallback = ("configured-tflite-crop-specialist", "unversioned")
    manifest_path = Path(settings.CROP_HEALTH_TFLITE_RELEASE_MANIFEST_PATH).expanduser()
    if not manifest_path.is_file():
        return fallback
    try:
        import yaml

        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    if not isinstance(manifest, dict):
        return fallback
    runtime = manifest.get("runtime")
    source_backbone = runtime.get("source_backbone") if isinstance(runtime, dict) else None
    release_id = manifest.get("release_id")
    model_id = str(source_backbone).strip() if source_backbone else fallback[0]
    model_version = str(release_id).strip() if release_id else fallback[1]
    return model_id, model_version


def _release_approval_reason(model_path: Path, labels_path: Path, crop: str) -> str | None:
    """Validate the manifest that authorizes a completed local result.

    The runtime binds its configured artifacts to immutable SHA-256 values and
    requires explicit independent-field and unknown/OOD gates.  This is still
    not a cryptographic signing system; deployment must mount the manifest from
    the reviewed release bundle, not let a farmer/client provide it.
    """
    manifest_path = Path(settings.CROP_HEALTH_TFLITE_RELEASE_MANIFEST_PATH).expanduser()
    if not manifest_path.is_file():
        return "No approved field/OOD release manifest is configured for this local model."
    try:
        import yaml

        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"The configured release manifest could not be read safely: {exc}"
    if not isinstance(manifest, dict):
        return "The configured release manifest is not a mapping."
    if manifest.get("status") != "approved_for_field_release":
        return "The configured model release is not approved for field deployment."
    if str(manifest.get("supported_crop", "")).strip().lower().replace(" ", "_") != crop:
        return "The approved release manifest does not cover the farmer-confirmed crop."
    artifact = manifest.get("artifact")
    labels = manifest.get("labels")
    if not isinstance(artifact, dict) or artifact.get("sha256") != _file_sha256(model_path):
        return "The configured model does not match the approved release artifact checksum."
    if not isinstance(labels, dict) or labels.get("sha256") != _file_sha256(labels_path):
        return "The configured labels do not match the approved release checksum."
    gates = manifest.get("release_gates")
    if not isinstance(gates, dict) or not _passed_gate(gates.get("independent_field_test")):
        return "The release manifest lacks a passed independent field-held-out evaluation gate."
    if not _passed_gate(gates.get("unknown_ood_test")):
        return "The release manifest lacks a passed unknown/OOD evaluation gate."
    if not _passed_gate(gates.get("agronomist_review")):
        return "The release manifest lacks a passed agronomist-review gate."
    return None


def run_tflite_crop_router(image_path: Path) -> dict[str, Any]:
    """Suggest a crop from an opt-in router; never silently select a specialist."""
    base: dict[str, Any] = {
        "provider": "local_tflite_demo", "crop": None,
        "model_id": "tfhub-mobilenetv3-small-crop-router", "model_version": "controlled-demo-unreleased",
        "inference_location": "local-server-tflite",
        "limitations": [
            "A crop-router result is a suggestion only; the farmer must confirm the crop before disease screening.",
            "This controlled-image prototype is not field validated and must not trigger farm action.",
        ],
    }
    quality_issue = _quality_issue(image_path)
    if quality_issue:
        return {**base, "status": "needs_expert_review", "error": quality_issue}
    artifacts = _router_available()
    if not artifacts:
        return {**base, "status": "needs_crop_confirmation", "error": "Confirm the crop before the local specialist can run."}
    try:
        candidates = _tflite_candidates(image_path, *artifacts)
    except (ImportError, ModuleNotFoundError) as exc:
        return {**base, "status": "provider_unavailable", "error": f"TensorFlow Lite runtime is unavailable: {exc}"}
    except Exception as exc:
        return {**base, "status": "needs_expert_review", "error": f"The crop router could not safely evaluate this image: {exc}"}
    review_reason = _crop_review_reason(candidates)
    suggested_crop = str(candidates[0]["label"]) if candidates and not review_reason else None
    return {**base, "status": "needs_crop_confirmation", "crop": suggested_crop,
            "crop_candidates": candidates, "error": review_reason or "Confirm or correct the suggested crop before disease screening."}


def run_tflite_specialist(image_path: Path, confirmed_crop: str | None) -> dict[str, Any]:
    """Run only after farmer crop confirmation; do not route arbitrary crops."""
    crop = _normalise_crop(confirmed_crop)
    model_id, model_version = _configured_model_identity()
    base: dict[str, Any] = {
        "provider": "local_tflite_demo", "crop": crop or None,
        "model_id": model_id, "model_version": model_version,
        "inference_location": "local-server-tflite",
        "limitations": [
            "This controlled-image prototype supports only the configured crop specialist.",
            "It has no approved unknown/OOD or farmer-phone field evaluation; labels are review candidates, not a completed diagnosis.",
            "It is not field validated and must not trigger pesticide, fertiliser, or irrigation action.",
        ],
    }
    if not crop:
        return run_tflite_crop_router(image_path)
    supported = settings.CROP_HEALTH_TFLITE_CROP.strip().lower().replace(" ", "_")
    if crop != supported:
        return {**base, "status": "unsupported_crop", "error": f"This local TFLite specialist supports only {supported}."}
    quality_issue = _quality_issue(image_path)
    if quality_issue:
        return {**base, "status": "needs_expert_review", "error": quality_issue}
    model_path, labels_path = Path(settings.CROP_HEALTH_TFLITE_MODEL_PATH).expanduser(), Path(settings.CROP_HEALTH_TFLITE_LABELS_PATH).expanduser()
    if not model_path.is_file() or not labels_path.is_file():
        return {**base, "status": "provider_unavailable", "error": "The configured local TFLite model or labels are unavailable."}
    try:
        candidates = _tflite_candidates(image_path, model_path, labels_path)
    except (ImportError, ModuleNotFoundError) as exc:
        return {**base, "status": "provider_unavailable", "error": f"TensorFlow Lite runtime is unavailable: {exc}"}
    except Exception as exc:
        return {**base, "status": "needs_expert_review", "error": f"The local model could not safely evaluate this image: {exc}"}
    review_reason = _review_reason(candidates)
    if review_reason:
        return {**base, "status": "needs_expert_review", "error": review_reason, "disease_candidates": candidates}
    release_reason = _release_approval_reason(model_path, labels_path, crop)
    if release_reason:
        return {
            **base,
            "status": "needs_expert_review",
            "error": f"{release_reason} Treat the ranked label as a review candidate.",
            "disease_candidates": candidates,
        }
    top = candidates[0]
    return {**base, "status": "completed", "label": top["label"], "confidence": top["score"], "disease_candidates": candidates}
