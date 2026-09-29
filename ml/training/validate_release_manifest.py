"""Validate a local crop-health release manifest against its artifact files.

This preflight reports integrity and release-evidence state. It never upgrades a
manifest status and deliberately accepts a rejected demo manifest so its exact
artifact can still be demonstrated with review-only output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_repo_path(repo_root: Path, value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Manifest requires {field}")
    path = (repo_root / value).resolve()
    try:
        path.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"Manifest {field} must remain inside the repository root") from exc
    if not path.is_file():
        raise ValueError(f"Manifest {field} does not exist: {path}")
    return path


def validate_manifest(manifest: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    if not isinstance(manifest.get("release_id"), str) or not manifest["release_id"]:
        raise ValueError("Manifest requires a non-empty release_id")
    if manifest.get("status") not in {"demo_only_rejected_for_field_release", "blocked_pending_scope_and_evaluation", "approved_for_field_release"}:
        raise ValueError("Manifest status is not a supported release state")
    artifact = manifest.get("artifact")
    labels = manifest.get("labels")
    scope = manifest.get("scope")
    if not isinstance(artifact, dict) or not isinstance(labels, dict) or not isinstance(scope, dict):
        raise ValueError("Manifest requires artifact, labels, and scope mappings")
    artifact_path = _resolve_repo_path(repo_root, artifact.get("path"), "artifact.path")
    labels_path = _resolve_repo_path(repo_root, labels.get("path"), "labels.path")
    actual_hash = sha256_file(artifact_path)
    if artifact.get("sha256") != actual_hash:
        raise ValueError("Artifact SHA-256 does not match the manifest")
    if artifact.get("size_bytes") != artifact_path.stat().st_size:
        raise ValueError("Artifact size does not match the manifest")
    actual_labels = json.loads(labels_path.read_text(encoding="utf-8"))
    expected_labels = scope.get("labels")
    if not isinstance(actual_labels, list) or actual_labels != expected_labels:
        raise ValueError("Labels file does not exactly match scope.labels")
    label_hash = sha256_file(labels_path)
    gates = manifest.get("release_gates")
    if not isinstance(gates, dict):
        raise ValueError("Manifest requires release_gates")
    approved = manifest["status"] == "approved_for_field_release"
    if approved:
        if labels.get("sha256") != label_hash:
            raise ValueError("Approved manifest labels.sha256 does not match the labels file")
        required = ("independent_field_test", "unknown_ood_test", "agronomist_review")
        if any(gates.get(name) not in {"passed", "approved", True} for name in required):
            raise ValueError("Approved manifest has an incomplete release gate")
    return {
        "release_id": manifest["release_id"],
        "status": manifest["status"],
        "artifact": {"path": str(artifact_path), "sha256": actual_hash, "size_bytes": artifact_path.stat().st_size},
        "labels": {"path": str(labels_path), "sha256": label_hash, "values": actual_labels},
        "approved_for_completed_output": approved,
        "release_gates": gates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        import yaml

        manifest = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("Manifest must be a YAML mapping")
        report = validate_manifest(manifest, args.repo_root.resolve())
    except Exception as exc:
        raise SystemExit(f"Release manifest preflight failed: {exc}") from exc
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
