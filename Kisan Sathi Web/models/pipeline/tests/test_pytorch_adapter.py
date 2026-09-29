from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT))

from model_pipeline.adapters import pytorch as adapter  # noqa: E402


def _write_manifest(tmp_path: Path, records: object) -> Path:
    data_root = tmp_path / "images"
    data_root.mkdir()
    for name in ("train-a.jpg", "train-b.jpg", "valid.jpg", "test.jpg"):
        (data_root / name).write_bytes(b"not decoded by manifest tests")
    path = tmp_path / "dataset.json"
    path.write_text(
        json.dumps(
            {
                "root": "images",
                "class_names": ["healthy", "rust"],
                "records": records,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_module_import_does_not_import_optional_frameworks() -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(PIPELINE_ROOT)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import model_pipeline.adapters.pytorch; "
                "assert 'torch' not in sys.modules; assert 'torchvision' not in sys.modules"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == 0, result.stderr


def test_optional_dependency_failure_is_actionable(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(name: str) -> object:
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(adapter.importlib, "import_module", missing)
    with pytest.raises(adapter.OptionalDependencyError, match="requirements-pytorch.txt"):
        adapter.seed_everything(7)


def test_manifest_requires_explicit_non_overlapping_splits(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path,
        {
            "train": [
                {"path": "train-a.jpg", "label": "healthy", "farm_id": "farm-1"},
                {"path": "train-b.jpg", "label": 1},
            ],
            "validation": [{"path": "valid.jpg", "label": "rust"}],
            "test": [{"path": "test.jpg", "label": "healthy"}],
        },
    )

    manifest = adapter.load_dataset_manifest(manifest_path)

    assert manifest.class_names == ("healthy", "rust")
    assert tuple(manifest.records) == adapter.SPLITS
    assert manifest.records_for("train")[0].metadata == {"farm_id": "farm-1"}
    assert manifest.records_for("train")[1].label == "rust"


@pytest.mark.parametrize(
    "records, message",
    [
        (
            {
                "train": [{"path": "train-a.jpg", "label": "healthy"}],
                "validation": [{"path": "valid.jpg", "label": "rust"}],
            },
            "missing: test",
        ),
        (
            {
                "train": [{"path": "train-a.jpg", "label": "healthy"}],
                "validation": [{"path": "train-a.jpg", "label": "healthy"}],
                "test": [{"path": "test.jpg", "label": "rust"}],
            },
            "duplicates",
        ),
        (
            {
                "train": [{"path": "../outside.jpg", "label": "healthy"}],
                "validation": [{"path": "valid.jpg", "label": "rust"}],
                "test": [{"path": "test.jpg", "label": "rust"}],
            },
            "escapes",
        ),
    ],
)
def test_manifest_rejects_implicit_or_unsafe_membership(
    tmp_path: Path, records: object, message: str
) -> None:
    path = _write_manifest(tmp_path, records)
    with pytest.raises(adapter.DatasetManifestError, match=message):
        adapter.load_dataset_manifest(path)


class _FakeWeight:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeWeights:
    def __init__(self, *names: str) -> None:
        self.members = {name: _FakeWeight(name) for name in names}

    def __getitem__(self, name: str) -> _FakeWeight:
        if name not in self.members:
            raise KeyError(name)
        return self.members[name]

    def __iter__(self):
        return iter(self.members.values())


class _FakeLinear:
    def __init__(self, in_features: int, out_features: int = 1000) -> None:
        self.in_features = in_features
        self.out_features = out_features


class _FakeModel:
    def __init__(self, classifier_attribute: str) -> None:
        if classifier_attribute == "fc":
            self.fc = _FakeLinear(1024)
        else:
            self.classifier = [object(), _FakeLinear(1280)]


def test_supported_models_use_explicit_weight_enums_and_replace_heads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}
    model_namespace = SimpleNamespace()
    for name, definition in adapter.ARCHITECTURES.items():
        setattr(
            model_namespace,
            definition.weights_enum,
            _FakeWeights(definition.default_weight, "ANOTHER_WEIGHT"),
        )

        def factory(*, weights: object, _name: str = name, _definition=definition) -> _FakeModel:
            calls[_name] = weights
            return _FakeModel(_definition.classifier_attribute)

        setattr(model_namespace, definition.factory, factory)

    fake_torch = SimpleNamespace(nn=SimpleNamespace(Linear=_FakeLinear))
    fake_vision = SimpleNamespace(models=model_namespace)
    monkeypatch.setattr(adapter, "_frameworks", lambda: (fake_torch, fake_vision))

    for architecture, definition in adapter.ARCHITECTURES.items():
        model = adapter.create_model(
            architecture,
            7,
            weight=definition.default_weight,
        )
        selected = calls[architecture]
        assert isinstance(selected, _FakeWeight)
        assert selected.name == definition.default_weight
        classifier = model.fc if definition.classifier_attribute == "fc" else model.classifier[-1]
        assert classifier.out_features == 7
        assert model._kisan_sathi_architecture == architecture

    no_weight_model = adapter.create_model("mobilenet_v3_small", 2, weight=None)
    assert calls["mobilenet_v3_small"] is None
    assert no_weight_model.classifier[-1].out_features == 2


def test_class_weights_and_evaluation_metrics() -> None:
    records = [
        adapter.DatasetRecord(Path("a"), "healthy", 0, "train"),
        adapter.DatasetRecord(Path("b"), "rust", 1, "train"),
        adapter.DatasetRecord(Path("c"), "rust", 1, "train"),
    ]
    assert adapter.class_weights(records, ("healthy", "rust")) == (1.5, 0.75)

    metrics = adapter.classification_metrics(
        [0, 0, 1, 1, 2],
        [0, 1, 1, 2, 2],
        ("healthy", "rust", "blight"),
    )
    assert metrics["confusion_matrix"] == [[1, 1, 0], [0, 1, 1], [0, 0, 1]]
    assert metrics["per_class_recall"] == {
        "healthy": 0.5,
        "rust": 0.5,
        "blight": 1.0,
    }
    assert math.isclose(metrics["macro_f1"], 11 / 18)


class _Parameter:
    def __init__(self, size: int) -> None:
        self.requires_grad = True
        self.size = size

    def numel(self) -> int:
        return self.size


class _Classifier:
    def __init__(self, parameters: list[_Parameter]) -> None:
        self._parameters = parameters

    def parameters(self):
        return iter(self._parameters)


def test_fine_tuning_stages_freeze_then_unfreeze() -> None:
    backbone = _Parameter(10)
    head = _Parameter(3)
    model = SimpleNamespace(
        classifier=_Classifier([head]),
        parameters=lambda: iter([backbone, head]),
    )

    assert adapter.set_trainable_parameters(model, "classifier") == 3
    assert backbone.requires_grad is False
    assert head.requires_grad is True
    assert adapter.set_trainable_parameters(model, "all") == 13
    assert backbone.requires_grad is True


def test_checkpoint_saves_state_dict_and_separate_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved: list[object] = []
    state = {"classifier.weight": [1, 2, 3]}

    class FakeTorch:
        @staticmethod
        def save(value: object, path: Path) -> None:
            saved.append(value)
            Path(path).write_bytes(b"state-dict-only")

        @staticmethod
        def load(path: Path, *, map_location: str, weights_only: bool) -> object:
            assert Path(path).read_bytes() == b"state-dict-only"
            assert map_location == "cpu"
            assert weights_only is True
            return state

    class Model:
        loaded: object = None

        def state_dict(self) -> object:
            return state

        def load_state_dict(self, value: object, *, strict: bool) -> None:
            self.loaded = (value, strict)

    monkeypatch.setattr(
        adapter,
        "_optional_module",
        lambda name: FakeTorch if name == "torch" else pytest.fail(name),
    )
    model = Model()
    checkpoint = tmp_path / "model.pt"

    paths = adapter.save_checkpoint(
        model,
        checkpoint,
        {"architecture": "mobilenet_v3_small", "epoch": 4},
    )

    assert saved == [state]
    assert Path(paths["checkpoint"]).read_bytes() == b"state-dict-only"
    document = json.loads(Path(paths["metadata"]).read_text(encoding="utf-8"))
    assert document["format"] == "pytorch_state_dict_v1"
    assert document["metadata"]["epoch"] == 4
    assert "model" not in document
    loaded = adapter.load_checkpoint(model, checkpoint)
    assert model.loaded == (state, True)
    assert loaded == document


def test_onnx_export_has_fixed_names_opset_and_dynamic_batch_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    class FakeOnnx:
        @staticmethod
        def export(model: object, example: object, destination: Path, **kwargs: object) -> None:
            captured.update(kwargs)
            captured["destination"] = destination

    fake_torch = SimpleNamespace(
        float32="float32",
        zeros=lambda shape, **kwargs: {"shape": shape, **kwargs},
        onnx=FakeOnnx,
    )
    monkeypatch.setattr(
        adapter,
        "_optional_module",
        lambda name: fake_torch if name == "torch" else pytest.fail(name),
    )

    class Model:
        def to(self, device: str) -> "Model":
            assert device == "cpu"
            return self

        def eval(self) -> "Model":
            return self

    output = adapter.export_onnx(Model(), tmp_path / "model.onnx")

    assert output == (tmp_path / "model.onnx").resolve()
    assert captured["opset_version"] == 17
    assert captured["input_names"] == ["input"]
    assert captured["output_names"] == ["logits"]
    assert captured["dynamic_axes"] == {
        "input": {0: "batch"},
        "logits": {0: "batch"},
    }
    assert captured["dynamo"] is False
