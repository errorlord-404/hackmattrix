from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RawPrediction:
    label: str
    confidence: float


class DiseaseModelAdapter(ABC):
    """Adapters must never fetch a model during construction or prediction."""
    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def predict(self, image: Any, top_k: int = 3) -> list[RawPrediction]: ...

    def unload(self) -> None:
        return None
