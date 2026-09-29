"""Evaluate a TFLite crop-health candidate with release-relevant metrics.

The evaluator deliberately separates a supported-class field test from an
unknown/OOD challenge directory. It reports evidence only; it cannot write an
approved release manifest or turn a model into a diagnosis service.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def image_files(root: Path) -> list[Path]:
    """Return only image payloads, excluding dataset manifests and review notes."""
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)


def accepted_prediction(scores: list[float], minimum_score: float, minimum_margin: float) -> tuple[int | None, float, float]:
    """Return accepted top index, score, and top-one/top-two margin."""
    if not scores:
        raise ValueError("Model returned no class scores")
    if any(score < 0 or score > 1 for score in scores) or not 0.98 <= sum(scores) <= 1.02:
        raise ValueError("Model outputs must be probability scores summing approximately to one")
    ranked = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
    top = ranked[0]
    margin = scores[top] - (scores[ranked[1]] if len(ranked) > 1 else 0.0)
    return (top if scores[top] >= minimum_score and margin >= minimum_margin else None, scores[top], margin)


def classification_report(labels: list[str], expected_predictions: Iterable[tuple[int, int | None]]) -> dict[str, Any]:
    """Compute compact confusion, precision, recall, macro-F1, and coverage."""
    matrix = [[0 for _ in labels] for _ in labels]
    expected_counts = [0 for _ in labels]
    rejected = total = correct = 0
    for expected, predicted in expected_predictions:
        if not 0 <= expected < len(labels):
            raise ValueError("Expected label index is outside the label list")
        total += 1
        expected_counts[expected] += 1
        if predicted is None:
            rejected += 1
            continue
        matrix[expected][predicted] += 1
        correct += int(expected == predicted)
    per_class: dict[str, dict[str, float | int]] = {}
    f1_values: list[float] = []
    for index, label in enumerate(labels):
        tp = matrix[index][index]
        # A rejected supported image is still a false negative for release
        # recall/F1. Coverage is reported separately so it cannot hide here.
        fn = expected_counts[index] - tp
        fp = sum(row[index] for row in matrix) - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": expected_counts[index]}
        f1_values.append(f1)
    accepted = total - rejected
    return {
        "samples": total,
        "accepted_samples": accepted,
        "rejected_supported_samples": rejected,
        "accepted_accuracy": correct / accepted if accepted else 0.0,
        "coverage": accepted / total if total else 0.0,
        "macro_f1": sum(f1_values) / len(f1_values) if f1_values else 0.0,
        "per_class": per_class,
        "confusion_matrix": {"labels": labels, "rows_expected_columns_predicted": matrix},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True, help="Field-held-out root with one directory per supported label")
    parser.add_argument("--unknown-dataset", type=Path, help="Challenge directory containing non-target/OOD images in any nested layout")
    parser.add_argument("--minimum-score", type=float, default=0.70)
    parser.add_argument("--minimum-margin", type=float, default=0.15)
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    if not 0 <= args.minimum_score <= 1 or not 0 <= args.minimum_margin <= 1:
        raise SystemExit("Acceptance thresholds must be between zero and one.")
    try:
        import numpy as np
        import tensorflow as tf
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("Install ml/training/requirements-tfhub.txt and Pillow.") from exc
    labels = json.loads(args.labels.read_text(encoding="utf-8"))
    if not isinstance(labels, list) or len(labels) < 2 or not all(isinstance(label, str) and label for label in labels):
        raise SystemExit("Labels must be a JSON list containing at least two non-empty strings.")
    interpreter = tf.lite.Interpreter(model_path=str(args.model))
    interpreter.allocate_tensors()
    input_info, output_info = interpreter.get_input_details()[0], interpreter.get_output_details()[0]
    _, height, width, _ = input_info["shape"]

    def predict(path: Path) -> tuple[int | None, float, float]:
        array = np.asarray(Image.open(path).convert("RGB").resize((width, height)), dtype=np.float32)[None, ...]
        scale, zero_point = input_info["quantization"]
        if input_info["dtype"] != np.float32:
            if not scale:
                raise ValueError("Quantized input does not expose a scale")
            array = np.clip(np.round(array / scale + zero_point), 0, 255).astype(input_info["dtype"])
        interpreter.set_tensor(input_info["index"], array)
        interpreter.invoke()
        output = interpreter.get_tensor(output_info["index"])[0].astype("float32")
        out_scale, out_zero = output_info["quantization"]
        if output_info["dtype"] != np.float32:
            if not out_scale:
                raise ValueError("Quantized output does not expose a scale")
            output = (output - out_zero) * out_scale
        if len(output) != len(labels):
            raise ValueError("Model output count does not match labels")
        return accepted_prediction(output.tolist(), args.minimum_score, args.minimum_margin)

    expected_predictions: list[tuple[int, int | None]] = []
    for expected, label in enumerate(labels):
        label_dir = args.dataset / label
        if not label_dir.is_dir():
            raise SystemExit(f"Field dataset is missing label directory: {label_dir}")
        for path in image_files(label_dir):
            predicted, _, _ = predict(path)
            expected_predictions.append((expected, predicted))
    report = classification_report(labels, expected_predictions)
    report["acceptance_policy"] = {"minimum_score": args.minimum_score, "minimum_margin": args.minimum_margin}
    report["model"] = str(args.model)
    report["labels"] = str(args.labels)
    # Persist split provenance so a saved report cannot be reused as evidence
    # for a different validation, external, or field partition.
    report["dataset"] = str(args.dataset)
    if args.unknown_dataset:
        outcomes = [predict(path) for path in image_files(args.unknown_dataset)]
        rejected = sum(prediction is None for prediction, _, _ in outcomes)
        report["unknown_ood"] = {
            "dataset": str(args.unknown_dataset),
            "samples": len(outcomes),
            "rejected": rejected,
            "true_rejection_rate": rejected / len(outcomes) if outcomes else 0.0,
        }
    else:
        report["unknown_ood"] = {"status": "not_evaluated"}
    encoded = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
