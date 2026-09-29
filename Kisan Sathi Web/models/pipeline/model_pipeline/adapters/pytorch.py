    """Optional PyTorch/TorchVision training adapter.

This module deliberately has no import-time dependency on either framework.
Dataset membership comes only from an explicit JSON manifest; this adapter never
walks a directory or creates a random release split.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SPLITS = ("train", "validation", "test")
ONNX_OPSET = 17
ONNX_INPUT_NAME = "input"
ONNX_OUTPUT_NAME = "logits"


class PyTorchAdapterError(RuntimeError):
    """Base error for the optional adapter."""


class OptionalDependencyError(PyTorchAdapterError):
    """Raised when the optional PyTorch dependency group is unavailable."""


class DatasetManifestError(PyTorchAdapterError, ValueError):
    """Raised when a dataset manifest is unsafe or incomplete."""


@dataclass(frozen=True)
class ArchitectureDefinition:
    factory: str
    weights_enum: str
    default_weight: str
    classifier_attribute: str


ARCHITECTURES: Mapping[str, ArchitectureDefinition] = {
    "mobilenet_v3_small": ArchitectureDefinition(
        factory="mobilenet_v3_small",
        weights_enum="MobileNet_V3_Small_Weights",
        default_weight="IMAGENET1K_V1",
        classifier_attribute="classifier",
    ),
    "mobilenet_v3_large": ArchitectureDefinition(
        factory="mobilenet_v3_large",
        weights_enum="MobileNet_V3_Large_Weights",
        default_weight="IMAGENET1K_V2",
        classifier_attribute="classifier",
    ),
    "efficientnet_b0": ArchitectureDefinition(
        factory="efficientnet_b0",
        weights_enum="EfficientNet_B0_Weights",
        default_weight="IMAGENET1K_V1",
        classifier_attribute="classifier",
    ),
    "shufflenet_v2_x1_0": ArchitectureDefinition(
        factory="shufflenet_v2_x1_0",
        weights_enum="ShuffleNet_V2_X1_0_Weights",
        default_weight="IMAGENET1K_V1",
        classifier_attribute="fc",
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
        if split not in SPLITS:
            raise KeyError(f"unknown split {split!r}; expected one of {SPLITS}")
        return self.records[split]


@dataclass(frozen=True)
class FineTuneStage:
    name: str
    epochs: int
    learning_rate: float
    trainable: str = "classifier"
    weight_decay: float = 0.0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("stage name must not be empty")
        if self.epochs <= 0:
            raise ValueError("stage epochs must be positive")
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


def _optional_module(name: str) -> Any:
    try:
        return importlib.import_module(name)
    except (ImportError, ModuleNotFoundError, OSError) as exc:
        raise OptionalDependencyError(
            "PyTorch training support is optional. Install "
            "models/pipeline/requirements-pytorch.txt before using this adapter."
        ) from exc


def _frameworks() -> tuple[Any, Any]:
    """Import torch and torchvision lazily at the call boundary."""

    return _optional_module("torch"), _optional_module("torchvision")


def available_architectures() -> tuple[str, ...]:
    return tuple(ARCHITECTURES)


def _resolve_weight(models: Any, definition: ArchitectureDefinition, weight: str | None) -> Any:
    if weight is None:
        return None
    enum_class = getattr(models, definition.weights_enum)
    try:
        return enum_class[weight]
    except KeyError as exc:
        choices = ", ".join(member.name for member in enum_class)
        raise ValueError(
            f"unknown {definition.weights_enum} member {weight!r}; choose one of: {choices}"
        ) from exc


def create_model(
    architecture: str,
    num_classes: int,
    *,
    weight: str | None = None,
) -> Any:
    """Build a supported model and replace its classifier.

    ``weight=None`` is intentionally the no-download path. Callers requesting
    pretrained weights must name a concrete TorchVision enum member, for example
    ``weight="IMAGENET1K_V1"``. The architecture-specific stable default can be
    obtained from :data:`ARCHITECTURES`; it is never selected implicitly.
    """

    if architecture not in ARCHITECTURES:
        raise ValueError(
            f"unsupported architecture {architecture!r}; expected one of {available_architectures()}"
        )
    if not isinstance(num_classes, int) or isinstance(num_classes, bool) or num_classes < 2:
        raise ValueError("num_classes must be an integer of at least 2")

    torch, torchvision = _frameworks()
    models = torchvision.models
    definition = ARCHITECTURES[architecture]
    selected_weight = _resolve_weight(models, definition, weight)
    model = getattr(models, definition.factory)(weights=selected_weight)

    if definition.classifier_attribute == "fc":
        in_features = model.fc.in_features
        model.fc = torch.nn.Linear(in_features, num_classes)
    else:
        classifier = model.classifier
        in_features = classifier[-1].in_features
        classifier[-1] = torch.nn.Linear(in_features, num_classes)

    model._kisan_sathi_architecture = architecture
    model._kisan_sathi_weight = weight
    return model


def default_pretrained_weight(architecture: str) -> str:
    try:
        return ARCHITECTURES[architecture].default_weight
    except KeyError as exc:
        raise ValueError(f"unsupported architecture {architecture!r}") from exc


def _string_list(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise DatasetManifestError(f"{field_name} must be a non-empty JSON array")
    result = tuple(value)
    if any(not isinstance(item, str) or not item.strip() for item in result):
        raise DatasetManifestError(f"{field_name} entries must be non-empty strings")
    if len(set(result)) != len(result):
        raise DatasetManifestError(f"{field_name} entries must be unique")
    return result


def _records_by_split(raw: Mapping[str, Any]) -> Mapping[str, list[Any]]:
    records = raw.get("records", raw.get("splits"))
    if isinstance(records, Mapping):
        missing = [split for split in SPLITS if split not in records]
        if missing:
            raise DatasetManifestError(
                "dataset manifest must explicitly contain train, validation, and test records; "
                f"missing: {', '.join(missing)}"
            )
        extra = sorted(set(records) - set(SPLITS))
        if extra:
            raise DatasetManifestError(f"unknown dataset splits: {', '.join(extra)}")
        return {split: records[split] for split in SPLITS}

    if isinstance(records, list):
        grouped: dict[str, list[Any]] = {split: [] for split in SPLITS}
        for index, item in enumerate(records):
            if not isinstance(item, Mapping):
                raise DatasetManifestError(f"records[{index}] must be an object")
            split = item.get("split")
            if split not in grouped:
                raise DatasetManifestError(
                    f"records[{index}].split must be one of {SPLITS}, got {split!r}"
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


def load_dataset_manifest(
    manifest_path: str | os.PathLike[str],
    *,
    require_files: bool = True,
) -> DatasetManifest:
    """Load an explicit train/validation/test manifest without discovering files."""

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
    root_path = Path(raw_root)
    root = root_path.resolve() if root_path.is_absolute() else (path.parent / root_path).resolve()
    grouped = _records_by_split(raw)
    class_to_index = {name: index for index, name in enumerate(class_names)}
    seen_paths: dict[Path, str] = {}
    parsed: dict[str, tuple[DatasetRecord, ...]] = {}

    for split in SPLITS:
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
                if label < 0 or label >= len(class_names):
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


def seed_everything(seed: int) -> None:
    """Configure deterministic Python and PyTorch execution."""

    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    torch = _optional_module("torch")
    os.environ["PYTHONHASHSEED"] = str(seed)
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True


def build_transforms(
    *,
    image_size: int = 224,
    resize_size: int = 256,
    mean: Sequence[float] = (0.485, 0.456, 0.406),
    std: Sequence[float] = (0.229, 0.224, 0.225),
) -> Mapping[str, Any]:
    if image_size <= 0 or resize_size < image_size:
        raise ValueError("resize_size must be at least image_size and both must be positive")
    if len(mean) != 3 or len(std) != 3 or any(value <= 0 for value in std):
        raise ValueError("mean and std must contain three channels and std values must be positive")
    torchvision = _optional_module("torchvision")
    transforms = torchvision.transforms
    interpolation = transforms.InterpolationMode.BILINEAR
    normalize = transforms.Normalize(mean=tuple(mean), std=tuple(std))
    evaluation = transforms.Compose(
        [
            transforms.Resize(resize_size, interpolation=interpolation, antialias=True),
            transforms.CenterCrop(image_size),
            transforms.ToTensor(),
            normalize,
        ]
    )
    training = transforms.Compose(
        [
            transforms.RandomResizedCrop(
                image_size,
                scale=(0.8, 1.0),
                interpolation=interpolation,
                antialias=True,
            ),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            normalize,
        ]
    )
    return {"train": training, "validation": evaluation, "test": evaluation}


def create_datasets(
    manifest: DatasetManifest | str | os.PathLike[str],
    *,
    transforms: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Create image datasets from manifest records only."""

    torch = _optional_module("torch")
    parsed = manifest if isinstance(manifest, DatasetManifest) else load_dataset_manifest(manifest)
    selected_transforms = transforms or build_transforms()
    if any(split not in selected_transforms for split in SPLITS):
        raise ValueError(f"transforms must contain every split: {SPLITS}")

    class ManifestImageDataset(torch.utils.data.Dataset):
        def __init__(self, records: Sequence[DatasetRecord], transform: Any) -> None:
            self.records = tuple(records)
            self.transform = transform

        def __len__(self) -> int:
            return len(self.records)

        def __getitem__(self, index: int) -> tuple[Any, int]:
            image_module = _optional_module("PIL.Image")
            record = self.records[index]
            with image_module.open(record.path) as source:
                image = source.convert("RGB")
                tensor = self.transform(image)
            return tensor, record.label_index

    return {
        split: ManifestImageDataset(parsed.records_for(split), selected_transforms[split])
        for split in SPLITS
    }


