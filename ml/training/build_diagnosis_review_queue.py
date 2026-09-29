"""Build a local, consented crop-health review queue from farmer SQLite stores.

It deliberately creates review metadata only. It never copies an image, uploads
data, makes a label ground truth, or writes a train/validation split.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def store_fingerprint(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()[:16]


def field_fingerprint(source_store: str, field_id: str | None) -> str | None:
    if not field_id:
        return None
    return hashlib.sha256(f"{source_store}:{field_id}".encode("utf-8")).hexdigest()[:16]


def review_items(rows: Iterable[dict[str, Any]], *, source_store: str, include_local_paths: bool = False) -> list[dict[str, Any]]:
    """Return consented, label-bearing farmer feedback as *unreviewed* queue items."""
    items: list[dict[str, Any]] = []
    for row in rows:
        if not row["share_for_model_improvement"] or row["correctness"] not in {"confirmed", "corrected"} or not row["label"]:
            continue
        image_path = Path(row["image_path"])
        item = {
            "review_item_id": row["feedback_id"],
            "source_store": source_store,
            "diagnosis_id": row["request_id"],
            "crop": row["confirmed_crop"],
            "farmer_observed_label": row["label"],
            "feedback_type": row["correctness"],
            "feedback_created_at": row["created_at"],
            "field_group": field_fingerprint(source_store, row.get("field_id")),
            "capture_recorded_at": row.get("image_created_at"),
            "image": {
                "mime_type": row["mime_type"],
                "size_bytes": row["size_bytes"],
                "sha256": row["checksum"],
                "available_locally": image_path.is_file(),
            },
            "training_eligibility": "requires_agronomist_label_review_and_dataset_split",
        }
        if include_local_paths:
            item["image"]["local_path"] = str(image_path)
        items.append(item)
    return items


def load_store_items(path: Path, *, include_local_paths: bool) -> list[dict[str, Any]]:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """SELECT feedback.id AS feedback_id, feedback.request_id, feedback.confirmed_crop,
                      feedback.label, feedback.correctness, feedback.share_for_model_improvement,
                      feedback.created_at, requests.field_id, images.created_at AS image_created_at,
                      images.path AS image_path, images.mime_type, images.size_bytes, images.checksum
               FROM diagnosis_feedback AS feedback
               JOIN diagnosis_requests AS requests ON requests.id = feedback.request_id
               JOIN diagnosis_images AS images ON images.request_id = feedback.request_id
               ORDER BY feedback.created_at ASC"""
        ).fetchall()
    except sqlite3.OperationalError as exc:
        raise ValueError(f"{path} does not contain the diagnosis feedback schema: {exc}") from exc
    finally:
        connection.close()
    return review_items((dict(row) for row in rows), source_store=store_fingerprint(path), include_local_paths=include_local_paths)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--farm-db", type=Path, action="append", required=True, help="Explicit farmer SQLite file; repeat for each authorised store.")
    parser.add_argument("--output", type=Path, required=True, help="JSON review-queue manifest; it contains no image copy.")
    parser.add_argument("--include-local-paths", action="store_true", help="Include private local image paths for an authorised reviewer; omitted by default.")
    args = parser.parse_args()
    items: list[dict[str, Any]] = []
    for path in args.farm_db:
        if not path.is_file():
            raise SystemExit(f"Farm SQLite file does not exist: {path}")
        try:
            items.extend(load_store_items(path, include_local_paths=args.include_local_paths))
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    manifest = {
        "schema_version": "crop-health-review-queue-v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "contains_image_copies": False,
        "contains_local_paths": args.include_local_paths,
        "items": items,
        "next_required_step": "An authorised agronomist must review labels and a data steward must create field-disjoint train/validation/final-test/OOD splits before ML use.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"review_items": len(items), "output": str(args.output), "contains_image_copies": False}, indent=2))


if __name__ == "__main__":
    main()
