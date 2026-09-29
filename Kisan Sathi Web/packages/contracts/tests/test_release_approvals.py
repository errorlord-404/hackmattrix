import copy
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TARGET = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(TARGET / "scripts"))

from validate_approved_releases import (  # noqa: E402
    ApprovalError,
    canonical_digest,
    load_record,
    validate_record,
)


RECORD = TARGET / "docs" / "APPROVED_RELEASES.json"
VALIDATOR = TARGET / "scripts" / "validate_approved_releases.py"


def _copy_record(tmp_path: Path) -> tuple[Path, dict]:
    root = tmp_path / "standalone"
    (root / "docs").mkdir(parents=True)
    shutil.copy2(RECORD, root / "docs" / RECORD.name)
    shutil.copytree(TARGET / "models" / "placeholders", root / "models" / "placeholders")
    record_path = root / "docs" / RECORD.name
    return record_path, load_record(record_path)


def _write_record(record_path: Path, record: dict) -> None:
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def test_development_scope_approves_only_exact_verified_identities() -> None:
    report = validate_record(RECORD, scope="development-dependencies")

    assert report["scope"] == "development-dependencies"
    assert report["status"] == "approved_for_development"
    assert report["release_cv_approved"] is False
    assert report["package_versions"] == {
        "PyJWT": "2.14.0",
        "onnxruntime-web": "1.30.0",
        "@playwright/test": "1.63.0",
    }
    assert report["playwright_image"] == (
        "mcr.microsoft.com/playwright:v1.63.0@"
        "sha256:eff16c30e6f3f4af0a03fa4b706120d5e9b0891c344a27d64559aff5900a4a27"
    )
    assert re.fullmatch(r"[0-9a-f]{64}", report["approval_record_digest"])


def test_release_cv_scope_is_explicitly_unapproved() -> None:
    with pytest.raises(ApprovalError, match="release-cv.*unapproved|release.*deferred"):
        validate_record(RECORD, scope="release-cv")


def test_require_all_and_production_fail_closed() -> None:
    for scope in ("all", "production"):
        with pytest.raises(ApprovalError, match="release-cv.*unapproved|release.*deferred"):
            validate_record(RECORD, scope=scope)


def test_development_cli_prints_stable_digest() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--record",
            str(RECORD),
            "--scope",
            "development-dependencies",
            "--print-digest",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert re.search(r'"approval_record_digest": "[0-9a-f]{64}"', result.stdout)


@pytest.mark.parametrize("flag", ["--require-all", "--production"])
def test_release_cli_flags_fail_closed(flag: str) -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--record", str(RECORD), flag],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "release-cv" in result.stdout


def test_record_has_reviewer_evidence_and_development_review_results() -> None:
    record = load_record(RECORD)
    assert record["review"]["reviewer"]
    assert record["review"]["reviewer_evidence"]
    assert record["scopes"]["development-dependencies"]["status"] == "approved_for_development"
    for package in record["scopes"]["development-dependencies"]["packages"]:
        assert package["license_review"]["status"] == "passed"
        assert package["install_script_review"]["status"] == "passed"


def test_mutable_playwright_tag_is_rejected(tmp_path: Path) -> None:
    record_path, record = _copy_record(tmp_path)
    record["scopes"]["development-dependencies"]["browser_image"]["reference"] = (
        "mcr.microsoft.com/playwright:latest"
    )
    _write_record(record_path, record)

    with pytest.raises(ApprovalError, match="immutable|digest|mutable"):
        validate_record(record_path, scope="development-dependencies")


def test_changed_dependency_identity_or_image_digest_is_rejected(tmp_path: Path) -> None:
    record_path, record = _copy_record(tmp_path)
    record["scopes"]["development-dependencies"]["packages"][0]["version"] = "2.13.0"
    _write_record(record_path, record)

    with pytest.raises(ApprovalError, match="PyJWT|version|identity"):
        validate_record(record_path, scope="development-dependencies")

    record_path, record = _copy_record(tmp_path / "image")
    record["scopes"]["development-dependencies"]["browser_image"]["digest"] = "sha256:" + "0" * 64
    _write_record(record_path, record)

    with pytest.raises(ApprovalError, match="digest|image"):
        validate_record(record_path, scope="development-dependencies")


def test_missing_placeholder_hash_is_rejected(tmp_path: Path) -> None:
    record_path, record = _copy_record(tmp_path)
    del record["scopes"]["release-cv"]["quarantined_compatibility_assets"][0]["artifacts"]["model"]["sha256"]
    _write_record(record_path, record)

    with pytest.raises(ApprovalError, match="sha256|hash"):
        validate_record(record_path, scope="development-dependencies")


def test_altered_placeholder_artifact_is_rejected(tmp_path: Path) -> None:
    record_path, _ = _copy_record(tmp_path)
    model = record_path.parents[1] / "models" / "placeholders" / "stub-disease-tomato" / "model.onnx"
    model.write_bytes(model.read_bytes() + b"tampered")

    with pytest.raises(ApprovalError, match="size|SHA-256|hash"):
        validate_record(record_path, scope="development-dependencies")


def test_structural_placeholder_cannot_be_presented_as_approved(tmp_path: Path) -> None:
    record_path, record = _copy_record(tmp_path)
    release_cv = record["scopes"]["release-cv"]
    release_cv["status"] = "approved"
    release_cv["approved"] = True
    release_cv["release_ready"] = True
    _write_record(record_path, record)

    with pytest.raises(ApprovalError, match="placeholder|release-cv|approved"):
        validate_record(record_path, scope="development-dependencies")


def test_stale_development_review_is_rejected(tmp_path: Path) -> None:
    record_path, record = _copy_record(tmp_path)
    record["review"]["expires_at"] = "2020-01-01T00:00:00Z"
    _write_record(record_path, record)

    with pytest.raises(ApprovalError, match="expired|stale"):
        validate_record(record_path, scope="development-dependencies")


def test_digest_is_stable_for_reformatted_record() -> None:
    record = load_record(RECORD)
    reformatted = json.loads(json.dumps(record, separators=(",", ":")))
    assert canonical_digest(record) == canonical_digest(reformatted)


def test_release_cv_records_quarantined_hashes_but_no_approved_artifacts() -> None:
    release_cv = load_record(RECORD)["scopes"]["release-cv"]
    assert release_cv["approved"] is False
    assert release_cv["release_ready"] is False
    assert release_cv["approved_artifacts"] is None
    assert release_cv["quarantined_compatibility_assets"]
    assert all(asset["approved"] is False for asset in release_cv["quarantined_compatibility_assets"])
    assert all(asset["activation_allowed"] is False for asset in release_cv["quarantined_compatibility_assets"])