def _seed_data_worker(_: int) -> None:
    torch = _optional_module("torch")
    worker_seed = torch.initial_seed() % (2**32)
    random.seed(worker_seed)


def create_dataloaders(
    manifest: DatasetManifest | str | os.PathLike[str],
    *,
    batch_size: int,
    seed: int,
    num_workers: int = 0,
    transforms: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    if batch_size <= 0 or num_workers < 0:
        raise ValueError("batch_size must be positive and num_workers must be non-negative")
    torch = _optional_module("torch")
    seed_everything(seed)
    datasets = create_datasets(manifest, transforms=transforms)
    generator = torch.Generator()
    generator.manual_seed(seed)
    return {
        split: torch.utils.data.DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=split == "train",
            num_workers=num_workers,
            worker_init_fn=_seed_data_worker,
            generator=generator,
            persistent_workers=num_workers > 0,
        )
        for split, dataset in datasets.items()
    }


def class_weights(
    train_records: Iterable[DatasetRecord], class_names: Sequence[str]
) -> tuple[float, ...]:
    counts = [0] * len(class_names)
    for record in train_records:
        if record.label_index < 0 or record.label_index >= len(counts):
            raise ValueError("training record contains an out-of-range class index")
        counts[record.label_index] += 1
    if not counts or any(count == 0 for count in counts):
        missing = [class_names[index] for index, count in enumerate(counts) if count == 0]
        raise ValueError(f"weighted loss requires training examples for every class: {missing}")
    total = sum(counts)
    return tuple(total / (len(counts) * count) for count in counts)


