"""Lazy, framework-neutral crop-disease model registry.

The registry contains metadata and relative artifact paths only. Heavy model
runtimes are imported when an entry is actually selected, so the Codex desktop
application can start without TensorFlow, PyTorch, or ONNX Runtime installed.
The bundled research checkpoints intentionally produce ranked review signals,
never a production diagnosis or treatment recommendation.
"""

from __future__ import annotations

import json
import re
import tempfile
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


class RegistryError(ValueError):
    """Raised for invalid registry metadata or an unsafe artifact path."""


@dataclass(frozen=True)
class ModelEntry:
    model_id: str
    framework: str
    model_path: str
    labels_path: str | None
    input_size: int
    preprocessing: str
    crops: tuple[str, ...]
    source: str
    revision: str
    license: str
    research_only: bool
    enabled: bool = True


_CACHE: dict[tuple[str, str], Any] = {}
_ALIASES = {
    "maize": {"maize", "corn", "corn_maize"},
    "chilli": {"chilli", "chili", "pepper", "pepper_bell", "capsicum"},
    "citrus": {"citrus", "orange"},
}


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def normalise_crop(value: str | None) -> str | None:
    if not value:
        return None
    crop = _normalise(value)
    return None if crop in {"unknown", "none", "i_do_not_know"} else crop


def _crop_matches(label: str, crop: str) -> bool:
    label_crop = _normalise(label.split("___", 1)[0])
    requested = _normalise(crop)
    aliases = _ALIASES.get(requested, {requested})
    return label_crop in aliases or requested in label_crop or label_crop in requested


def _canonical_label(label: str) -> str:
    """Normalise source-specific class labels before comparing model votes."""
    return re.sub(r"^\s*\d+\s*:\s*", "", str(label)).strip()


def _photo_quality(image_path: Path) -> dict[str, Any]:
    """Reject obviously unusable photos before loading heavyweight classifiers.

    This is deliberately an image-quality screen, not an OOD detector. The
    research checkpoints do not ship validated OOD calibration artifacts.
    """
    try:
        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        if min(width, height) < 128:
            return {"status": "rejected", "reason": "The photo is too small. Take a closer, sharper leaf photo."}
        pixels = np.asarray(image, dtype=np.float32)
    except Exception:
        return {"status": "rejected", "reason": "The photo could not be read safely. Retake it as a clear JPEG, PNG, or WebP image."}
    brightness = float(pixels.mean())
    contrast = float(pixels.std())
    if brightness < 20:
        return {"status": "rejected", "reason": "The photo is too dark. Retake it in natural light."}
    if brightness > 235:
        return {"status": "rejected", "reason": "The photo is overexposed. Avoid glare and retake it."}
    if contrast < 12:
        return {"status": "rejected", "reason": "The photo has too little visible detail. Keep the affected leaf in focus."}
    return {"status": "accepted", "width": width, "height": height, "brightness": round(brightness, 1), "contrast": round(contrast, 1)}


def _safe_path(root: Path, relative: str) -> Path:
    root = root.expanduser().resolve()
    candidate = (root / relative).expanduser().resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise RegistryError(f"Model artifact escapes the configured model root: {relative}") from exc
    return candidate


