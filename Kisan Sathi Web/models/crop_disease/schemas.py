"""Pydantic contracts used by router, service and FastAPI adapter."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class TopCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    disease_id: str
    disease_name: str
    raw_model_label: str
    confidence: float = Field(ge=0, le=1)
    healthy: bool


class ModelMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    name: str
    architecture: str
    framework: str
    source: str
    training_domain: Literal["controlled", "field", "unknown"]
    revision: str | None = None
    device: str | None = None


class RoutingMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    requested_crop: str | None
    normalized_crop: str | None
    selected_specialist: str | None
    reason: str


class TimingMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    model_load_ms: float = 0
    preprocess_ms: float = 0
    inference_ms: float = 0
    postprocess_ms: float = 0
    total_ms: float = 0


class DiseaseInferenceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["healthy", "disease", "uncertain", "unsupported_crop", "model_unavailable", "inference_error", "crop_required", "ensemble_unavailable"]
    crop: str | None = None
    model_available: bool
    prediction: TopCandidate | None = None
    top_k: list[TopCandidate] = Field(default_factory=list)
    model: ModelMetadata | None = None
    routing: RoutingMetadata
    warnings: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    timings: TimingMetadata = Field(default_factory=TimingMetadata)