def create_cross_entropy(
    *,
    mode: str,
    train_records: Iterable[DatasetRecord],
    class_names: Sequence[str],
    device: str = "cpu",
    label_smoothing: float = 0.0,
) -> Any:
    if mode not in {"standard", "weighted"}:
        raise ValueError("cross entropy mode must be 'standard' or 'weighted'")
    if not 0.0 <= label_smoothing < 1.0:
        raise ValueError("label_smoothing must be in [0, 1)")
    torch = _optional_module("torch")
    weight_tensor = None
    if mode == "weighted":
        weight_tensor = torch.tensor(
            class_weights(train_records, class_names), dtype=torch.float32, device=device
        )
    return torch.nn.CrossEntropyLoss(weight=weight_tensor, label_smoothing=label_smoothing)


def set_trainable_parameters(model: Any, trainable: str) -> int:
    """Freeze the backbone or unfreeze the complete model for a training stage."""

    if trainable not in {"classifier", "all"}:
        raise ValueError("trainable must be 'classifier' or 'all'")
    for parameter in model.parameters():
        parameter.requires_grad = trainable == "all"
    if trainable == "classifier":
        classifier = getattr(model, "classifier", None) or getattr(model, "fc", None)
        if classifier is None:
            raise ValueError("model has no supported replaceable classifier")
        for parameter in classifier.parameters():
            parameter.requires_grad = True
    count = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    if count == 0:
        raise ValueError("training stage selected no trainable parameters")
    return count