class CropModelRegistry:
    def __init__(self, registry_path: Path, model_root: Path):
        self.registry_path = registry_path.expanduser().resolve()
        self.model_root = model_root.expanduser().resolve()
        try:
            payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RegistryError(f"Crop model registry is missing: {self.registry_path}") from exc
        except json.JSONDecodeError as exc:
            raise RegistryError(f"Crop model registry is invalid JSON: {self.registry_path}") from exc
        self.version = str(payload.get("version", "unversioned"))
        self.entries: tuple[ModelEntry, ...] = tuple(self._entry(item) for item in payload.get("models", []))

    @staticmethod
    def _entry(item: dict[str, Any]) -> ModelEntry:
        required = {"model_id", "framework", "model_path", "input_size", "preprocessing", "crops"}
        missing = sorted(required.difference(item))
        if missing:
            raise RegistryError(f"Model registry entry is missing: {', '.join(missing)}")
        return ModelEntry(
            model_id=str(item["model_id"]), framework=str(item["framework"]).lower(),
            model_path=str(item["model_path"]), labels_path=item.get("labels_path"),
            input_size=int(item["input_size"]), preprocessing=str(item["preprocessing"]),
            crops=tuple(str(c).lower() for c in item["crops"]), source=str(item.get("source", "unknown")),
            revision=str(item.get("revision", "unknown")), license=str(item.get("license", "unknown")),
            research_only=bool(item.get("research_only", True)), enabled=bool(item.get("enabled", True)),
        )

    def artifact_path(self, entry: ModelEntry) -> Path:
        return _safe_path(self.model_root, entry.model_path)

    def labels_path(self, entry: ModelEntry) -> Path | None:
        return _safe_path(self.model_root, entry.labels_path) if entry.labels_path else None

    def available(self, entry: ModelEntry) -> bool:
        model_path = self.artifact_path(entry)
        labels_path = self.labels_path(entry)
        return model_path.exists() and (labels_path is None or labels_path.exists())

    def for_crop(self, crop: str, selected_ids: set[str] | None = None, max_count: int = 4) -> list[ModelEntry]:
        crop = normalise_crop(crop) or ""
        return [
            entry for entry in self.entries
            if entry.enabled and (not selected_ids or entry.model_id in selected_ids)
            and (not entry.crops or crop in entry.crops) and self.available(entry)
        ][:max_count]

    def summary(self) -> dict[str, Any]:
        return {
            "registry_version": self.version,
            "research_only": True,
            "models": [
                {"model_id": e.model_id, "framework": e.framework, "crops": list(e.crops),
                 "available": self.available(e), "source": e.source, "revision": e.revision,
                 "license": e.license, "research_only": e.research_only}
                for e in self.entries
            ],
        }

    def labels(self, entry: ModelEntry) -> list[str]:
        path = self.labels_path(entry)
        if path and path.exists():
            payload = path.read_text(encoding="utf-8")
            try:
                data = json.loads(payload)
                if isinstance(data, list):
                    return [str(item) for item in data]
                if isinstance(data, dict):
                    data = data.get("labels") or data.get("id2label") or data
                    if isinstance(data, dict):
                        return [str(data[key]) for key in sorted(data, key=lambda k: int(k) if str(k).isdigit() else str(k))]
                    if isinstance(data, list):
                        return [str(item) for item in data]
            except json.JSONDecodeError:
                return [line.split(":", 1)[-1].strip() for line in payload.splitlines() if line.strip()]
        config = self.artifact_path(entry) / "config.json"
        if config.exists():
            data = json.loads(config.read_text(encoding="utf-8"))
            labels = data.get("id2label", {})
            return [str(labels[key]) for key in sorted(labels, key=lambda k: int(k) if str(k).isdigit() else str(k))]
        return []


def _softmax(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32).reshape(-1)
    values = values - np.max(values)
    result = np.exp(values)
    return result / max(float(result.sum()), 1e-12)


def _scores(values: Any) -> np.ndarray:
    raw = np.asarray(values, dtype=np.float32).reshape(-1)
    if len(raw) == 0:
        return raw
    if np.any(raw < 0) or not 0.98 <= float(raw.sum()) <= 1.02:
        return _softmax(raw)
    return raw / max(float(raw.sum()), 1e-12)


