"""Research-model prototype profile.

This module deliberately sits beside, rather than inside, the production CV
release path.  It exposes only downloaded artifacts whose source manifest
still verifies.  A verified download is enough to run a prototype; it is not
evidence of field validation, agronomist approval, or production readiness.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .downloader import verify
from .ontology import CANONICAL_CROPS, display_name
from .registry import CropDiseaseRegistry, ModelEntry
from .router import CONTROLLED_WARNING


PROTOTYPE_PROFILE_ID = "crop-disease-research-prototype"
PROTOTYPE_LIMITATION = (
    "Prototype only: these research checkpoints are not validated for Indian "
    "field conditions and must not be used as a diagnosis or treatment order."
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest(entry: ModelEntry, root: Path) -> tuple[dict[str, Any] | None, bool]:
    directory = root / entry.local_path
    manifest_path = directory / "download-manifest.json"
    if not manifest_path.is_file() or not verify(entry, directory):
        return None, False
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, False
    return document, True


def _model_record(entry: ModelEntry, root: Path, manifest: dict[str, Any], verified: bool) -> dict[str, Any]:
    directory = root / entry.local_path
    files = manifest.get("files", [])
    artifact_files = [
        row for row in files
        if isinstance(row, dict)
        and isinstance(row.get("path"), str)
        and Path(row["path"]).suffix.casefold() in {".onnx", ".keras", ".h5", ".safetensors"}
    ]
    return {
        "id": entry.id,
        "name": entry.name,
        "provider": entry.provider,
        "framework": entry.framework,
        "architecture": entry.architecture,
        "source_url": entry.source_url,
        "revision": entry.revision,
        "license": entry.license,
        "crops": list(entry.crops),
        "training_domain": entry.training_domain,
        "status": "prototype_available" if verified else "not_installed_or_invalid",
        "loadable": verified,
        "manifest": {
            "path": f"models/crop_disease/downloaded/{entry.local_path}/download-manifest.json",
            "sha256": _sha256(directory / "download-manifest.json") if verified else None,
            "file_count": len(files) if isinstance(files, list) else 0,
            "model_artifacts": artifact_files,
        },
    }


def build_prototype_status(registry: CropDiseaseRegistry, downloaded_root: Path) -> dict[str, Any]:
    """Build a safe public status document from the installed registry."""

    root = downloaded_root.resolve()
    records: list[dict[str, Any]] = []
    available_crops: set[str] = set()
    candidates = [entry for entry in registry.entries if entry.enabled and entry.status == "VERIFIED_DOWNLOADABLE"]
    for entry in candidates:
        manifest, verified = _manifest(entry, root)
        if manifest is None:
            manifest = {"files": []}
        record = _model_record(entry, root, manifest, verified)
        records.append(record)
        if verified:
            available_crops.update(entry.crops)

    records.sort(key=lambda item: item["id"])
    return {
        "schema_version": "1.0",
        "profile_id": PROTOTYPE_PROFILE_ID,
        "status": "prototype_available" if available_crops else "prototype_unavailable",
        "prototype_only": True,
        "production_approved": False,
        "activation_allowed": False,
        "diagnostic_use_allowed": False,
        "models": records,
        "model_count": sum(record["loadable"] for record in records),
        "supported_crops": [
            {"id": crop, "name": display_name(crop)}
            for crop in sorted(available_crops)
        ],
        "unsupported_crops": [
            {"id": crop, "name": display_name(crop)}
            for crop in sorted(set(CANONICAL_CROPS) - available_crops)
        ],
        "warnings": [CONTROLLED_WARNING, PROTOTYPE_LIMITATION],
    }


def build_prototype_profile(registry: CropDiseaseRegistry, downloaded_root: Path) -> dict[str, Any]:
    """Return the persisted profile shape used by the prototype validator."""

    return build_prototype_status(registry, downloaded_root)
