"""Fine-tune a TensorFlow Hub classifier and keep its deployment contract.

The input uses ImageFolder-like ``train/<label>`` and ``val/<label>`` folders.
It is intentionally an evaluation/training utility, not a field diagnosis API.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from tfhub_models import BACKBONES, get_backbone


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--dataset", type=Path, required=True, help="Directory containing train/ and val/ label folders")
    result.add_argument("--output", type=Path, required=True, help="Saved Keras model directory")
    result.add_argument("--backbone", choices=sorted(BACKBONES), default="mobilenet_v3_large")
    result.add_argument("--epochs", type=int, default=8)
    result.add_argument(
        "--head-epochs",
        type=int,
        default=2,
        help="Warm-up epochs for the new disease head before optional backbone fine-tuning",
    )
    result.add_argument("--batch-size", type=int, default=16)
    result.add_argument(
        "--class-weight",
        choices=("balanced", "none"),
        default="balanced",
        help="Balance sparse disease labels by training-folder count; keep the validation distribution untouched.",
    )
    result.add_argument("--learning-rate", type=float, default=3e-4)
    result.add_argument(
        "--fine-tune-learning-rate",
        type=float,
        default=3e-5,
        help="Lower learning rate used after unfreezing a fine-tunable pretrained backbone",
    )
    result.add_argument("--seed", type=int, default=42)
    result.add_argument("--freeze-backbone", action="store_true", help="Train only the final classification head")
    return result


def training_stages(*, epochs: int, head_epochs: int, freeze_backbone: bool, fine_tune_supported: bool) -> tuple[int, int]:
    """Return head-warmup and backbone-fine-tuning epoch counts.

    Small agricultural datasets are particularly prone to erasing useful ImageNet
    features when every layer is made trainable from the first update.  We always
    warm up the newly random classification head first.  TF1 Hub feature-vector
    exports remain frozen because their variables are not trainable through
    ``hub.KerasLayer``.
    """
    if epochs < 1:
        raise ValueError("epochs must be at least 1")
    if head_epochs < 0:
        raise ValueError("head_epochs cannot be negative")
    if freeze_backbone or not fine_tune_supported:
        return epochs, 0
    warmup = min(max(head_epochs, 1), epochs)
    return warmup, epochs - warmup


def balanced_class_weights(class_counts: list[int]) -> dict[int, float]:
    """Inverse-frequency weights with mean sample contribution of one."""
    if not class_counts or any(count <= 0 for count in class_counts):
        raise ValueError("Every class must contain at least one training image")
    total = sum(class_counts)
    classes = len(class_counts)
    return {index: total / (classes * count) for index, count in enumerate(class_counts)}


def should_keep_fine_tuned(*, warmup_accuracy: float, fine_tuned_accuracy: float) -> bool:
    """Select fine-tuned weights only when they do not regress validation accuracy."""
    return fine_tuned_accuracy >= warmup_accuracy


def resolve_dataset_dirs(dataset: Path) -> tuple[Path, Path]:
    """Resolve training plus one unambiguous validation directory.

    Legacy demo data uses ``val/`` while the reviewed field-split builder uses
    ``validation/``. Supporting both prevents a manual rename that could blur
    the protected field-test boundary. Both names together are rejected.
    """
    train_dir = dataset / "train"
    candidates = [dataset / name for name in ("val", "validation") if (dataset / name).is_dir()]
    if not train_dir.is_dir() or not candidates:
        raise ValueError("Dataset must contain train/ and either val/ or validation/ directories.")
    if len(candidates) > 1:
        raise ValueError("Dataset contains both val/ and validation/ directories; use exactly one to avoid ambiguous evidence.")
    return train_dir, candidates[0]


def main() -> None:
    args = parser().parse_args()
    try:
        import tensorflow as tf
        import tensorflow_hub as hub
        import tf_keras as keras
    except ImportError as exc:
        raise SystemExit("Install ml/training/requirements-tfhub.txt in a dedicated training environment.") from exc

    tf.keras.utils.set_random_seed(args.seed)
    random.seed(args.seed)
    spec = get_backbone(args.backbone)
    if not args.freeze_backbone and not spec.fine_tune_supported:
        raise SystemExit(
            f"{spec.name} is published as a TF1 Hub feature vector and cannot be unfrozen through hub.KerasLayer. "
            "Use --freeze-backbone or select a TF2 candidate such as mobilenet_v3_large or efficientnet_v2_b0 for full TF Hub fine-tuning."
        )
    if args.fine_tune_learning_rate <= 0 or args.learning_rate <= 0:
        raise SystemExit("Learning rates must be greater than zero.")
    try:
        warmup_epochs, fine_tune_epochs = training_stages(
            epochs=args.epochs,
            head_epochs=args.head_epochs,
            freeze_backbone=args.freeze_backbone,
            fine_tune_supported=spec.fine_tune_supported,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    try:
        train_dir, val_dir = resolve_dataset_dirs(args.dataset)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    train = tf.keras.utils.image_dataset_from_directory(train_dir, image_size=(spec.image_size, spec.image_size), batch_size=args.batch_size, seed=args.seed)
    labels = list(train.class_names)
    val = tf.keras.utils.image_dataset_from_directory(val_dir, image_size=(spec.image_size, spec.image_size), batch_size=args.batch_size, shuffle=False)
    if list(val.class_names) != labels:
        raise SystemExit("Train and validation label folders must match in alphabetical order.")
    class_counts = [sum(1 for path in (train_dir / label).iterdir() if path.is_file()) for label in labels]
    class_weight = balanced_class_weights(class_counts) if args.class_weight == "balanced" else None
    augment = keras.Sequential([
        keras.layers.RandomFlip("horizontal"), keras.layers.RandomRotation(0.04),
        keras.layers.RandomContrast(0.12), keras.layers.RandomBrightness(0.10), keras.layers.RandomZoom(0.10),
    ], name="field_like_augmentation")
    # Start frozen even for MobileNetV3.  This preserves the pretrained visual
    # representation while the randomly initialized disease head learns its
    # scale, then permits a small, lower-rate fine-tuning stage.
    feature_extractor = hub.KerasLayer(spec.handle, trainable=False, name="tfhub_backbone")
    model = keras.Sequential([
        keras.layers.InputLayer(input_shape=(spec.image_size, spec.image_size, 3)),
        augment,
        keras.layers.Rescaling(1.0 / 255),
        feature_extractor,
        keras.layers.Dropout(0.25),
        keras.layers.Dense(len(labels), activation="softmax", name="disease_head"),
    ])
    model.compile(optimizer=keras.optimizers.Adam(args.learning_rate), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    train = train.prefetch(tf.data.AUTOTUNE)
    val = val.prefetch(tf.data.AUTOTUNE)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    callbacks = [keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3, restore_best_weights=True)]
    history = model.fit(train, validation_data=val, epochs=warmup_epochs, callbacks=callbacks, class_weight=class_weight)
    completed_warmup_epochs = len(history.history.get("loss", []))
    warmup_metrics = model.evaluate(val, return_dict=True, verbose=0)
    warmup_weights = model.get_weights()
    completed_fine_tune_epochs = 0
    selected_stage = "head_warmup"
    if fine_tune_epochs:
        feature_extractor.trainable = True
        # Keras requires recompilation after changing trainable variables.
        model.compile(
            optimizer=keras.optimizers.Adam(args.fine_tune_learning_rate),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )
        fine_tune_history = model.fit(
            train,
            validation_data=val,
            initial_epoch=warmup_epochs,
            epochs=args.epochs,
            callbacks=[keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3, restore_best_weights=True)],
            class_weight=class_weight,
        )
        completed_fine_tune_epochs = len(fine_tune_history.history.get("loss", []))
        for key, values in fine_tune_history.history.items():
            history.history.setdefault(key, []).extend(values)
        fine_tuned_metrics = model.evaluate(val, return_dict=True, verbose=0)
        if should_keep_fine_tuned(
            warmup_accuracy=float(warmup_metrics["accuracy"]),
            fine_tuned_accuracy=float(fine_tuned_metrics["accuracy"]),
        ):
            selected_stage = "backbone_fine_tune"
        else:
            model.set_weights(warmup_weights)
    metrics = model.evaluate(val, return_dict=True)
    model.save(str(args.output), save_format="tf")
    metadata = {
        "format": "tensorflow_saved_model", "backbone": spec.name, "tfhub_handle": spec.handle,
        "image_size": spec.image_size, "classes": labels, "normalization": "rgb / 255.0",
        "validation": {key: float(value) for key, value in metrics.items()}, "history": history.history,
        "seed": args.seed,
        "edge_intent": spec.edge_intent,
        "transfer_learning": {
            "pretrained_backbone": spec.handle,
            "planned_head_warmup_epochs": warmup_epochs,
            "planned_backbone_fine_tune_epochs": fine_tune_epochs,
            "completed_head_warmup_epochs": completed_warmup_epochs,
            "completed_backbone_fine_tune_epochs": completed_fine_tune_epochs,
            "selected_stage": selected_stage,
            "head_learning_rate": args.learning_rate,
            "fine_tune_learning_rate": args.fine_tune_learning_rate if fine_tune_epochs else None,
        },
        "training_distribution": {
            "class_counts": dict(zip(labels, class_counts, strict=True)),
            "class_weight_mode": args.class_weight,
            "class_weights": dict(zip(labels, class_weight.values(), strict=True)) if class_weight else None,
        },
    }
    (args.output / "kisansathi_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
