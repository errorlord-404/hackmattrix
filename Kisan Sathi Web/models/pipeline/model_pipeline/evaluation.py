"""Deterministic model evaluation helpers with no ML-framework dependency."""

from __future__ import annotations

import math
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from .contracts import PipelineError, load_json, sha256_file, write_json
from .packaging import gate_report, verify_candidate_bundle


def _check_labels(y_true: Sequence[int], y_pred: Sequence[int], class_count: int) -> None:
    if len(y_true) != len(y_pred) or not y_true:
        raise PipelineError("y_true and y_pred must be non-empty and have equal length")
    if class_count < 2:
        raise PipelineError("class_count must be at least two")
    if any(not isinstance(value, int) or value < 0 or value >= class_count for value in (*y_true, *y_pred)):
        raise PipelineError("class index is outside the declared class_count")


def confusion_matrix(y_true: Sequence[int], y_pred: Sequence[int], class_count: int) -> list[list[int]]:
    _check_labels(y_true, y_pred, class_count)
    matrix = [[0 for _ in range(class_count)] for _ in range(class_count)]
    for actual, predicted in zip(y_true, y_pred, strict=True):
        matrix[actual][predicted] += 1
    return matrix


def classification_metrics(
    y_true: Sequence[int], y_pred: Sequence[int], labels: Sequence[str]
) -> dict[str, object]:
    matrix = confusion_matrix(y_true, y_pred, len(labels))
    rows: list[dict[str, float | int | str]] = []
    for index, label in enumerate(labels):
        true_positive = matrix[index][index]
        false_negative = sum(matrix[index]) - true_positive
        false_positive = sum(row[index] for row in matrix) - true_positive
        support = true_positive + false_negative
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows.append(
            {
                "index": index,
                "label": label,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": support,
            }
        )
    total = len(y_true)
    accuracy = sum(matrix[i][i] for i in range(len(labels))) / total
    return {
        "sample_count": total,
        "accuracy": accuracy,
        "macro_precision": sum(float(row["precision"]) for row in rows) / len(rows),
        "macro_recall": sum(float(row["recall"]) for row in rows) / len(rows),
        "macro_f1": sum(float(row["f1"]) for row in rows) / len(rows),
        "per_class": rows,
        "confusion_matrix": matrix,
    }


def top_k_accuracy(y_true: Sequence[int], probabilities: Sequence[Sequence[float]], k: int) -> float:
    if len(y_true) != len(probabilities) or not y_true:
        raise PipelineError("labels and probabilities must be non-empty and aligned")
    width = len(probabilities[0])
    if not 1 <= k <= width or any(len(row) != width for row in probabilities):
        raise PipelineError("probability rows must have equal width and k must be valid")
    correct = 0
    for actual, row in zip(y_true, probabilities, strict=True):
        top = sorted(range(width), key=lambda index: row[index], reverse=True)[:k]
        correct += int(actual in top)
    return correct / len(y_true)


def expected_calibration_error(
    y_true: Sequence[int], probabilities: Sequence[Sequence[float]], bins: int = 15
) -> float:
    if bins < 2 or len(y_true) != len(probabilities) or not y_true:
        raise PipelineError("ECE requires aligned non-empty values and at least two bins")
    buckets: list[list[tuple[float, int]]] = [[] for _ in range(bins)]
    for actual, row in zip(y_true, probabilities, strict=True):
        predicted = max(range(len(row)), key=row.__getitem__)
        confidence = float(row[predicted])
        if not 0.0 <= confidence <= 1.0:
            raise PipelineError("probabilities must be between zero and one")
        bucket = min(int(confidence * bins), bins - 1)
        buckets[bucket].append((confidence, int(predicted == actual)))
    total = len(y_true)
    return sum(
        len(bucket) / total
        * abs(sum(conf for conf, _ in bucket) / len(bucket) - sum(ok for _, ok in bucket) / len(bucket))
        for bucket in buckets
        if bucket
    )


