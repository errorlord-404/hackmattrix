import hashlib
import json
from pathlib import Path

from PIL import Image

from model_pipeline.quantization import ImageCalibrationReader


def test_image_calibration_reader_uses_only_hashed_calibration_records(tmp_path: Path):
    image_path = tmp_path / "leaf.png"
    Image.new("RGB", (16, 12), color=(20, 80, 40)).save(image_path)
    digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
    manifest = {"purpose": "calibration", "records": [{"path": "leaf.png", "sha256": digest, "split": "calibration"}]}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    reader = ImageCalibrationReader(manifest_path, image_size=(8, 8))
    tensor = reader.get_next()["input"]
    assert tensor.shape == (1, 3, 8, 8)
    assert reader.get_next() is None
