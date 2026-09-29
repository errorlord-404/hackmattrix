from pathlib import Path

from PIL import Image

from models.crop_disease.adapters.onnx_classifier import OnnxImageClassifier


def test_real_candidate_onnx_adapter_runs_locally():
    root = Path(__file__).resolve().parents[2] / "candidates" / "mesabo-agri-plant-disease-resnet50-61aa6c3"
    adapter = OnnxImageClassifier(root, device="cpu")
    predictions = adapter.predict(Image.new("RGB", (300, 220), color=(80, 120, 40)), top_k=3)
    assert len(predictions) == 3
    assert all(0 <= item.confidence <= 1 for item in predictions)
    assert adapter.provider == "CPUExecutionProvider"
