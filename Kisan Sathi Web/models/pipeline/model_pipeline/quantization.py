"""Optional ONNX quantization adapters.

Static calibrated INT8 is the default for CNN release candidates. Dynamic
quantization is retained for experimentation and cannot by itself satisfy the
release recipe.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .contracts import PipelineError


class ArrayCalibrationReader:
    def __init__(self, input_name: str, tensors: Iterable[Any]):
        self.input_name = input_name
        self._iterator = iter(tensors)

    def get_next(self) -> dict[str, Any] | None:
        try:
            value = next(self._iterator)
        except StopIteration:
            return None
        return {self.input_name: value}


class ImageCalibrationReader:
    """Deterministic calibration reader backed by an explicit image manifest.

    Only records explicitly marked ``calibration`` are accepted. Every file is
    checksum-checked before it can enter the quantizer; directory discovery and
    random sampling are intentionally unsupported.
    """

    def __init__(self, manifest_path: Path, input_name: str = "input", *, image_size: tuple[int, int] = (224, 224), limit: int | None = None, mean: tuple[float, float, float] = (0.485, 0.456, 0.406), std: tuple[float, float, float] = (0.229, 0.224, 0.225)) -> None:
        import hashlib
        import json

        if len(image_size) != 2 or any(value <= 0 for value in image_size):
            raise PipelineError("image_size must contain two positive values")
        document = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        if document.get("purpose") != "calibration":
            raise PipelineError("static quantization requires a manifest with purpose=calibration")
        records = document.get("records")
        if not isinstance(records, list) or not records:
            raise PipelineError("calibration manifest records must be non-empty")
        root = Path(manifest_path).parent / document.get("root", ".")
        selected = [record for record in records if record.get("split") == "calibration"]
        if limit is not None:
            if not isinstance(limit, int) or limit <= 0:
                raise PipelineError("calibration limit must be positive")
            selected = selected[:limit]
        if not selected:
            raise PipelineError("calibration manifest has no calibration records")
        self.input_name = input_name
        self._tensors: list[Any] = []
        self._index = 0
        self._load_images(selected, root.resolve(), image_size, mean, std, hashlib)

    def _load_images(self, records: list[dict[str, Any]], root: Path, image_size: tuple[int, int], mean: tuple[float, float, float], std: tuple[float, float, float], hashlib: Any) -> None:
        import numpy as np
        from PIL import Image

        target_width, target_height = image_size
        for index, record in enumerate(records):
            relative = record.get("path")
            if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
                raise PipelineError(f"calibration record {index} has an unsafe path")
            path = (root / relative).resolve()
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise PipelineError(f"calibration record {index} escapes the manifest root") from exc
            if not path.is_file():
                raise PipelineError(f"calibration record {index} is missing: {relative}")
            expected = record.get("sha256")
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if not isinstance(expected, str) or actual != expected.casefold():
                raise PipelineError(f"calibration record {index} checksum does not match")
            with Image.open(path) as source:
                image = source.convert("RGB")
                width, height = image.size
                scale = max(target_width / width, target_height / height)
                resized = image.resize((max(target_width, round(width * scale)), max(target_height, round(height * scale))))
                left, top = (resized.width - target_width) // 2, (resized.height - target_height) // 2
                values = np.asarray(resized.crop((left, top, left + target_width, top + target_height)), dtype=np.float32) / 255.0
            values = (values - np.asarray(mean, dtype=np.float32)) / np.asarray(std, dtype=np.float32)
            self._tensors.append(np.transpose(values, (2, 0, 1))[None, ...])

    def get_next(self) -> dict[str, Any] | None:
        if self._index >= len(self._tensors):
            return None
        value = self._tensors[self._index]
        self._index += 1
        return {self.input_name: value}


def _require_onnx_runtime() -> tuple[Any, Any, Any, Any]:
    try:
        from onnxruntime.quantization import QuantFormat, QuantType, quantize_dynamic, quantize_static
    except ModuleNotFoundError as exc:
        raise PipelineError("ONNX quantization requires requirements-onnx.txt") from exc
    return QuantFormat, QuantType, quantize_dynamic, quantize_static


def quantize_onnx(
    source: Path,
    destination: Path,
    *,
    mode: str = "static-int8",
    calibration_reader: Any | None = None,
    per_channel: bool = True,
) -> dict[str, object]:
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if not source.is_file() or source.suffix.lower() != ".onnx":
        raise PipelineError("quantization source must be an existing ONNX file")
    if source == destination:
        raise PipelineError("quantization destination must differ from source")
    destination.parent.mkdir(parents=True, exist_ok=True)
    QuantFormat, QuantType, quantize_dynamic, quantize_static = _require_onnx_runtime()
    if mode == "static-int8":
        if calibration_reader is None:
            raise PipelineError("static INT8 quantization requires representative calibration data")
        quantize_static(
            str(source),
            str(destination),
            calibration_reader,
            quant_format=QuantFormat.QDQ,
            activation_type=QuantType.QInt8,
            weight_type=QuantType.QInt8,
            per_channel=per_channel,
        )
        release_default = True
    elif mode == "dynamic-int8":
        quantize_dynamic(
            str(source),
            str(destination),
            weight_type=QuantType.QInt8,
            per_channel=per_channel,
        )
        release_default = False
    else:
        raise PipelineError(f"unsupported ONNX quantization mode: {mode}")
    if not destination.is_file() or destination.stat().st_size == 0:
        raise PipelineError("quantizer did not produce an artifact")
    return {
        "mode": mode,
        "release_default": release_default,
        "artifact": str(destination),
        "size_bytes": destination.stat().st_size,
        "evaluation_required": True,
    }
