import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training"))

from validate_release_manifest import validate_manifest


def _manifest(root: Path, *, status: str = "demo_only_rejected_for_field_release") -> dict:
    model = root / "artifact.tflite"
    labels = root / "labels.json"
    model.write_bytes(b"model")
    labels.write_text(json.dumps(["healthy", "blight"]), encoding="utf-8")
    return {
        "release_id": "test-release",
        "status": status,
        "scope": {"labels": ["healthy", "blight"]},
        "artifact": {"path": "artifact.tflite", "sha256": hashlib.sha256(model.read_bytes()).hexdigest(), "size_bytes": model.stat().st_size},
        "labels": {"path": "labels.json", "sha256": hashlib.sha256(labels.read_bytes()).hexdigest()},
        "release_gates": {"independent_field_test": "missing", "unknown_ood_test": "missing", "agronomist_review": "missing"},
    }


def test_rejected_demo_manifest_checks_artifact_and_labels(tmp_path):
    report = validate_manifest(_manifest(tmp_path), tmp_path)
    assert report["approved_for_completed_output"] is False
    assert report["labels"]["values"] == ["healthy", "blight"]


def test_preflight_rejects_artifact_checksum_mismatch(tmp_path):
    manifest = _manifest(tmp_path)
    manifest["artifact"]["sha256"] = "mismatch"
    with pytest.raises(ValueError, match="SHA-256"):
        validate_manifest(manifest, tmp_path)


def test_approved_manifest_requires_all_evidence_gates(tmp_path):
    manifest = _manifest(tmp_path, status="approved_for_field_release")
    with pytest.raises(ValueError, match="incomplete release gate"):
        validate_manifest(manifest, tmp_path)
    manifest["release_gates"] = {"independent_field_test": "passed", "unknown_ood_test": "passed", "agronomist_review": "passed"}
    assert validate_manifest(manifest, tmp_path)["approved_for_completed_output"] is True