def _batch(batch: Any, device: str) -> tuple[Any, Any]:
    if isinstance(batch, Mapping):
        images, labels = batch["images"], batch["labels"]
    else:
        images, labels = batch
    return images.to(device), labels.to(device)


def classification_metrics(
    y_true: Sequence[int], y_pred: Sequence[int], class_names: Sequence[str]
) -> Mapping[str, Any]:
    """Compute deterministic classification metrics without sklearn."""

    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    if not class_names:
        raise ValueError("class_names must not be empty")
    size = len(class_names)
    matrix = [[0 for _ in range(size)] for _ in range(size)]
    for index, (truth, prediction) in enumerate(zip(y_true, y_pred)):
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
    total = len(y_true)
    correct = sum(matrix[index][index] for index in range(size))
    return {
        "sample_count": total,
        "accuracy": correct / total if total else 0.0,
        "confusion_matrix": matrix,
        "per_class_recall": per_class_recall,
        "per_class_f1": per_class_f1,
        "macro_f1": sum(per_class_f1.values()) / size,
    }


def evaluate_model(
    model: Any,
    dataloader: Iterable[Any],
    class_names: Sequence[str],
    *,
    device: str = "cpu",
) -> Mapping[str, Any]:
    torch = _optional_module("torch")
    model.to(device)
    model.eval()
    y_true: list[int] = []
    y_pred: list[int] = []
    with torch.inference_mode():
        for raw_batch in dataloader:
            images, labels = _batch(raw_batch, device)
            logits = model(images)
            predictions = logits.argmax(dim=1)
            y_true.extend(int(value) for value in labels.detach().cpu().tolist())
            y_pred.extend(int(value) for value in predictions.detach().cpu().tolist())
    return classification_metrics(y_true, y_pred, class_names)


def train_model(
    model: Any,
    dataloaders: Mapping[str, Iterable[Any]],
    manifest: DatasetManifest,
    *,
    stages: Sequence[FineTuneStage] = DEFAULT_FINE_TUNE_STAGES,
    loss_mode: str = "standard",
    device: str = "cpu",
    seed: int = 0,
    label_smoothing: float = 0.0,
) -> list[Mapping[str, Any]]:
    """Train classifier-first then optionally unfreeze using explicit stages."""

    if "train" not in dataloaders or "validation" not in dataloaders:
        raise ValueError("dataloaders must contain train and validation")
    if not stages:
        raise ValueError("at least one fine-tuning stage is required")
    torch = _optional_module("torch")
    seed_everything(seed)
    model.to(device)
    criterion = create_cross_entropy(
        mode=loss_mode,
        train_records=manifest.records_for("train"),
        class_names=manifest.class_names,
        device=device,
        label_smoothing=label_smoothing,
    )
    history: list[Mapping[str, Any]] = []
    global_epoch = 0
    for stage in stages:
        set_trainable_parameters(model, stage.trainable)
        optimizer = torch.optim.AdamW(
            (parameter for parameter in model.parameters() if parameter.requires_grad),
            lr=stage.learning_rate,
            weight_decay=stage.weight_decay,
        )
        for stage_epoch in range(stage.epochs):
            model.train()
            total_loss = 0.0
            samples = 0
            for raw_batch in dataloaders["train"]:
                images, labels = _batch(raw_batch, device)
                optimizer.zero_grad(set_to_none=True)
                logits = model(images)
                loss = criterion(logits, labels)
                loss.backward()
                optimizer.step()
                batch_size = int(labels.shape[0])
                total_loss += float(loss.detach().item()) * batch_size
                samples += batch_size
            if samples == 0:
                raise ValueError("training dataloader is empty")
            validation = evaluate_model(
                model, dataloaders["validation"], manifest.class_names, device=device
            )
            history.append(
                {
                    "stage": stage.name,
                    "stage_epoch": stage_epoch + 1,
                    "epoch": global_epoch + 1,
                    "train_loss": total_loss / samples,
                    "validation": validation,
                }
            )
            global_epoch += 1
    return history


