from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import DiseaseModelAdapter, RawPrediction


class OnnxImageClassifier(DiseaseModelAdapter):
    """Local-only ONNX image classifier for server parity with browser ORT."""

    def __init__(self, model_dir: Path, *, device: str = "auto") -> None:
        self.model_dir, self.device = Path(model_dir), device
        self.session: Any = None
        self.labels: list[str] = []
        self.input_name = "input"
        self.input_size = (224, 224)
        self.mean = (0.485, 0.456, 0.406)
        self.std = (0.229, 0.224, 0.225)
        self.provider = "CPUExecutionProvider"

    def load(self) -> None:
        if self.session is not None:
            return
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("Install models/pipeline/requirements-onnx.txt to load ONNX models") from exc
        labels_path = self.model_dir / "labels.json"
        if not labels_path.is_file():
            raise RuntimeError("ONNX model labels.json is missing")
        labels_document = json.loads(labels_path.read_text(encoding="utf-8"))
        labels = labels_document.get("labels") if isinstance(labels_document, dict) else labels_document
        if not isinstance(labels, list) or not labels or not all(isinstance(item, str) for item in labels):
            raise RuntimeError("ONNX labels.json must contain an ordered string label list")
        preprocess_path = self.model_dir / "preprocess.json"
        if preprocess_path.is_file():
            preprocess = json.loads(preprocess_path.read_text(encoding="utf-8"))
            size = preprocess.get("input_size", [224, 224])
            if isinstance(size, list) and len(size) == 2 and all(isinstance(value, int) for value in size):
                self.input_size = (size[0], size[1])
            normalization = preprocess.get("normalization", {})
            if isinstance(normalization, dict):
                mean, std = normalization.get("mean"), normalization.get("std")
                if isinstance(mean, list) and len(mean) == 3 and isinstance(std, list) and len(std) == 3:
                    self.mean, self.std = tuple(float(value) for value in mean), tuple(float(value) for value in std)
        artifact = next(iter(sorted(self.model_dir.glob("model.onnx"))), None)
        artifact = artifact or next(iter(sorted(self.model_dir.glob("model-int8.onnx"))), None)
        artifact = artifact or next(iter(sorted(self.model_dir.glob("model-fp32.onnx"))), None)
        artifact = artifact or next((item for item in sorted(self.model_dir.glob("*.onnx")) if "dynamic" not in item.name.casefold()), None)
        if artifact is None:
            raise RuntimeError("ONNX model artifact is missing")
        available = ort.get_available_providers()
        providers = ["CPUExecutionProvider"]
        if self.device in {"auto", "cuda"} and "CUDAExecutionProvider" in available:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        self.session = ort.InferenceSession(str(artifact), providers=providers)
        self.provider = self.session.get_providers()[0]
        self.labels = labels
        self.input_name = self.session.get_inputs()[0].name

    def _tensor(self, image: Any) -> Any:
        import numpy as np

        rgb = image.convert("RGB")
        width, height = rgb.size
        target_width, target_height = self.input_size
        scale = max(target_width / width, target_height / height)
        resized = rgb.resize((max(target_width, round(width * scale)), max(target_height, round(height * scale))))
        left = (resized.width - target_width) // 2
        top = (resized.height - target_height) // 2
        cropped = resized.crop((left, top, left + target_width, top + target_height))
        values = np.asarray(cropped, dtype=np.float32) / 255.0
        values = (values - np.asarray(self.mean, dtype=np.float32)) / np.asarray(self.std, dtype=np.float32)
        return np.transpose(values, (2, 0, 1))[None, ...]

    def predict(self, image: Any, top_k: int = 3) -> list[RawPrediction]:
        self.load()
        import numpy as np

        logits = np.asarray(self.session.run(None, {self.input_name: self._tensor(image)})[0][0], dtype=np.float32)
        if logits.shape[0] != len(self.labels):
            raise RuntimeError("ONNX output count does not match authoritative labels")
        probabilities = np.exp(logits - logits.max())
        probabilities = probabilities / probabilities.sum()
        indexes = np.argsort(probabilities)[::-1][:max(1, top_k)]
        return [RawPrediction(self.labels[int(index)], float(probabilities[int(index)])) for index in indexes]

    def unload(self) -> None:
        self.session = None
