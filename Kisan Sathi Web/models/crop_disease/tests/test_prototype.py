from __future__ import annotations

from pathlib import Path

from models.crop_disease.prototype import build_prototype_status
from models.crop_disease.registry import CropDiseaseRegistry, default_registry_path


def test_profile_reports_current_verified_models_and_keeps_production_closed():
    registry = CropDiseaseRegistry.from_path(default_registry_path())
    profile = build_prototype_status(registry, Path(__file__).parents[1] / "downloaded")

    assert profile["status"] == "prototype_available"
    assert profile["model_count"] == 3
    assert profile["prototype_only"] is True
    assert profile["production_approved"] is False
    assert profile["activation_allowed"] is False
    assert {item["id"] for item in profile["supported_crops"]} >= {"maize", "potato", "tomato", "citrus", "grape", "soybean", "chilli"}
    assert all(model["loadable"] for model in profile["models"])


def test_prototype_onnx_profile_reports_candidate_without_production_flags():
    standalone_root = Path(__file__).resolve().parents[3]
    crop_root = standalone_root / "models" / "crop_disease"
    registry = CropDiseaseRegistry.from_path(crop_root / "registry.prototype.json")
    profile = build_prototype_status(registry, standalone_root / "models" / "candidates")

    assert profile["status"] == "prototype_available"
    assert profile["model_count"] == 1
    assert profile["models"][0]["framework"] == "onnxruntime"
    assert profile["prototype_only"] is True
    assert profile["production_approved"] is False
    assert profile["activation_allowed"] is False
