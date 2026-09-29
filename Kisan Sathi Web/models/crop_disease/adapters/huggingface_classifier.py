from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import DiseaseModelAdapter, RawPrediction


class HuggingFaceImageClassifier(DiseaseModelAdapter):
    def __init__(self, model_dir: Path, *, device: str = "auto") -> None:
        self.model_dir, self.device = model_dir, device
        self.model: Any = None
        self.processor: Any = None
        self.torch: Any = None

    def load(self) -> None:
        if self.model is not None:
            return
        if not (self.model_dir / "config.json").is_file():
            raise RuntimeError("local Hugging Face model config is missing")
        try:
            import torch
            from transformers import AutoImageProcessor, AutoModelForImageClassification
        except ImportError as exc:
            raise RuntimeError("Install the optional crop-disease PyTorch dependencies to load this model") from exc
        target = "cuda" if self.device == "auto" and torch.cuda.is_available() else ("cpu" if self.device == "auto" else self.device)
        self.processor = AutoImageProcessor.from_pretrained(str(self.model_dir), local_files_only=True)
        self.model = AutoModelForImageClassification.from_pretrained(str(self.model_dir), local_files_only=True).to(target).eval()
        self.device, self.torch = target, torch

    def predict(self, image: Any, top_k: int = 3) -> list[RawPrediction]:
        self.load()
        assert self.processor is not None and self.model is not None and self.torch is not None
        batch = self.processor(images=image, return_tensors="pt")
        batch = {key: value.to(self.device) for key, value in batch.items()}
        with self.torch.inference_mode():
            probabilities = self.torch.softmax(self.model(**batch).logits[0], dim=-1)
        count = min(max(1, top_k), int(probabilities.shape[0]))
        values, indexes = self.torch.topk(probabilities, count)
        labels = self.model.config.id2label
        return [RawPrediction(str(labels.get(int(index), labels.get(str(int(index)), "unknown"))), float(value)) for value, index in zip(values.tolist(), indexes.tolist())]

    def unload(self) -> None:
        self.model = self.processor = None
        if self.torch is not None and self.device == "cuda":
            self.torch.cuda.empty_cache()
