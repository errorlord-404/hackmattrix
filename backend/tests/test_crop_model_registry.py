import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ml"))
from inference.crop_model_registry import CropModelRegistry, RegistryError, run_registry_inference


def test_parent_registry_declares_all_available_model_adapters():
    root = Path(__file__).resolve().parents[2]
    registry = CropModelRegistry(root / "ml/model_registry.json", root / "ml/private-artifacts/crop-disease")
    assert {entry.model_id for entry in registry.entries} == {
        "harimitra", "mesabo_resnet50", "plantvillage_efficientnet", "mesabo_resnet50_onnx",
    }
    assert {entry.framework for entry in registry.entries} == {"keras_legacy", "transformers", "keras", "onnx"}
    assert all(entry.research_only for entry in registry.entries)


def test_registry_rejects_artifact_escape(tmp_path):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps({"models": [{
        "model_id": "escape", "framework": "onnx", "model_path": "../outside.onnx",
        "input_size": 224, "preprocessing": "imagenet", "crops": ["tomato"],
    }]}), encoding="utf-8")
    registry = CropModelRegistry(registry_path, tmp_path / "models")
    with pytest.raises(RegistryError):
        registry.artifact_path(registry.entries[0])


def test_registry_runner_requires_farmer_crop_confirmation(tmp_path):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps({"models": []}), encoding="utf-8")
    response = run_registry_inference(
        tmp_path / "leaf.jpg", None, registry_path, tmp_path / "models",
    )
    assert response["status"] == "needs_crop_confirmation"
    assert response["model_evidence"] == []


def test_registry_runner_preserves_review_only_status(monkeypatch, tmp_path):
    image = tmp_path / "leaf.jpg"
    image.write_bytes(b"fixture")
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps({"models": [{
        "model_id": "fake", "framework": "onnx", "model_path": "fake.onnx",
        "input_size": 224, "preprocessing": "imagenet", "crops": ["tomato"],
    }]}), encoding="utf-8")
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "fake.onnx").write_bytes(b"fixture")

    import inference.crop_model_registry as module
    monkeypatch.setattr(module, "_photo_quality", lambda *_args: {"status": "accepted"})
    monkeypatch.setattr(module, "_predict", lambda *_args: [{"label": "Tomato___healthy", "score": 0.91}])
    response = run_registry_inference(image, "tomato", registry_path, tmp_path / "models")
    assert response["status"] == "needs_expert_review"
    assert response["model_evidence"][0]["status"] == "ok"
    assert response["disease_candidates"][0]["label"] == "Tomato___healthy"
    assert response["model_agreement"] == {
        "status": "unanimous", "top_label": "Tomato___healthy", "supporting_models": ["fake"], "support_fraction": 1.0,
    }


def test_registry_runner_rejects_a_photo_that_cannot_support_model_review(tmp_path):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps({"models": []}), encoding="utf-8")
    image = tmp_path / "tiny.jpg"
    image.write_bytes(b"not-an-image")

    response = run_registry_inference(image, "tomato", registry_path, tmp_path / "models")

    assert response["status"] == "needs_expert_review"
    assert response["photo_quality"]["status"] == "rejected"
    assert response["ood_status"] == "unavailable"
    assert response["model_evidence"] == []


def test_registry_runner_canonicalises_labels_and_reports_model_disagreement(monkeypatch, tmp_path):
    image = tmp_path / "leaf.jpg"
    image.write_bytes(b"fixture")
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps({"models": [
        {"model_id": "first", "framework": "onnx", "model_path": "first.onnx", "input_size": 224, "preprocessing": "imagenet", "crops": ["tomato"]},
        {"model_id": "second", "framework": "onnx", "model_path": "second.onnx", "input_size": 224, "preprocessing": "imagenet", "crops": ["tomato"]},
    ]}), encoding="utf-8")
    model_root = tmp_path / "models"
    model_root.mkdir()
    (model_root / "first.onnx").write_bytes(b"fixture")
    (model_root / "second.onnx").write_bytes(b"fixture")

    import inference.crop_model_registry as module
    monkeypatch.setattr(module, "_photo_quality", lambda *_args: {"status": "accepted"})
    monkeypatch.setattr(module, "_predict", lambda _image, entry, *_args: [
        {"label": "30: Tomato___Late_blight" if entry.model_id == "first" else "Tomato___Early_blight", "score": 0.9},
    ])

    response = run_registry_inference(image, "tomato", registry_path, model_root)

    assert {candidate["label"] for candidate in response["disease_candidates"]} == {"Tomato___Late_blight", "Tomato___Early_blight"}
    assert response["model_agreement"]["status"] == "disagreed"
    assert response["model_agreement"]["support_fraction"] == 0.5
