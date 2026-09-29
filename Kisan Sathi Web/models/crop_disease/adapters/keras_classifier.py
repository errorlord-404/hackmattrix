from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import DiseaseModelAdapter, RawPrediction


class KerasImageClassifier(DiseaseModelAdapter):
    def __init__(self, model_dir: Path, *, input_size: int = 256) -> None:
        self.model_dir, self.input_size = model_dir, input_size
        self.model: Any = None
        self.keras: Any = None
        self.labels: list[str] = []

    def load(self) -> None:
        if self.model is not None:
            return
        label_path = self.model_dir / "labels.json"
        if not label_path.is_file():
            raise RuntimeError("Keras model is not loadable: authoritative labels.json is missing")
        labels = json.loads(label_path.read_text(encoding="utf-8"))
        if not isinstance(labels, list) or not all(isinstance(item, str) for item in labels):
            raise RuntimeError("Keras model labels.json is invalid")
        artifacts = [*sorted(self.model_dir.glob("*.keras")), *sorted(self.model_dir.glob("*.h5"))]
        if not artifacts:
            raise RuntimeError("local Keras artifact is missing")
        try:
            import keras
        except ImportError:
            try:
                from tensorflow import keras
            except ImportError as exc:
                raise RuntimeError("Install optional TensorFlow/Keras dependencies to load this model") from exc
        load_errors: list[str] = []
        model = None
        for artifact in artifacts:
            try:
                model = keras.saving.load_model(artifact, compile=False)
                break
            except Exception as exc:  # legacy Keras formats can be version-specific
                load_errors.append(f"{artifact.name}: {exc}")
        if model is None:
            detail = "; ".join(load_errors[-2:])
            raise RuntimeError(f"no compatible local Keras artifact could be loaded: {detail}")
        shape = getattr(model, "input_shape", None)
        if isinstance(shape, tuple) and len(shape) == 4 and all(isinstance(value, int) for value in shape[1:3]):
            self.input_size = int(shape[1])
        self.model, self.keras, self.labels = model, keras, labels

    def predict(self, image: Any, top_k: int = 3) -> list[RawPrediction]:
        self.load()
        import numpy as np
        array = np.asarray(image.convert("RGB").resize((self.input_size, self.input_size)), dtype="float32") / 255.0
        scores = np.asarray(self.model.predict(np.expand_dims(array, 0), verbose=0)[0], dtype="float32")
        if len(scores) != len(self.labels):
            raise RuntimeError("model output count does not match authoritative labels")
        if not np.isclose(float(scores.sum()), 1.0, rtol=1e-3, atol=1e-3):
            scores = np.exp(scores - scores.max()); scores = scores / scores.sum()
        indexes = np.argsort(scores)[::-1][:max(1, top_k)]
        return [RawPrediction(self.labels[int(index)], float(scores[int(index)])) for index in indexes]

    def unload(self) -> None:
        self.model = None
        if self.keras is not None:
            self.keras.backend.clear_session()
