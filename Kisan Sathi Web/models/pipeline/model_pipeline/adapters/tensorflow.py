"""Optional TensorFlow/Keras/TensorFlow Hub lifecycle adapter.

The module is safe to import in the dependency-light pipeline environment.
TensorFlow, TensorFlow Hub, and tf2onnx are imported only by calls that need
them. Dataset membership is always supplied by an explicit JSON manifest; no
directory walking or random split creation is performed here.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SPLITS = ("train", "validation", "test")
CALIBRATION_SPLIT = "calibration"
ONNX_OPSET = 17
ONNX_INPUT_NAME = "input"
ONNX_OUTPUT_NAME = "logits"


class TensorFlowAdapterError(RuntimeError):
    """Base error for the optional adapter."""


class OptionalDependencyError(TensorFlowAdapterError):
    """Raised when an optional framework dependency is unavailable."""


class DatasetManifestError(TensorFlowAdapterError, ValueError):
    """Raised when explicit dataset membership is unsafe or incomplete."""


@dataclass(frozen=True)
class ArchitectureDefinition:
    factory: str
    default_weight: str


KERAS_ARCHITECTURES: Mapping[str, ArchitectureDefinition] = {
    "mobilenet_v3_small": ArchitectureDefinition(
        factory="MobileNetV3Small", default_weight="imagenet"
    ),
    "mobilenet_v3_large": ArchitectureDefinition(
        factory="MobileNetV3Large", default_weight="imagenet"
    ),
    "efficientnet_b0": ArchitectureDefinition(
        factory="EfficientNetB0", default_weight="imagenet"
    ),
}


@dataclass(frozen=True)
class DatasetRecord:
    path: Path
    label: str
    label_index: int
    split: str
    checksum_sha256: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DatasetManifest:
    path: Path
    root: Path
    class_names: tuple[str, ...]
    records: Mapping[str, tuple[DatasetRecord, ...]]

    def records_for(self, split: str) -> tuple[DatasetRecord, ...]:
        try:
            return self.records[split]
        except KeyError as exc:
            raise KeyError(
                f"unknown split {split!r}; available splits: {tuple(self.records)}"
            ) from exc


@dataclass(frozen=True)
class AugmentationConfig:
    horizontal_flip: bool = True
    rotation: float = 0.04
    contrast: float = 0.12
    brightness: float = 0.10
    zoom: float = 0.10

    def __post_init__(self) -> None:
        for name in ("rotation", "contrast", "brightness", "zoom"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                raise ValueError(f"augmentation {name} must be a non-negative number")


@dataclass(frozen=True)
class FineTuneStage:
    name: str
    epochs: int
    learning_rate: float
    trainable: str = "classifier"
    weight_decay: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("stage name must not be empty")
        if not isinstance(self.epochs, int) or isinstance(self.epochs, bool) or self.epochs <= 0:
            raise ValueError("stage epochs must be a positive integer")
        if self.learning_rate <= 0:
            raise ValueError("stage learning_rate must be positive")
        if self.weight_decay < 0:
            raise ValueError("stage weight_decay must be non-negative")
        if self.trainable not in {"classifier", "all"}:
            raise ValueError("stage trainable must be 'classifier' or 'all'")


DEFAULT_FINE_TUNE_STAGES = (
    FineTuneStage("classifier", epochs=3, learning_rate=1e-3, trainable="classifier"),
    FineTuneStage("fine_tune", epochs=5, learning_rate=1e-4, trainable="all"),
)


@dataclass(frozen=True)
class TFHubFeatureVector:
    """Configuration for one immutable TF Hub feature-vector export."""

    handle: str
    trainable: bool = False

    def __post_init__(self) -> None:
        validate_tfhub_handle(self.handle)
        if not isinstance(self.trainable, bool):
            raise ValueError("TF Hub trainable must be a boolean")

    @classmethod
    def from_config(
        cls, config: "TFHubFeatureVector | Mapping[str, Any] | str"
    ) -> "TFHubFeatureVector":
        if isinstance(config, cls):
            return config
        if isinstance(config, str):
            return cls(handle=config)
        if not isinstance(config, Mapping):
            raise ValueError("TF Hub configuration must be an object containing handle")
        extra = sorted(set(config) - {"handle", "trainable"})
        if extra:
            raise ValueError(f"unknown TF Hub configuration fields: {', '.join(extra)}")
        if "handle" not in config:
            raise ValueError("TF Hub configuration requires an explicit handle")
        return cls(handle=config["handle"], trainable=config.get("trainable", False))


def _optional_module(name: str) -> Any:
    try:
        return importlib.import_module(name)
    except (ImportError, ModuleNotFoundError, OSError) as exc:
        if name == "tf2onnx":
            message = (
                "TensorFlow-to-ONNX export requires tf2onnx. Install "
                "models/pipeline/requirements-tensorflow.txt, or install tf2onnx "
                "in the dedicated model-export environment."
            )
        else:
            message = (
                "TensorFlow training/export support is optional. Install "
                "models/pipeline/requirements-tensorflow.txt before using this adapter."
            )
        raise OptionalDependencyError(message) from exc


def _tensorflow() -> Any:
    return _optional_module("tensorflow")


def _tensorflow_hub() -> Any:
    return _optional_module("tensorflow_hub")


def available_architectures() -> tuple[str, ...]:
    return tuple(KERAS_ARCHITECTURES)


def default_pretrained_weight(architecture: str) -> str:
    try:
        return KERAS_ARCHITECTURES[architecture].default_weight
    except KeyError as exc:
        raise ValueError(f"unsupported architecture {architecture!r}") from exc


def validate_tfhub_handle(handle: str) -> str:
    """Require an explicit feature-vector handle ending in a numeric version."""

    if not isinstance(handle, str) or not handle.strip():
        raise ValueError("TF Hub handle must be a non-empty string")
    normalized = handle.strip().rstrip("/")
    if not (
        normalized.startswith("https://tfhub.dev/")
        or normalized.startswith("tfhub://")
    ):
        raise ValueError("TF Hub handle must use https://tfhub.dev/ or tfhub://")
    if not re.search(r"/(?:feature_vector|feature-vector)/\d+$", normalized):
        raise ValueError(
            "TF Hub handle must identify a feature-vector export and end in an "
            "explicit numeric version, for example .../feature_vector/5"
        )
    return normalized


def _string_list(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise DatasetManifestError(f"{field_name} must be a non-empty JSON array")
    result = tuple(value)
    if any(not isinstance(item, str) or not item.strip() for item in result):
        raise DatasetManifestError(f"{field_name} entries must be non-empty strings")
    if len(set(result)) != len(result):
        raise DatasetManifestError(f"{field_name} entries must be unique")
    return result


def _records_by_split(
    raw: Mapping[str, Any], required_splits: Sequence[str]
) -> Mapping[str, list[Any]]:
    records = raw.get("records", raw.get("splits"))
    if isinstance(records, Mapping):
        missing = [split for split in required_splits if split not in records]
        if missing:
            raise DatasetManifestError(
                "dataset manifest must explicitly contain "
                f"{', '.join(required_splits)} records; missing: {', '.join(missing)}"
            )
        extra = sorted(set(records) - set(required_splits))
        if extra:
            raise DatasetManifestError(f"unknown dataset splits: {', '.join(extra)}")
        return {split: records[split] for split in required_splits}

    if isinstance(records, list):
        grouped: dict[str, list[Any]] = {split: [] for split in required_splits}
        for index, item in enumerate(records):
            if not isinstance(item, Mapping):
                raise DatasetManifestError(f"records[{index}] must be an object")
            split = item.get("split")
            if split not in grouped:
                raise DatasetManifestError(
                    f"records[{index}].split must be one of {tuple(required_splits)}, "
                    f"got {split!r}"
                )
            grouped[split].append(item)
        return grouped

    raise DatasetManifestError(
        "dataset manifest requires records as a split mapping or a list with explicit split fields"
    )


def _safe_record_path(root: Path, value: Any, location: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise DatasetManifestError(f"{location}.path must be a non-empty string")
    candidate = Path(value)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise DatasetManifestError(f"{location}.path escapes the dataset root") from exc
    return resolved


def _load_manifest(
    manifest_path: str | os.PathLike[str],
    *,
    required_splits: Sequence[str],
    require_files: bool,
) -> DatasetManifest:
    path = Path(manifest_path).resolve()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DatasetManifestError(f"cannot read dataset manifest {path}: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise DatasetManifestError("dataset manifest must be a JSON object")

    class_names = _string_list(raw.get("class_names", raw.get("classes")), "class_names")
    raw_root = raw.get("root", ".")
    if not isinstance(raw_root, str) or not raw_root.strip():
        raise DatasetManifestError("root must be a non-empty string")
    root_value = Path(raw_root)
    root = root_value.resolve() if root_value.is_absolute() else (path.parent / root_value).resolve()
    grouped = _records_by_split(raw, required_splits)
    class_to_index = {name: index for index, name in enumerate(class_names)}
    seen_paths: dict[Path, str] = {}
    parsed: dict[str, tuple[DatasetRecord, ...]] = {}

    for split in required_splits:
        items = grouped[split]
        if not isinstance(items, list) or not items:
            raise DatasetManifestError(f"records.{split} must be a non-empty JSON array")
        split_records: list[DatasetRecord] = []
        for index, item in enumerate(items):
            location = f"records.{split}[{index}]"
            if not isinstance(item, Mapping):
                raise DatasetManifestError(f"{location} must be an object")
            record_path = _safe_record_path(root, item.get("path"), location)
            if require_files and not record_path.is_file():
                raise DatasetManifestError(f"{location}.path does not exist: {record_path}")
            if record_path in seen_paths:
                raise DatasetManifestError(
                    f"{location}.path duplicates a record in {seen_paths[record_path]}"
                )
            seen_paths[record_path] = split

            label = item.get("label")
            if isinstance(label, int) and not isinstance(label, bool):
                if not 0 <= label < len(class_names):
                    raise DatasetManifestError(f"{location}.label index is out of range")
                label_index = label
                label_name = class_names[label]
            elif isinstance(label, str) and label in class_to_index:
                label_name = label
                label_index = class_to_index[label]
            else:
                raise DatasetManifestError(
                    f"{location}.label must name a declared class or use its integer index"
                )

            checksum = item.get("sha256")
            if checksum is not None and (
                not isinstance(checksum, str)
                or len(checksum) != 64
                or any(character not in "0123456789abcdefABCDEF" for character in checksum)
            ):
                raise DatasetManifestError(f"{location}.sha256 must be 64 hexadecimal characters")
            metadata = {
                key: value
                for key, value in item.items()
                if key not in {"path", "label", "split", "sha256"}
            }
            split_records.append(
                DatasetRecord(
                    path=record_path,
                    label=label_name,
                    label_index=label_index,
                    split=split,
                    checksum_sha256=checksum.lower() if checksum else None,
                    metadata=metadata,
                )
            )
        parsed[split] = tuple(split_records)

    return DatasetManifest(path=path, root=root, class_names=class_names, records=parsed)


def load_dataset_manifest(
    manifest_path: str | os.PathLike[str], *, require_files: bool = True
) -> DatasetManifest:
    """Load explicit, non-overlapping train/validation/test records."""

    return _load_manifest(
        manifest_path, required_splits=SPLITS, require_files=require_files
    )


def load_calibration_manifest(
    manifest_path: str | os.PathLike[str], *, require_files: bool = True
) -> DatasetManifest:
    """Load a manifest dedicated to representative INT8 calibration records."""

    return _load_manifest(
        manifest_path,
        required_splits=(CALIBRATION_SPLIT,),
        require_files=require_files,
    )


def seed_everything(seed: int) -> None:
    """Set Python and TensorFlow deterministic seeds and deterministic ops."""

    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    tf = _tensorflow()
    os.environ["PYTHONHASHSEED"] = str(seed)
    os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")
    random.seed(seed)
    tf.keras.utils.set_random_seed(seed)
    experimental = getattr(getattr(tf, "config", None), "experimental", None)
    enable = getattr(experimental, "enable_op_determinism", None)
    if enable is not None:
        enable()


def _validate_input_shape(input_shape: Sequence[int]) -> tuple[int, int, int]:
    if len(input_shape) != 3 or any(
        not isinstance(value, int) or isinstance(value, bool) or value <= 0
        for value in input_shape
    ):
        raise ValueError("input_shape must be three positive integers in HWC order")
    if input_shape[2] != 3:
        raise ValueError("input_shape must contain three RGB channels")
    return tuple(input_shape)


def _augmentation_layers(tf: Any, config: AugmentationConfig, seed: int) -> list[Any]:
    layers: list[Any] = []
    if config.horizontal_flip:
        layers.append(tf.keras.layers.RandomFlip("horizontal", seed=seed))
    if config.rotation:
        layers.append(tf.keras.layers.RandomRotation(config.rotation, seed=seed + 1))
    if config.contrast:
        layers.append(tf.keras.layers.RandomContrast(config.contrast, seed=seed + 2))
    if config.brightness:
        layers.append(tf.keras.layers.RandomBrightness(config.brightness, seed=seed + 3))
    if config.zoom:
        layers.append(tf.keras.layers.RandomZoom(config.zoom, seed=seed + 4))
    return layers


def build_augmentation(
    config: AugmentationConfig | None = None, *, seed: int = 0
) -> Any:
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    tf = _tensorflow()
    selected = config or AugmentationConfig()
    return tf.keras.Sequential(
        _augmentation_layers(tf, selected, seed), name="field_like_augmentation"
    )


def _model_shell(
    tf: Any,
    *,
    backbone: Any,
    num_classes: int,
    input_shape: tuple[int, int, int],
    dropout: float,
    augmentation: AugmentationConfig | None,
    seed: int,
    rescale: bool,
    name: str,
) -> Any:
    inputs = tf.keras.Input(shape=input_shape, name=ONNX_INPUT_NAME)
    values = inputs
    if augmentation is not None:
        augment = tf.keras.Sequential(
            _augmentation_layers(tf, augmentation, seed),
            name="field_like_augmentation",
        )
        values = augment(values)
    if rescale:
        values = tf.keras.layers.Rescaling(1.0 / 255.0, name="input_rescaling")(values)
    values = backbone(values, training=False)
    if dropout:
        values = tf.keras.layers.Dropout(dropout, seed=seed, name="classifier_dropout")(
            values
        )
    outputs = tf.keras.layers.Dense(num_classes, name=ONNX_OUTPUT_NAME)(values)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name=name)
    model._kisan_sathi_backbone = backbone
    return model


def create_keras_model(
    architecture: str,
    num_classes: int,
    *,
    weight: str | None = None,
    input_shape: Sequence[int] = (224, 224, 3),
    dropout: float = 0.25,
    augmentation: AugmentationConfig | None = None,
    seed: int = 0,
) -> Any:
    """Create a supported Keras Applications classifier.

    ``weight=None`` is the no-download path. To request pretrained weights the
    caller must explicitly pass ``weight="imagenet"``; defaults are exposed as
    metadata and are never selected implicitly.
    """

    if architecture not in KERAS_ARCHITECTURES:
        raise ValueError(
            f"unsupported architecture {architecture!r}; expected one of {available_architectures()}"
        )
    if not isinstance(num_classes, int) or isinstance(num_classes, bool) or num_classes < 2:
        raise ValueError("num_classes must be an integer of at least 2")
    shape = _validate_input_shape(input_shape)
    if not 0 <= dropout < 1:
        raise ValueError("dropout must be in [0, 1)")
    if weight not in {None, "imagenet"}:
        raise ValueError("Keras Applications weight must be None or 'imagenet'")

    tf = _tensorflow()
    definition = KERAS_ARCHITECTURES[architecture]
    factory = getattr(tf.keras.applications, definition.factory)
    backbone = factory(
        include_top=False,
        weights=weight,
        input_shape=shape,
        pooling="avg",
    )
    backbone.trainable = False
    model = _model_shell(
        tf,
        backbone=backbone,
        num_classes=num_classes,
        input_shape=shape,
        dropout=dropout,
        augmentation=augmentation,
        seed=seed,
        rescale=False,
        name=f"kisansathi_{architecture}",
    )
    model._kisan_sathi_architecture = architecture
    model._kisan_sathi_weight = weight
    model._kisan_sathi_provider = "keras_applications"
    return model


def create_hub_model(
    config: TFHubFeatureVector | Mapping[str, Any] | str,
    num_classes: int,
    *,
    input_shape: Sequence[int] = (224, 224, 3),
    dropout: float = 0.25,
    augmentation: AugmentationConfig | None = None,
    seed: int = 0,
) -> Any:
    """Create a classifier from an explicitly configured, versioned Hub handle."""

    selected = TFHubFeatureVector.from_config(config)
    if not isinstance(num_classes, int) or isinstance(num_classes, bool) or num_classes < 2:
        raise ValueError("num_classes must be an integer of at least 2")
    shape = _validate_input_shape(input_shape)
    if not 0 <= dropout < 1:
        raise ValueError("dropout must be in [0, 1)")
    tf = _tensorflow()
    hub = _tensorflow_hub()
    backbone = hub.KerasLayer(
        selected.handle,
        trainable=selected.trainable,
        name="tfhub_backbone",
    )
    model = _model_shell(
        tf,
        backbone=backbone,
        num_classes=num_classes,
        input_shape=shape,
        dropout=dropout,
        augmentation=augmentation,
        seed=seed,
        rescale=True,
        name="kisansathi_tfhub_feature_vector",
    )
    model._kisan_sathi_architecture = "tensorflow_hub"
    model._kisan_sathi_hub_handle = selected.handle
    model._kisan_sathi_provider = "tensorflow_hub"
    return model


def create_model(
    architecture: str,
    num_classes: int,
    *,
    weight: str | None = None,
    hub_config: TFHubFeatureVector | Mapping[str, Any] | str | None = None,
    input_shape: Sequence[int] = (224, 224, 3),
    dropout: float = 0.25,
    augmentation: AugmentationConfig | None = None,
    seed: int = 0,
) -> Any:
    """Unified model factory for Keras Applications or configured TF Hub."""

    if architecture in {"tensorflow_hub", "tfhub"}:
        if hub_config is None:
            raise ValueError("TF Hub models require hub_config with a versioned handle")
        if weight is not None:
            raise ValueError("weight is not used for TF Hub models")
        return create_hub_model(
            hub_config,
            num_classes,
            input_shape=input_shape,
            dropout=dropout,
            augmentation=augmentation,
            seed=seed,
        )
    if hub_config is not None:
        raise ValueError("hub_config is only valid when architecture is 'tensorflow_hub'")
    return create_keras_model(
        architecture,
        num_classes,
        weight=weight,
        input_shape=input_shape,
        dropout=dropout,
        augmentation=augmentation,
        seed=seed,
    )


def _decode_record(tf: Any, path: Any, label: Any, image_size: tuple[int, int]) -> Any:
    encoded = tf.io.read_file(path)
    image = tf.io.decode_image(encoded, channels=3, expand_animations=False)
    image = tf.image.resize(image, image_size, method="bilinear")
    image = tf.cast(image, tf.float32)
    image.set_shape((image_size[0], image_size[1], 3))
    return image, label


def create_datasets(
    manifest: DatasetManifest | str | os.PathLike[str],
    *,
    batch_size: int,
    seed: int,
    image_size: Sequence[int] = (224, 224),
) -> Mapping[str, Any]:
    """Build deterministic ``tf.data`` datasets from manifest records only."""

    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")
    if (
        len(image_size) != 2
        or any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in image_size)
    ):
        raise ValueError("image_size must contain two positive integers")
    parsed = manifest if isinstance(manifest, DatasetManifest) else load_dataset_manifest(manifest)
    if tuple(parsed.records) != SPLITS:
        raise ValueError(f"training datasets require exactly these splits: {SPLITS}")
    tf = _tensorflow()
    seed_everything(seed)
    size = tuple(image_size)
    result: dict[str, Any] = {}
    for split in SPLITS:
        records = parsed.records_for(split)
        paths = [str(record.path) for record in records]
        labels = [record.label_index for record in records]
        dataset = tf.data.Dataset.from_tensor_slices((paths, labels))
        if split == "train":
            dataset = dataset.shuffle(
                len(records), seed=seed, reshuffle_each_iteration=True
            )
        dataset = dataset.map(
            lambda path, label: _decode_record(tf, path, label, size),
            num_parallel_calls=tf.data.AUTOTUNE,
            deterministic=True,
        )
        options = tf.data.Options()
        options.experimental_deterministic = True
        result[split] = (
            dataset.with_options(options).batch(batch_size).prefetch(tf.data.AUTOTUNE)
        )
    return result


def class_weights(
    train_records: Iterable[DatasetRecord], class_names: Sequence[str]
) -> dict[int, float]:
    counts = [0] * len(class_names)
    for record in train_records:
        if not 0 <= record.label_index < len(counts):
            raise ValueError("training record contains an out-of-range class index")
        counts[record.label_index] += 1
    if not counts or any(count == 0 for count in counts):
        missing = [class_names[index] for index, count in enumerate(counts) if count == 0]
        raise ValueError(f"weighted loss requires training examples for every class: {missing}")
    total = sum(counts)
    return {index: total / (len(counts) * count) for index, count in enumerate(counts)}


def set_trainable_parameters(model: Any, trainable: str) -> int:
    """Freeze the configured backbone or unfreeze it for a later stage."""

    if trainable not in {"classifier", "all"}:
        raise ValueError("trainable must be 'classifier' or 'all'")
    backbone = getattr(model, "_kisan_sathi_backbone", None)
    if backbone is None:
        try:
            backbone = model.get_layer("tfhub_backbone")
        except (AttributeError, ValueError) as exc:
            raise ValueError("model does not expose its KisanSathi backbone") from exc
    backbone.trainable = trainable == "all"
    variables = getattr(model, "trainable_variables", ())
    count = sum(int(getattr(variable, "shape", ()).num_elements()) for variable in variables)
    return count


def classification_metrics(
    y_true: Sequence[int], y_pred: Sequence[int], class_names: Sequence[str]
) -> Mapping[str, Any]:
    """Compute confusion matrix, per-class recall, and macro-F1 without sklearn."""

    if len(y_true) != len(y_pred) or not y_true:
        raise ValueError("y_true and y_pred must be non-empty and have the same length")
    if not class_names:
        raise ValueError("class_names must not be empty")
    size = len(class_names)
    matrix = [[0 for _ in range(size)] for _ in range(size)]
    for index, (truth, prediction) in enumerate(zip(y_true, y_pred, strict=True)):
        if not isinstance(truth, int) or not isinstance(prediction, int):
            raise ValueError(f"labels at position {index} must be integers")
        if not 0 <= truth < size or not 0 <= prediction < size:
            raise ValueError(f"labels at position {index} are outside the class range")
        matrix[truth][prediction] += 1

    per_class_recall: dict[str, float] = {}
    per_class_f1: dict[str, float] = {}
    for index, name in enumerate(class_names):
        true_positive = matrix[index][index]
        actual = sum(matrix[index])
        predicted = sum(row[index] for row in matrix)
        recall = true_positive / actual if actual else 0.0
        precision = true_positive / predicted if predicted else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class_recall[name] = recall
        per_class_f1[name] = f1
    correct = sum(matrix[index][index] for index in range(size))
    return {
        "sample_count": len(y_true),
        "accuracy": correct / len(y_true),
        "confusion_matrix": matrix,
        "per_class_recall": per_class_recall,
        "per_class_f1": per_class_f1,
        "macro_f1": sum(per_class_f1.values()) / size,
    }


def _python_values(value: Any) -> list[int]:
    if hasattr(value, "numpy"):
        value = value.numpy()
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [int(item) for item in value]


def evaluate_model(
    model: Any, dataset: Iterable[Any], class_names: Sequence[str]
) -> Mapping[str, Any]:
    tf = _tensorflow()
    y_true: list[int] = []
    y_pred: list[int] = []
    for images, labels in dataset:
        logits = model(images, training=False)
        predictions = tf.argmax(logits, axis=-1)
        y_true.extend(_python_values(labels))
        y_pred.extend(_python_values(predictions))
    return classification_metrics(y_true, y_pred, class_names)


def _optimizer(tf: Any, stage: FineTuneStage) -> Any:
    if stage.weight_decay:
        adamw = getattr(tf.keras.optimizers, "AdamW", None)
        if adamw is None:
            raise TensorFlowAdapterError(
                "this TensorFlow build lacks keras.optimizers.AdamW required by weight_decay"
            )
        return adamw(learning_rate=stage.learning_rate, weight_decay=stage.weight_decay)
    return tf.keras.optimizers.Adam(learning_rate=stage.learning_rate)


def train_model(
    model: Any,
    datasets: Mapping[str, Any],
    manifest: DatasetManifest,
    *,
    stages: Sequence[FineTuneStage] = DEFAULT_FINE_TUNE_STAGES,
    class_weight_mode: str = "standard",
    seed: int = 0,
    callbacks: Sequence[Any] = (),
) -> list[Mapping[str, Any]]:
    """Train a frozen head followed by explicitly configured unfreezing stages."""

    if "train" not in datasets or "validation" not in datasets:
        raise ValueError("datasets must contain train and validation")
    if not stages:
        raise ValueError("at least one fine-tuning stage is required")
    if class_weight_mode not in {"standard", "weighted"}:
        raise ValueError("class_weight_mode must be 'standard' or 'weighted'")
    tf = _tensorflow()
    seed_everything(seed)
    weights = (
        class_weights(manifest.records_for("train"), manifest.class_names)
        if class_weight_mode == "weighted"
        else None
    )
    history: list[Mapping[str, Any]] = []
    completed_epochs = 0
    for stage in stages:
        set_trainable_parameters(model, stage.trainable)
        model.compile(
            optimizer=_optimizer(tf, stage),
            loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
            metrics=[tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy")],
        )
        fitted = model.fit(
            datasets["train"],
            validation_data=datasets["validation"],
            initial_epoch=completed_epochs,
            epochs=completed_epochs + stage.epochs,
            class_weight=weights,
            callbacks=list(callbacks),
            verbose=0,
        )
        stage_history = {
            key: [float(value) for value in values]
            for key, values in fitted.history.items()
        }
        completed = len(stage_history.get("loss", []))
        completed_epochs += completed
        history.append(
            {
                "stage": stage.name,
                "trainable": stage.trainable,
                "planned_epochs": stage.epochs,
                "completed_epochs": completed,
                "learning_rate": stage.learning_rate,
                "history": stage_history,
            }
        )
    return history


def _json_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    try:
        encoded = json.dumps(dict(metadata), sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("checkpoint metadata must be finite JSON data") from exc
    return json.loads(encoded)


def _sha256_artifact(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_file():
        files = (path,)
        root = path.parent
    elif path.is_dir():
        files = tuple(sorted(item for item in path.rglob("*") if item.is_file()))
        root = path
    else:
        raise TensorFlowAdapterError(f"checkpoint artifact was not created: {path}")
    for item in files:
        digest.update(item.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        with item.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def save_checkpoint(
    model: Any,
    checkpoint_path: str | os.PathLike[str],
    metadata: Mapping[str, Any],
    *,
    format: str = "keras",
    metadata_path: str | os.PathLike[str] | None = None,
) -> Mapping[str, str]:
    """Save a Keras checkpoint or SavedModel plus a separate JSON sidecar."""

    if format not in {"keras", "saved_model"}:
        raise ValueError("checkpoint format must be 'keras' or 'saved_model'")
    destination = Path(checkpoint_path).resolve()
    if format == "keras" and destination.suffix != ".keras":
        raise ValueError("Keras checkpoints must use a .keras extension")
    sidecar = (
        Path(metadata_path).resolve()
        if metadata_path is not None
        else destination.with_name(destination.name + ".json")
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    if format == "keras":
        model.save(str(destination))
    else:
        exporter = getattr(model, "export", None)
        if exporter is not None:
            exporter(str(destination))
        else:
            tf = _tensorflow()
            tf.saved_model.save(model, str(destination))
    document = {
        "format": "tensorflow_keras_v1" if format == "keras" else "tensorflow_saved_model_v1",
        "artifact": destination.name,
        "artifact_sha256": _sha256_artifact(destination),
        "metadata": _json_metadata(metadata),
    }
    sidecar.write_text(
        json.dumps(document, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return {"checkpoint": str(destination), "metadata": str(sidecar)}


def load_checkpoint(
    checkpoint_path: str | os.PathLike[str],
    *,
    metadata_path: str | os.PathLike[str] | None = None,
    custom_objects: Mapping[str, Any] | None = None,
) -> tuple[Any, Mapping[str, Any]]:
    source = Path(checkpoint_path).resolve()
    sidecar = (
        Path(metadata_path).resolve()
        if metadata_path is not None
        else source.with_name(source.name + ".json")
    )
    document = json.loads(sidecar.read_text(encoding="utf-8"))
    if document.get("format") not in {
        "tensorflow_keras_v1",
        "tensorflow_saved_model_v1",
    }:
        raise TensorFlowAdapterError("unsupported checkpoint metadata format")
    if document.get("artifact_sha256") != _sha256_artifact(source):
        raise TensorFlowAdapterError("checkpoint hash does not match JSON metadata")
    tf = _tensorflow()
    if document["format"] == "tensorflow_keras_v1":
        model = tf.keras.models.load_model(str(source), custom_objects=custom_objects)
    else:
        model = tf.saved_model.load(str(source))
    return model, document


def _representative_dataset(
    tf: Any,
    manifest: DatasetManifest,
    *,
    image_size: tuple[int, int],
    limit: int | None,
) -> Any:
    records = manifest.records_for(CALIBRATION_SPLIT)
    selected = records if limit is None else records[:limit]

    def generate() -> Iterable[list[Any]]:
        for record in selected:
            encoded = tf.io.read_file(str(record.path))
            image = tf.io.decode_image(encoded, channels=3, expand_animations=False)
            image = tf.image.resize(image, image_size, method="bilinear")
            image = tf.cast(tf.expand_dims(image, axis=0), tf.float32)
            yield [image]

    return generate


def build_representative_dataset(
    calibration_manifest: DatasetManifest | str | os.PathLike[str],
    *,
    image_size: Sequence[int] = (224, 224),
    limit: int | None = None,
) -> Any:
    """Create the converter callback from an explicit calibration manifest."""

    if (
        len(image_size) != 2
        or any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in image_size)
    ):
        raise ValueError("image_size must contain two positive integers")
    if limit is not None and (
        not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0
    ):
        raise ValueError("calibration limit must be a positive integer")
    manifest = (
        calibration_manifest
        if isinstance(calibration_manifest, DatasetManifest)
        else load_calibration_manifest(calibration_manifest)
    )
    if tuple(manifest.records) != (CALIBRATION_SPLIT,):
        raise DatasetManifestError(
            "representative calibration data must come from a calibration-only manifest"
        )
    tf = _tensorflow()
    return _representative_dataset(
        tf, manifest, image_size=tuple(image_size), limit=limit
    )


def _tflite_converter(tf: Any, model_or_saved_model: Any) -> Any:
    if isinstance(model_or_saved_model, (str, os.PathLike)):
        source = Path(model_or_saved_model).resolve()
        if not source.is_dir():
            raise ValueError("SavedModel source must be an existing directory")
        return tf.lite.TFLiteConverter.from_saved_model(str(source))
    return tf.lite.TFLiteConverter.from_keras_model(model_or_saved_model)


def export_tflite(
    model_or_saved_model: Any,
    output_path: str | os.PathLike[str],
    *,
    mode: str = "fp32",
    calibration_manifest: DatasetManifest | str | os.PathLike[str] | None = None,
    image_size: Sequence[int] = (224, 224),
    calibration_limit: int | None = None,
    integer_io_type: str = "int8",
) -> Path:
    """Export FP32, float16, or fully integer calibrated INT8 TFLite."""

    normalized_mode = {"full-int8": "int8", "full_int8": "int8"}.get(mode, mode)
    if normalized_mode not in {"fp32", "float16", "int8"}:
        raise ValueError("TFLite mode must be 'fp32', 'float16', or 'int8'")
    if Path(output_path).suffix.lower() != ".tflite":
        raise ValueError("TFLite output path must use a .tflite extension")
    if normalized_mode == "int8" and calibration_manifest is None:
        raise ValueError(
            "full INT8 export requires an explicit representative calibration manifest"
        )
    if integer_io_type not in {"int8", "uint8"}:
        raise ValueError("integer_io_type must be 'int8' or 'uint8'")

    tf = _tensorflow()
    converter = _tflite_converter(tf, model_or_saved_model)
    if normalized_mode == "float16":
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.target_spec.supported_types = [tf.float16]
    elif normalized_mode == "int8":
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.representative_dataset = build_representative_dataset(
            calibration_manifest,
            image_size=image_size,
            limit=calibration_limit,
        )
        converter.target_spec.supported_ops = [
            tf.lite.OpsSet.TFLITE_BUILTINS_INT8
        ]
        io_dtype = tf.int8 if integer_io_type == "int8" else tf.uint8
        converter.inference_input_type = io_dtype
        converter.inference_output_type = io_dtype

    converted = converter.convert()
    if not isinstance(converted, (bytes, bytearray)) or not converted:
        raise TensorFlowAdapterError("TFLite converter did not produce a non-empty artifact")
    destination = Path(output_path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(bytes(converted))
    return destination


def export_tflite_variants(
    model_or_saved_model: Any,
    output_dir: str | os.PathLike[str],
    *,
    calibration_manifest: DatasetManifest | str | os.PathLike[str],
    image_size: Sequence[int] = (224, 224),
    calibration_limit: int | None = None,
    integer_io_type: str = "int8",
) -> Mapping[str, Path]:
    """Export the three supported variants; INT8 calibration is mandatory."""

    if calibration_manifest is None:
        raise ValueError(
            "exporting all TFLite variants requires a representative calibration manifest"
        )
    root = Path(output_dir).resolve()
    return {
        "fp32": export_tflite(model_or_saved_model, root / "model-fp32.tflite", mode="fp32"),
        "float16": export_tflite(
            model_or_saved_model, root / "model-float16.tflite", mode="float16"
        ),
        "int8": export_tflite(
            model_or_saved_model,
            root / "model-int8.tflite",
            mode="int8",
            calibration_manifest=calibration_manifest,
            image_size=image_size,
            calibration_limit=calibration_limit,
            integer_io_type=integer_io_type,
        ),
    }


def export_onnx(
    model: Any,
    output_path: str | os.PathLike[str],
    *,
    input_shape: Sequence[int] = (224, 224, 3),
    opset: int = ONNX_OPSET,
) -> Path:
    """Export a Keras model through tf2onnx with a dynamic batch dimension."""

    shape = _validate_input_shape(input_shape)
    if not isinstance(opset, int) or isinstance(opset, bool) or opset <= 0:
        raise ValueError("opset must be a positive integer")
    tf = _tensorflow()
    tf2onnx = _optional_module("tf2onnx")
    destination = Path(output_path).resolve()
    if destination.suffix.lower() != ".onnx":
        raise ValueError("ONNX output path must use a .onnx extension")
    destination.parent.mkdir(parents=True, exist_ok=True)
    signature = (
        tf.TensorSpec((None, *shape), tf.float32, name=ONNX_INPUT_NAME),
    )
    tf2onnx.convert.from_keras(
        model,
        input_signature=signature,
        opset=opset,
        output_path=str(destination),
    )
    return destination


__all__ = [
    "CALIBRATION_SPLIT",
    "DEFAULT_FINE_TUNE_STAGES",
    "KERAS_ARCHITECTURES",
    "ONNX_INPUT_NAME",
    "ONNX_OPSET",
    "ONNX_OUTPUT_NAME",
    "SPLITS",
    "ArchitectureDefinition",
    "AugmentationConfig",
    "DatasetManifest",
    "DatasetManifestError",
    "DatasetRecord",
    "FineTuneStage",
    "OptionalDependencyError",
    "TFHubFeatureVector",
    "TensorFlowAdapterError",
    "available_architectures",
    "build_augmentation",
    "build_representative_dataset",
    "class_weights",
    "classification_metrics",
    "create_datasets",
    "create_hub_model",
    "create_keras_model",
    "create_model",
    "default_pretrained_weight",
    "evaluate_model",
    "export_onnx",
    "export_tflite",
    "export_tflite_variants",
    "load_calibration_manifest",
    "load_checkpoint",
    "load_dataset_manifest",
    "save_checkpoint",
    "seed_everything",
    "set_trainable_parameters",
    "train_model",
    "validate_tfhub_handle",
]