def _json_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    try:
        encoded = json.dumps(dict(metadata), sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("checkpoint metadata must be finite JSON data") from exc
    return json.loads(encoded)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_checkpoint(
    model: Any,
    checkpoint_path: str | os.PathLike[str],
    metadata: Mapping[str, Any],
    *,
    metadata_path: str | os.PathLike[str] | None = None,
) -> Mapping[str, str]:
    """Save only a state_dict and a separate JSON metadata document."""

    torch = _optional_module("torch")
    destination = Path(checkpoint_path).resolve()
    sidecar = (
        Path(metadata_path).resolve()
        if metadata_path is not None
        else destination.with_suffix(destination.suffix + ".json")
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary_sidecar = sidecar.with_suffix(sidecar.suffix + ".tmp")
    try:
        state_dict = model.state_dict()
        torch.save(state_dict, temporary)
        temporary.replace(destination)
        document = {
            "format": "pytorch_state_dict_v1",
            "state_dict_file": destination.name,
            "state_dict_sha256": _sha256(destination),
            "metadata": _json_metadata(metadata),
        }
        temporary_sidecar.write_text(
            json.dumps(document, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        temporary_sidecar.replace(sidecar)
    finally:
        temporary.unlink(missing_ok=True)
        temporary_sidecar.unlink(missing_ok=True)
    return {"checkpoint": str(destination), "metadata": str(sidecar)}


def load_checkpoint(
    model: Any,
    checkpoint_path: str | os.PathLike[str],
    *,
    metadata_path: str | os.PathLike[str] | None = None,
    map_location: str = "cpu",
    strict: bool = True,
) -> Mapping[str, Any]:
    """Load a weights-only state_dict into an already constructed model."""

    torch = _optional_module("torch")
    source = Path(checkpoint_path).resolve()
    sidecar = (
        Path(metadata_path).resolve()
        if metadata_path is not None
        else source.with_suffix(source.suffix + ".json")
    )
    document = json.loads(sidecar.read_text(encoding="utf-8"))
    if document.get("format") != "pytorch_state_dict_v1":
        raise PyTorchAdapterError("unsupported checkpoint metadata format")
    if document.get("state_dict_sha256") != _sha256(source):
        raise PyTorchAdapterError("checkpoint hash does not match JSON metadata")
    state_dict = torch.load(source, map_location=map_location, weights_only=True)
    if not isinstance(state_dict, Mapping):
        raise PyTorchAdapterError("checkpoint is not a state_dict mapping")
    model.load_state_dict(state_dict, strict=strict)
    return document


def export_onnx(
    model: Any,
    output_path: str | os.PathLike[str],
    *,
    input_shape: Sequence[int] = (3, 224, 224),
    device: str = "cpu",
) -> Path:
    """Export with a fixed web-compatible contract and dynamic batch only."""

    if len(input_shape) != 3 or any(
        not isinstance(value, int) or isinstance(value, bool) or value <= 0
        for value in input_shape
    ):
        raise ValueError("input_shape must be three positive integers in CHW order")
    torch = _optional_module("torch")
    destination = Path(output_path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    model.to(device)
    model.eval()
    example = torch.zeros((1, *input_shape), dtype=torch.float32, device=device)
    torch.onnx.export(
        model,
        example,
        destination,
        export_params=True,
        opset_version=ONNX_OPSET,
        do_constant_folding=True,
        input_names=[ONNX_INPUT_NAME],
        output_names=[ONNX_OUTPUT_NAME],
        dynamic_axes={
            ONNX_INPUT_NAME: {0: "batch"},
            ONNX_OUTPUT_NAME: {0: "batch"},
        },
        dynamo=False,
    )
    return destination


__all__ = [
    "ARCHITECTURES",
    "DEFAULT_FINE_TUNE_STAGES",
    "DatasetManifest",
    "DatasetManifestError",
    "DatasetRecord",
    "FineTuneStage",
    "ONNX_INPUT_NAME",
    "ONNX_OPSET",
    "ONNX_OUTPUT_NAME",
    "OptionalDependencyError",
    "PyTorchAdapterError",
    "available_architectures",
    "build_transforms",
    "class_weights",
    "classification_metrics",
    "create_cross_entropy",
    "create_dataloaders",
    "create_datasets",
    "create_model",
    "default_pretrained_weight",
    "evaluate_model",
    "export_onnx",
    "load_checkpoint",
    "load_dataset_manifest",
    "save_checkpoint",
    "seed_everything",
    "set_trainable_parameters",
    "train_model",
]
