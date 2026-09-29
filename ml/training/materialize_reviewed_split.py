"""Materialize an authorised reviewed split into image folders for training.

The caller must explicitly confirm data-steward authority. This command verifies
each source checksum and refuses a non-empty destination to avoid accidental
mixing or overwriting of datasets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_label(label: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")
    if not value:
        raise ValueError("Agronomist label cannot be empty after safe folder normalization")
    return value


def materialize_split(manifest: dict[str, Any], output: Path) -> dict[str, int]:
    """Copy only integrity-checked reviewed images into partition/label folders."""
    if manifest.get("schema_version") != "crop-health-field-split-v1":
        raise ValueError("Split manifest schema_version must be crop-health-field-split-v1")
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Destination must not already contain files: {output}")
    counts: dict[str, int] = {}
    for partition, items in manifest.get("partitions", {}).items():
        if partition not in {"train", "validation", "field_test"} or not isinstance(items, list):
            raise ValueError("Split manifest partitions are invalid")
        for item in items:
            image = item.get("image", {})
            source_value = image.get("local_path")
            if not isinstance(source_value, str) or not source_value:
                raise ValueError(f"{item.get('review_item_id')} lacks a locally authorised image path")
            source = Path(source_value)
            if not source.is_file():
                raise ValueError(f"Source image is missing: {source}")
            if sha256_file(source) != image.get("sha256"):
                raise ValueError(f"Source image checksum changed: {source}")
            suffix = source.suffix.lower() if source.suffix else ".img"
            destination = output / partition / safe_label(str(item.get("agronomist_label", ""))) / f"{item['review_item_id']}{suffix}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            counts[partition] = counts.get(partition, 0) + 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confirm-authorised-data-steward", action="store_true", help="Required acknowledgement before local copies are created.")
    args = parser.parse_args()
    if not args.confirm_authorised_data_steward:
        raise SystemExit("Refusing to copy farmer images without --confirm-authorised-data-steward")
    try:
        manifest = json.loads(args.split_manifest.read_text(encoding="utf-8"))
        counts = materialize_split(manifest, args.output)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"Reviewed split could not be materialized: {exc}") from exc
    print(json.dumps({"copied": counts, "output": str(args.output), "next_required_step": "Train only on train, tune only on validation, and keep field_test untouched until the candidate is frozen."}, indent=2))


if __name__ == "__main__":
    main()
