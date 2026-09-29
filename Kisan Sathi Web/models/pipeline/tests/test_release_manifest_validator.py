import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from models.validate_release_manifest import ReleaseManifestError, validate_release_manifest


def test_release_manifest_rejects_deferred_cv_scope(tmp_path: Path):
    manifest = tmp_path / "approved-release.json"
    manifest.write_text(
        json.dumps(
            {
                "release_id": "rice-release-1",
                "status": "approved",
                "expires_at": "2099-01-01T00:00:00Z",
                "artifacts": {},
                "preprocessing": {},
                "crop_ids": ["rice"],
                "thresholds": {},
                "gates": {"field": True, "ood": True, "agronomist": True, "redistribution": True, "golden_parity": True},
                "rollback": {"release_id": "rice-release-0", "validated": True},
                "runtime": {},
            }
        ),
        encoding="utf-8",
    )
    authority = tmp_path / "APPROVED_RELEASES.json"
    authority.write_text(json.dumps({"scopes": {"release-cv": {"approved": False}}}), encoding="utf-8")
    with pytest.raises(ReleaseManifestError, match="model, labels, preprocess"):
        validate_release_manifest(manifest, authority)


def test_release_manifest_requires_authority_for_approval(tmp_path: Path):
    manifest = tmp_path / "approved-release.json"
    manifest.write_text(json.dumps({"status": "candidate"}), encoding="utf-8")
    authority = tmp_path / "APPROVED_RELEASES.json"
    authority.write_text(json.dumps({"scopes": {"release-cv": {"approved": False}}}), encoding="utf-8")
    with pytest.raises(ReleaseManifestError, match="release manifest is missing"):
        validate_release_manifest(manifest, authority, require_approved=True)
