"""Validate the hierarchical crop-model catalog without activating research entries."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class CatalogError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_path(root: Path, value: str, field: str) -> Path:
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise CatalogError(f"{field} escapes the model directory") from exc
    return candidate


def _validate_artifact(root: Path, artifact: dict[str, Any], field: str, required: bool) -> None:
    path_value = artifact.get("path")
    hash_value = artifact.get("sha256")
    size_value = artifact.get("size_bytes")
    if not required and path_value is None and hash_value is None and size_value is None:
        return
    if not isinstance(path_value, str) or not isinstance(hash_value, str) or not isinstance(size_value, int):
        raise CatalogError(f"{field} must have path, sha256, and size_bytes for an approved model")
    path = _safe_path(root, path_value, field)
    if not path.is_file():
        raise CatalogError(f"{field} does not exist: {path_value}")
    if path.stat().st_size != size_value:
        raise CatalogError(f"{field} size does not match catalog")
    if _sha256(path) != hash_value.lower():
        raise CatalogError(f"{field} SHA-256 does not match catalog")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"unable to read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise CatalogError(f"{label} must be a JSON object")
    return value


def _validate_schema(document: dict[str, Any], schema: dict[str, Any], label: str) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(document), key=lambda error: list(error.path))
    if errors:
        raise CatalogError(f"{label} schema validation failed: " + "; ".join(error.message for error in errors))


def validate_catalog(
    catalog_path: Path,
    *,
    require_approved: bool = False,
    crop: str | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    catalog_path = catalog_path.resolve()
    root = catalog_path.parent
    catalog = _load_json(catalog_path, "catalog")
    schema = _load_json(root / "catalog.schema.json", "catalog schema")
    sources = _load_json(root / "research-sources.json", "research sources")
    source_schema = _load_json(root / "research-sources.schema.json", "research sources schema")
    _validate_schema(catalog, schema, "catalog")
    _validate_schema(sources, source_schema, "research sources")

    source_ids = [entry["source_id"] for entry in sources["sources"]]
    if len(source_ids) != len(set(source_ids)):
        raise CatalogError("research source_id values must be unique")
    known_sources = set(source_ids)

    models = catalog["models"]
    ids = [entry["model_id"] for entry in models]
    if len(ids) != len(set(ids)):
        raise CatalogError("model_id values must be unique")
    identifiers = [entry for entry in models if entry["role"] == "crop_identifier"]
    if len(identifiers) != 1:
        raise CatalogError("catalog must contain exactly one crop_identifier entry")
    identifier = identifiers[0]
    if identifier["crop"] != "multi_crop" or identifier["task"] != "crop_identification":
        raise CatalogError("crop_identifier must use multi_crop and crop_identification")

    specialists = [entry for entry in models if entry["role"] == "disease_specialist"]
    coverage = catalog["coverage"]["crop_ids"]
    specialist_crops = [entry["crop"] for entry in specialists]
    if len(specialist_crops) != len(set(specialist_crops)):
        raise CatalogError("each crop may have only one disease_specialist slot in a catalog version")
    missing_slots = sorted(set(coverage) - set(specialist_crops))
    extra_slots = sorted(set(specialist_crops) - set(coverage))
    if missing_slots or extra_slots:
        raise CatalogError(f"specialist coverage mismatch: missing={missing_slots}, extra={extra_slots}")

    selected = [
        entry
        for entry in models
        if (crop is None or entry["crop"] == crop) and (role is None or entry["role"] == role)
    ]
    if crop is not None and not selected:
        raise CatalogError(f"no catalog entry exists for crop: {crop}")
    for entry in models:
        if entry["role"] == "disease_specialist" and entry["task"] != "crop_disease_screening":
            raise CatalogError(f"specialist has incompatible task: {entry['model_id']}")
        unknown_sources = sorted(set(entry["research"]["source_ids"]) - known_sources)
        if unknown_sources:
            raise CatalogError(f"unknown research sources for {entry['model_id']}: {unknown_sources}")
        approved = entry["status"] == "approved"
        artifacts = entry["artifacts"]
        if approved:
            if entry["research"]["readiness"] != "release_evidence" or entry["research"]["field_evidence"] != "passed":
                raise CatalogError(f"approved model lacks release and field evidence: {entry['model_id']}")
            if not artifacts["release_manifest"]:
                raise CatalogError(f"approved model has no release manifest: {entry['model_id']}")
            _validate_artifact(root, artifacts["model"], f"{entry['model_id']}.model", True)
            _validate_artifact(root, artifacts["labels"], f"{entry['model_id']}.labels", True)
            if artifacts["model"]["size_bytes"] > entry["runtime"]["target_max_size_mb"] * 1024 * 1024:
                raise CatalogError(f"approved model exceeds its declared client size target: {entry['model_id']}")
            manifest = _safe_path(root, artifacts["release_manifest"], f"{entry['model_id']}.release_manifest")
            if not manifest.is_file():
                raise CatalogError(f"approved release manifest does not exist: {artifacts['release_manifest']}")
        else:
            if any(artifacts[key].get(value) is not None for key in ("model", "labels") for value in ("path", "sha256", "size_bytes")):
                raise CatalogError(f"non-approved model must not claim distributable artifacts: {entry['model_id']}")
    approved_count = sum(entry["status"] == "approved" for entry in selected)
    approved_identifier = identifier["status"] == "approved"
    if require_approved:
        if not approved_identifier:
            raise CatalogError("no approved crop identifier is available")
        if crop is not None and not any(entry["status"] == "approved" for entry in specialists if entry["crop"] == crop):
            raise CatalogError(f"no approved disease specialist is available for crop: {crop}")
        if crop is None and not any(entry["status"] == "approved" for entry in specialists):
            raise CatalogError("no approved disease specialist is available")
    status_counts = {
        status: sum(entry["status"] == status for entry in selected)
        for status in ("missing", "research_candidate", "pending_review", "approved", "revoked")
    }
    return {
        "catalog_id": catalog["catalog_id"],
        "model_count": len(models),
        "selected_count": len(selected),
        "approved_count": approved_count,
        "approved_identifier": approved_identifier,
        "coverage_count": len(coverage),
        "research_source_count": len(source_ids),
        "status_counts": status_counts,
        "status": catalog["status"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=Path(__file__).resolve().parents[1] / "models" / "catalog.json")
    parser.add_argument("--crop")
    parser.add_argument("--role", choices=("crop_identifier", "disease_specialist"))
    parser.add_argument("--require-approved", action="store_true")
    args = parser.parse_args()
    try:
        report = validate_catalog(args.catalog, require_approved=args.require_approved, crop=args.crop, role=args.role)
    except CatalogError as exc:
        print(f"model catalog: FAIL: {exc}")
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