def _load(entry: ModelEntry, registry: CropModelRegistry) -> Any:
    key = (str(registry.artifact_path(entry)), entry.framework)
    if key in _CACHE:
        return _CACHE[key]
    path = registry.artifact_path(entry)
    if entry.framework in {"keras", "tensorflow", "tensorflow_keras", "keras_legacy"}:
        import tensorflow as tf
        keras_api = tf.keras
        if entry.framework == "keras_legacy":
            import tf_keras
            keras_api = tf_keras
        try:
            loaded = keras_api.models.load_model(path, compile=False)
        except (TypeError, ValueError) as exc:
            # Harimitra was serialized by an older Keras release that stored
            # ``batch_input_shape`` on Conv2D. Keras 3 rejects that legacy
            # keyword, so repair only the in-memory config in a temp archive;
            # the downloaded artifact remains unchanged and hashable.
            if path.suffix != ".keras":
                raise exc
            with zipfile.ZipFile(path) as source:
                config = json.loads(source.read("config.json"))

                def scrub(value: Any) -> None:
                    if isinstance(value, dict):
                        if value.get("class_name") == "InputLayer" and "batch_input_shape" in value:
                            value["batch_shape"] = value.pop("batch_input_shape")
                        elif value.get("class_name") != "InputLayer":
                            value.pop("batch_input_shape", None)
                            value.pop("batch_shape", None)
                        for child in value.values():
                            scrub(child)
                    elif isinstance(value, list):
                        for child in value:
                            scrub(child)

                scrub(config)
                temporary = tempfile.NamedTemporaryFile(suffix=".keras", delete=False)
                temporary.close()
                try:
                    with zipfile.ZipFile(temporary.name, "w") as target:
                        for info in source.infolist():
                            content = json.dumps(config).encode() if info.filename == "config.json" else source.read(info.filename)
                            target.writestr(info, content)
                    loaded = keras_api.models.load_model(temporary.name, compile=False)
                finally:
                    Path(temporary.name).unlink(missing_ok=True)
    elif entry.framework in {"transformers", "pytorch", "torch"}:
        from transformers import AutoImageProcessor, AutoModelForImageClassification
        loaded = (AutoImageProcessor.from_pretrained(path, local_files_only=True),
                  AutoModelForImageClassification.from_pretrained(path, local_files_only=True))
    elif entry.framework in {"onnx", "onnxruntime"}:
        import onnxruntime as ort
        loaded = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    else:
        raise RegistryError(f"Unsupported model framework: {entry.framework}")
    _CACHE[key] = loaded
    return loaded


def _image_array(image_path: Path, entry: ModelEntry) -> np.ndarray:
    image = Image.open(image_path).convert("RGB").resize((entry.input_size, entry.input_size))
    array = np.asarray(image, dtype=np.float32)
    if entry.preprocessing == "efficientnet":
        array = array / 127.5 - 1.0
    elif entry.preprocessing == "imagenet":
        array = array / 255.0
        array = (array - np.asarray([0.485, 0.456, 0.406])) / np.asarray([0.229, 0.224, 0.225])
    return array


def _predict(image_path: Path, entry: ModelEntry, registry: CropModelRegistry, crop: str) -> list[dict[str, Any]]:
    labels = registry.labels(entry)
    loaded = _load(entry, registry)
    if entry.framework in {"keras", "tensorflow", "tensorflow_keras", "keras_legacy"}:
        values = loaded.predict(np.expand_dims(_image_array(image_path, entry), 0), verbose=0)[0]
    elif entry.framework in {"transformers", "pytorch", "torch"}:
        import torch
        processor, model = loaded
        inputs = processor(images=Image.open(image_path).convert("RGB"), return_tensors="pt")
        with torch.no_grad():
            values = model(**inputs).logits.detach().cpu().numpy()[0]
    else:
        session = loaded
        input_meta = session.get_inputs()[0]
        array = _image_array(image_path, entry)
        if len(input_meta.shape) == 4 and input_meta.shape[1] == 3:
            array = np.transpose(array, (2, 0, 1))
        values = session.run(None, {input_meta.name: np.expand_dims(array, 0).astype(np.float32)})[0][0]
    scores = _scores(values)
    matching = [index for index, label in enumerate(labels) if _crop_matches(label, crop)]
    indices = matching if matching else list(range(len(scores)))
    ranked = sorted(indices, key=lambda index: float(scores[index]), reverse=True)[:5]
    return [{"label": labels[int(index)] if int(index) < len(labels) else f"class_{int(index)}",
             "score": round(float(scores[int(index)]), 6)} for index in ranked]


