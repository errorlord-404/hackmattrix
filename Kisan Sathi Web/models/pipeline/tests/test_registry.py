from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT))

from model_pipeline.contracts import PipelineError
from model_pipeline.registry import ModelRegistry


def test_registry_is_framework_neutral_and_complete() -> None:
    before = set(sys.modules)
    module = importlib.reload(sys.modules["model_pipeline.registry"])
    after = set(sys.modules)
    assert not (
        {"torch", "torchvision", "tensorflow", "tensorflow_hub", "onnx", "onnxruntime"}
        & (after - before)
    )

    report = module.ModelRegistry().report()
    assert report["status"] == "templates_only"
    assert report["activation_allowed"] is False
    assert report["recipe_count"] == 16
    assert report["crop_count"] == 15
    assert {"torchvision", "keras", "tensorflow_hub", "onnx", "tflite"} <= set(report["frameworks"])


def test_registry_cli_does_not_import_ml_frameworks() -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(PIPELINE_ROOT)
    script = (
        "import sys; from model_pipeline.cli import main; "
        "code = main(['registry-list']); "
        "forbidden = {'torch', 'torchvision', 'tensorflow', 'tensorflow_hub', 'onnx', 'onnxruntime'}; "
        "assert not (forbidden & set(sys.modules)); "
        "raise SystemExit(code)"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == 0, result.stderr
    assert "torchvision-mobilenet-v3-small" in result.stdout


def test_backbones_have_immutable_sources_and_license_metadata() -> None:
    backbones = ModelRegistry().backbones()
    assert {item["framework"] for item in backbones} >= {
        "torchvision", "keras", "tensorflow_hub", "onnx", "tflite"
    }
    assert {item["provider"] for item in backbones} == {
        "torchvision", "keras_applications", "tensorflow_hub", "import_onnx", "import_tflite"
    }
    for item in backbones:
        assert item["status"] == "template"
        assert item["source"]["immutable_id"]
        assert item["source"]["revision"]
        assert set(item["license"]) == {
            "name", "identifier", "url", "applies_to", "redistribution_review", "notes"
        }
        assert item["license"]["redistribution_review"] == "required"


def test_doctor_fails_clearly_for_required_missing_backend(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from model_pipeline import cli

    real_find_spec = cli.importlib.util.find_spec
    monkeypatch.setattr(
        cli.importlib.util,
        "find_spec",
        lambda name: None if name in {"onnx", "onnxruntime"} else real_find_spec(name),
    )
    assert cli.main(["doctor", "--require", "onnx"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "missing_dependencies"
    assert report["missing_required_optional"] == ["onnx"]


def test_registry_rejects_duplicate_backbone(tmp_path: Path) -> None:
    for name in ("backbones.schema.json", "recipes.schema.json"):
        (tmp_path / name).write_text((PIPELINE_ROOT / name).read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "top15.json").write_text(
        (PIPELINE_ROOT / "recipes" / "top15.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    document = json.loads((PIPELINE_ROOT / "backbones.json").read_text(encoding="utf-8"))
    document["backbones"].append(document["backbones"][0])
    (tmp_path / "backbones.json").write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(PipelineError, match="unique"):
        ModelRegistry(tmp_path).backbones()
