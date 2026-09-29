"""Create a field-disjoint split manifest from agronomist-reviewed queue items.

This is intentionally an offline data-steward command. It copies no images and
will not accept farmer feedback as a training label without an explicit expert
approval record.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any


PARTITIONS = ("train", "validation", "field_test")


def approved_items(queue: dict[str, Any], review: dict[str, Any]) -> list[dict[str, Any]]:
    """Join review decisions to queue items while preserving field boundaries."""
    if queue.get("schema_version") != "crop-health-review-queue-v1":
        raise ValueError("Review queue schema_version must be crop-health-review-queue-v1")
    if review.get("schema_version") != "crop-health-expert-review-v1":
        raise ValueError("Expert review schema_version must be crop-health-expert-review-v1")
    decisions = {item.get("review_item_id"): item for item in review.get("items", []) if isinstance(item, dict)}
    selected: list[dict[str, Any]] = []
    for item in queue.get("items", []):
        decision = decisions.get(item.get("review_item_id"))
        if not decision or decision.get("decision") != "approved":
            continue
        label = decision.get("agronomist_label")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"Approved item {item.get('review_item_id')} requires a non-empty agronomist_label")
        if not item.get("field_group"):
            raise ValueError(f"Approved item {item.get('review_item_id')} lacks an anonymized field group")
        image = item.get("image")
        if not isinstance(image, dict) or not image.get("available_locally"):
            raise ValueError(f"Approved item {item.get('review_item_id')} has no locally available image")
        selected.append({**item, "agronomist_label": label.strip(), "expert_review_id": decision.get("expert_review_id")})
    return selected


def field_disjoint_split(items: list[dict[str, Any]], *, seed: int = 42) -> dict[str, list[dict[str, Any]]]:
    """Assign each anonymous field group to exactly one partition."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(item["field_group"], []).append(item)
    if len(groups) < len(PARTITIONS):
        raise ValueError("At least three distinct field groups are required for train, validation, and field_test.")
    group_ids = sorted(groups)
    random.Random(seed).shuffle(group_ids)
    split = {partition: [] for partition in PARTITIONS}
    for index, group_id in enumerate(group_ids):
        split[PARTITIONS[index % len(PARTITIONS)]].extend(groups[group_id])
    labels = sorted({item["agronomist_label"] for item in items})
    missing = {
        partition: sorted(set(labels) - {item["agronomist_label"] for item in partition_items})
        for partition, partition_items in split.items()
    }
    missing = {partition: labels for partition, labels in missing.items() if labels}
    if missing:
        formatted = "; ".join(f"{partition}: {', '.join(labels)}" for partition, labels in missing.items())
        raise ValueError(f"Field-disjoint assignment leaves labels absent from a partition ({formatted}). Collect more reviewed field groups.")
    return split


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-queue", type=Path, required=True)
    parser.add_argument("--expert-review", type=Path, required=True, help="JSON approval record, never an unreviewed farmer-feedback file.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        queue = json.loads(args.review_queue.read_text(encoding="utf-8"))
        review = json.loads(args.expert_review.read_text(encoding="utf-8"))
        split = field_disjoint_split(approved_items(queue, review), seed=args.seed)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"Field split could not be built: {exc}") from exc
    manifest = {
        "schema_version": "crop-health-field-split-v1",
        "seed": args.seed,
        "contains_image_copies": False,
        "partitions": split,
        "counts": {partition: len(items) for partition, items in split.items()},
        "label_counts": {partition: dict(Counter(item["agronomist_label"] for item in items)) for partition, items in split.items()},
        "next_required_step": "A data steward may materialize these approved, field-disjoint entries in a protected dataset location. Hold field_test untouched until the candidate is frozen; build a separate unknown/OOD challenge set.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"counts": manifest["counts"], "contains_image_copies": False}, indent=2))


if __name__ == "__main__":
    main()