def run_registry_inference(
    image_path: Path,
    confirmed_crop: str | None,
    registry_path: Path,
    model_root: Path,
    selected_model_ids: set[str] | None = None,
    max_count: int = 4,
) -> dict[str, Any]:
    crop = normalise_crop(confirmed_crop)
    base = {"provider": "local_model_registry_demo", "crop": crop,
            "model_id": "crop-disease-research-ensemble", "model_version": "registry-v1",
            "inference_location": "local-server", "disease_candidates": [], "model_evidence": [],
            "ood_status": "unavailable",
            "limitations": [
                "These research checkpoints are not field-validated or agronomist-approved.",
                "PlantVillage-style labels may not represent Indian field conditions.",
                "No validated OOD detector is packaged with these research checkpoints.",
                "Use this ranked signal only for expert review; no pesticide or fertiliser action is generated.",
            ]}
    if not crop:
        return {**base, "status": "needs_crop_confirmation", "error": "Confirm the crop before running crop-specific models."}
    photo_quality = _photo_quality(image_path)
    if photo_quality["status"] != "accepted":
        return {**base, "status": "needs_expert_review", "error": photo_quality["reason"], "photo_quality": photo_quality}
    try:
        registry = CropModelRegistry(registry_path, model_root)
        entries = registry.for_crop(crop, selected_model_ids, max_count)
    except RegistryError as exc:
        return {**base, "status": "provider_unavailable", "error": str(exc)}
    if not entries:
        return {**base, "status": "unsupported_crop", "error": f"No installed model entry supports {crop}.", "registry": registry.summary()}
    aggregate: dict[str, dict[str, Any]] = {}
    for entry in entries:
        evidence: dict[str, Any] = {"model_id": entry.model_id, "framework": entry.framework,
                                     "source": entry.source, "revision": entry.revision,
                                     "research_only": entry.research_only}
        try:
            predictions = _predict(image_path, entry, registry, crop)
            evidence.update({"status": "ok", "candidates": predictions})
            for prediction in predictions:
                label = _canonical_label(str(prediction["label"]))
                item = aggregate.setdefault(label, {"label": label, "scores": [], "models": set()})
                item["scores"].append(float(prediction["score"]))
                item["models"].add(entry.model_id)
        except Exception as exc:
            evidence.update({"status": "unavailable", "error": str(exc)[:240]})
        base["model_evidence"].append(evidence)
    ranked = sorted(({
        "label": item["label"],
        "score": round(sum(item["scores"]) / len(item["scores"]), 6),
        "model_count": len(item["models"]),
        "models": sorted(item["models"]),
    } for item in aggregate.values()), key=lambda item: (item["score"], item["model_count"]), reverse=True)[:5]
    usable = [item for item in base["model_evidence"] if item["status"] == "ok"]
    if not usable or not ranked:
        return {**base, "status": "needs_expert_review", "error": "Installed research models could not produce a ranked signal.", "photo_quality": photo_quality}
    top = ranked[0]
    top_votes: dict[str, list[str]] = {}
    for evidence in usable:
        candidates = evidence.get("candidates", [])
        if candidates:
            top_votes.setdefault(_canonical_label(str(candidates[0]["label"])), []).append(evidence["model_id"])
    voted_label, voted_models = max(top_votes.items(), key=lambda item: (len(item[1]), item[0]))
    agreement_count = len(voted_models)
    agreement_status = "unanimous" if agreement_count == len(usable) else "partial" if agreement_count > 1 else "disagreed"
    return {**base, "status": "needs_expert_review", "error": "Research-model output requires agronomist review.",
            "label": top["label"], "confidence": top["score"], "disease_candidates": ranked,
            "photo_quality": photo_quality,
            "model_agreement": {"status": agreement_status, "top_label": voted_label,
                                "supporting_models": sorted(voted_models), "support_fraction": round(agreement_count / len(usable), 2)},
            "models_used": [item["model_id"] for item in usable],
            "models_unavailable": [item["model_id"] for item in base["model_evidence"] if item["status"] != "ok"]}
