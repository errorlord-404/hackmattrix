from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT))

from model_pipeline.contracts import PipelineError  # noqa: E402
from model_pipeline.evaluation import metric_delta  # noqa: E402
from model_pipeline import quantization  # noqa: E402


def _fake_runtime(calls: list[tuple[str, object]]):
    quant_format = SimpleNamespace(QDQ="QDQ")
    quant_type = SimpleNamespace(QInt8="QInt8")

    def dynamic(source: str, destination: str, **kwargs: object) -> None:
        calls.append(("dynamic", kwargs))
        Path(destination).write_bytes(b"dynamic-int8")

    def static(source: str, destination: str, reader: object, **kwargs: object) -> None:
        calls.append(("static", {"reader": reader, **kwargs}))
        Path(destination).write_bytes(b"static-int8")

    return quant_format, quant_type, dynamic, static


def test_static_int8_requires_representative_calibration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "model.onnx"
    source.write_bytes(b"trained-model")
    monkeypatch.setattr(quantization, "_require_onnx_runtime", lambda: _fake_runtime([]))

    with pytest.raises(PipelineError, match="representative calibration data"):
        quantization.quantize_onnx(source, tmp_path / "quantized.onnx")


def test_static_int8_is_release_default_and_dynamic_is_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "model.onnx"
    source.write_bytes(b"trained-model")
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(quantization, "_require_onnx_runtime", lambda: _fake_runtime(calls))
    reader = quantization.ArrayCalibrationReader("input", [[1.0]])

    static = quantization.quantize_onnx(
        source,
        tmp_path / "static.onnx",
        calibration_reader=reader,
    )
    dynamic = quantization.quantize_onnx(
        source,
        tmp_path / "dynamic.onnx",
        mode="dynamic-int8",
    )

    assert static["mode"] == "static-int8"
    assert static["release_default"] is True
    assert dynamic["release_default"] is False
    assert calls[0][0] == "static"
    assert calls[0][1]["reader"] is reader
    assert calls[0][1]["quant_format"] == "QDQ"
    assert calls[0][1]["activation_type"] == "QInt8"
    assert metric_delta({"macro_f1": 0.8}, {"macro_f1": 0.79}) == pytest.approx(
        {"macro_f1": -0.01}
    )
