import hashlib
import json
from pathlib import Path

import pytest

from app.services.vision_release import VisionReleaseUnavailable, load_approved_descriptor


def _release_fixture(root: Path, approved: bool = True):
    manifest_dir = root / "models" / "manifests"
    manifest_dir.mkdir(parents=True)
    artifacts_dir = manifest_dir / "artifacts"
    artifacts_dir.mkdir()
    artifacts = {}
    for role, suffix in (("model", ".onnx"), ("labels", ".json"), ("preprocess", ".json"), ("golden", ".json")):
        path = artifacts_dir / f"{role}{suffix}"
        data = role.encode("utf-8")
        path.write_bytes(data)
        artifacts[role] = {"path": f"artifacts/{path.name}", "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
    manifest = {
        "release_id": "rice-release-1", "status": "approved", "expires_at": "2099-01-01T00:00:00Z",
        "artifacts": artifacts, "preprocessing": {"version": "preprocess-v1", "width": 224},
        "crop_ids": ["rice"], "thresholds": {"min_confidence": 0.8},
        "gates": {"field": True, "ood": True, "agronomist": True, "redistribution": True, "golden_parity": True},
        "rollback": {"release_id": "rice-release-0", "validated": True}, "runtime": {"webgpu": False},
    }
    manifest_path = manifest_dir / "approved-release.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    approvals = root / "docs"
    approvals.mkdir()
    approval_path = approvals / "APPROVED_RELEASES.json"
    approval_path.write_text(json.dumps({"scopes": {"release-cv": {"approved": approved, "release_ready": approved, "activation_allowed": approved, "approved_artifacts": {"release_id": "rice-release-1", "manifest": {"path": "models/manifests/approved-release.json", "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()}}}}}), encoding="utf-8")
    return manifest_path, approval_path


def test_descriptor_is_signed_only_for_approved_release(tmp_path: Path):
    manifest, approval = _release_fixture(tmp_path)
    descriptor = load_approved_descriptor(manifest, approval, "test-secret")
    assert descriptor["activationAllowed"] is True
    assert len(descriptor["signature"]) == 64


def test_descriptor_fails_closed_without_authority(tmp_path: Path):
    manifest, approval = _release_fixture(tmp_path, approved=False)
    with pytest.raises(VisionReleaseUnavailable):
        load_approved_descriptor(manifest, approval, "test-secret")
