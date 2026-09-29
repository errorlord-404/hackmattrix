from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Callable

from .adapters import DiseaseModelAdapter, HuggingFaceImageClassifier, KerasImageClassifier, OnnxImageClassifier
from .cache import ModelCache
from .ontology import normalize_crop, normalize_disease_label
from .registry import CropDiseaseRegistry, ModelEntry, default_registry_path
from .schemas import DiseaseInferenceResult, ModelMetadata, RoutingMetadata, TimingMetadata, TopCandidate

CONTROLLED_WARNING = "This model was trained on controlled PlantVillage-style imagery and is not validated for Indian field conditions. Treat this result as decision support, not a diagnosis."


class CropDiseaseRouter:
    def __init__(self, *, registry: CropDiseaseRegistry | None = None, downloaded_root: Path | None = None, cache_size: int = 2, device: str = "auto", min_confidence: float = 0.60, allow_research_models: bool = True, adapter_factory: Callable[[ModelEntry, Path], DiseaseModelAdapter] | None = None) -> None:
        self.registry = registry or CropDiseaseRegistry.from_path(default_registry_path())
        self.downloaded_root = downloaded_root or Path(os.getenv("CROP_MODEL_DIR", Path(__file__).resolve().parent / "downloaded"))
        self.cache, self.device, self.min_confidence, self.allow_research_models = ModelCache[DiseaseModelAdapter](cache_size), device, min_confidence, allow_research_models
        self.adapter_factory = adapter_factory or self._build_adapter

    def _build_adapter(self, entry: ModelEntry, location: Path) -> DiseaseModelAdapter:
        if entry.framework == "transformers_pytorch":
            return HuggingFaceImageClassifier(location, device=self.device)
        if entry.framework == "keras":
            return KerasImageClassifier(location, input_size=entry.input_size)
        if entry.framework == "onnxruntime":
            return OnnxImageClassifier(location, device=self.device)
        raise RuntimeError(f"unsupported framework {entry.framework}")

    def _entry_dir(self, entry: ModelEntry) -> Path:
        return self.downloaded_root / entry.local_path

    def _installed(self, entry: ModelEntry) -> bool:
        return (self._entry_dir(entry) / "download-manifest.json").is_file()

    def predict(self, image: object, *, crop: str | None, preferred_model: str | None = None, top_k: int = 3, mode: str = "single") -> DiseaseInferenceResult:
        started = time.perf_counter()
        normalized = normalize_crop(crop)
        timing = lambda: TimingMetadata(total_ms=round((time.perf_counter() - started) * 1000, 2))
        route = lambda selected=None, reason="": RoutingMetadata(requested_crop=crop, normalized_crop=normalized, selected_specialist=selected, reason=reason)
        if not crop:
            return DiseaseInferenceResult(status="crop_required", model_available=False, routing=route(reason="crop_identifier_not_installed"), recommendation="Provide a crop name or install a separately approved crop identifier.", warnings=[CONTROLLED_WARNING], timings=timing())
        if not normalized:
            return DiseaseInferenceResult(status="unsupported_crop", crop=crop, model_available=False, routing=route(reason="unknown_crop"), recommendation="Choose a crop from the canonical crop catalog.", warnings=[CONTROLLED_WARNING], timings=timing())
        if not self.allow_research_models:
            return DiseaseInferenceResult(status="model_unavailable", crop=normalized, model_available=False, routing=route(reason="production_release_required"), recommendation="Install and approve a production model release before enabling crop-disease inference.", warnings=[CONTROLLED_WARNING], timings=timing())
        if mode == "ensemble":
            return DiseaseInferenceResult(status="ensemble_unavailable", crop=normalized, model_available=False, routing=route(reason="ensemble_not_calibrated"), recommendation="Use single-model mode until calibrated cross-model evaluation exists.", warnings=[CONTROLLED_WARNING], timings=timing())
        candidates = self.registry.candidates(normalized, executable_only=True)
        if preferred_model:
            candidates = [entry for entry in candidates if entry.id == preferred_model]
        if not candidates:
            return DiseaseInferenceResult(status="model_unavailable", crop=normalized, model_available=False, routing=route(reason="no_registered_specialist"), recommendation="Register and qualify a crop-specific model before enabling inference.", warnings=[CONTROLLED_WARNING], timings=timing())
        entry = candidates[0]
        location = self._entry_dir(entry)
        if not self._installed(entry):
            return DiseaseInferenceResult(status="model_unavailable", crop=normalized, model_available=False, routing=route(entry.id, "artifact_not_installed"), recommendation="Run the explicit downloader and verify its manifest before inference.", model=self._metadata(entry), warnings=[CONTROLLED_WARNING], timings=timing())
        try:
            adapter = self.cache.get_or_load(entry.id, lambda: self.adapter_factory(entry, location))
            predictions = adapter.predict(image, top_k=max(1, min(top_k, 10)))
        except Exception:
            return DiseaseInferenceResult(status="inference_error", crop=normalized, model_available=True, routing=route(entry.id, "adapter_failure"), recommendation="Inspect local model dependencies and its verified artifact manifest.", model=self._metadata(entry), warnings=[CONTROLLED_WARNING], timings=timing())
        top = [self._candidate(item.label, item.confidence, normalized) for item in predictions]
        best = top[0]
        status = "healthy" if best.healthy else "disease"
        if best.confidence < self.min_confidence:
            status = "uncertain"
        return DiseaseInferenceResult(status=status, crop=normalized, model_available=True, prediction=best, top_k=top, model=self._metadata(entry), routing=route(entry.id, "highest_priority_downloaded_specialist"), warnings=[CONTROLLED_WARNING], timings=timing())

    @staticmethod
    def _candidate(raw_label: str, confidence: float, crop: str) -> TopCandidate:
        label = normalize_disease_label(raw_label, crop)
        return TopCandidate(disease_id=label.disease_id, disease_name=label.disease_name, raw_model_label=raw_label, confidence=round(confidence, 6), healthy=label.healthy)

    @staticmethod
    def _metadata(entry: ModelEntry) -> ModelMetadata:
        return ModelMetadata(id=entry.id, name=entry.name, architecture=entry.architecture, framework=entry.framework, source=entry.source_url, training_domain=entry.training_domain if entry.training_domain in {"controlled", "field", "unknown"} else "unknown", revision=entry.revision)