def multiclass_brier_score(y_true: Sequence[int], probabilities: Sequence[Sequence[float]]) -> float:
    if len(y_true) != len(probabilities) or not y_true:
        raise PipelineError("Brier score requires aligned non-empty values")
    width = len(probabilities[0])
    total = 0.0
    for actual, row in zip(y_true, probabilities, strict=True):
        if len(row) != width:
            raise PipelineError("probability rows must have equal width")
        total += sum((float(value) - float(index == actual)) ** 2 for index, value in enumerate(row))
    return total / len(y_true)


def binary_ood_auroc(known_scores: Iterable[float], ood_scores: Iterable[float]) -> float:
    """Return AUROC where larger scores mean more likely OOD."""

    known = [float(value) for value in known_scores]
    ood = [float(value) for value in ood_scores]
    if not known or not ood or any(not math.isfinite(value) for value in known + ood):
        raise PipelineError("OOD AUROC requires finite known and OOD scores")
    wins = 0.0
    for positive in ood:
        for negative in known:
            wins += 1.0 if positive > negative else 0.5 if positive == negative else 0.0
    return wins / (len(known) * len(ood))


def metric_delta(reference: dict[str, float], candidate: dict[str, float]) -> dict[str, float]:
    missing = sorted(set(reference) - set(candidate))
    if missing:
        raise PipelineError(f"candidate metrics are missing: {missing}")
    return {key: float(candidate[key]) - float(value) for key, value in reference.items()}


def evaluate_release_candidate(
    candidate_manifest: Path,
    *,
    dataset_manifest: Path | None = None,
    threshold_profile: Path | None = None,
    output: Path,
) -> dict[str, object]:
    """Emit deterministic release evidence without granting approval.

    This is intentionally a governance/evidence command. It verifies the
    immutable candidate bundle and records hashes and gate states, but it does
    not invent metrics, mark human reviews complete, or edit the approval list.
    """
    manifest_path = Path(candidate_manifest).resolve()
    manifest = verify_candidate_bundle(manifest_path)
    gates = gate_report(manifest)
    evidence: dict[str, object] = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "candidate_id": manifest["candidate_id"],
        "candidate_manifest": {
            "path": str(manifest_path),
            "sha256": sha256_file(manifest_path),
        },
        "artifacts": manifest["artifacts"],
        "dataset": None,
        "threshold_profile": None,
        "gates": gates,
        "release_ready": False,
        "approval_required": True,
        "approval_authority": "docs/APPROVED_RELEASES.json",
    }
    if dataset_manifest is not None:
        path = Path(dataset_manifest).resolve()
        if not path.is_file():
            raise PipelineError("dataset manifest does not exist")
        dataset = load_json(path, "dataset manifest")
        evidence["dataset"] = {"path": str(path), "sha256": sha256_file(path), "manifest_id": dataset.get("manifest_id")}
    if threshold_profile is not None:
        path = Path(threshold_profile).resolve()
        if not path.is_file():
            raise PipelineError("threshold profile does not exist")
        profile = load_json(path, "threshold profile")
        evidence["threshold_profile"] = {"path": str(path), "sha256": sha256_file(path), "profile_id": profile.get("profile_id")}
    eval_record = manifest["artifacts"]["evaluation"]
    eval_path = (manifest_path.parent / eval_record["path"]).resolve()
    try:
        evaluation = json.loads(eval_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PipelineError("evaluation artifact must be readable JSON") from exc
    if not isinstance(evaluation, dict):
        raise PipelineError("evaluation artifact must be a JSON object")
    evidence["evaluation_summary"] = {
        "declared": {key: evaluation[key] for key in ("metrics", "cohorts", "thresholds", "parity", "limitations") if key in evaluation},
        "artifact_sha256": eval_record["sha256"],
    }
    write_json(Path(output), evidence)
    return evidence
