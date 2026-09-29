from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.cutover import CutoverBlocked, validate_evidence
from scripts.rollback import RollbackError, apply_rollback


def _target(release_id: str) -> dict:
    return {"release_id": release_id, "image_identity": "sha256:image", "schema_identity": "schema-v1", "model_identity": "model-v1", "data_identity": "snapshot-v1"}


def test_rollback_dry_run_and_atomic_apply(tmp_path: Path):
    state = tmp_path / "state.json"
    target = tmp_path / "target.json"
    state.write_text(json.dumps(_target("new")), encoding="utf-8")
    target.write_text(json.dumps(_target("previous")), encoding="utf-8")
    preview = apply_rollback(state, target, dry_run=True)
    assert preview["status"] == "dry_run"
    assert json.loads(state.read_text(encoding="utf-8"))["release_id"] == "new"
    applied = apply_rollback(state, target, dry_run=False)
    assert applied["status"] == "applied"
    assert json.loads(state.read_text(encoding="utf-8"))["release_id"] == "previous"


def test_rollback_rejects_incomplete_target(tmp_path: Path):
    state = tmp_path / "state.json"
    target = tmp_path / "target.json"
    state.write_text(json.dumps(_target("new")), encoding="utf-8")
    target.write_text(json.dumps({"release_id": "bad"}), encoding="utf-8")
    with pytest.raises(RollbackError):
        apply_rollback(state, target, dry_run=True)


def test_cutover_rejects_failing_machine_evidence(tmp_path: Path):
    results = tmp_path / "results.json"
    checksums = tmp_path / "checksums.json"
    results.write_text(json.dumps({"schema_version": 1, "status": "fail", "release_ready": False, "results": []}), encoding="utf-8")
    checksums.write_text(json.dumps({"schema_version": 1, "files": []}), encoding="utf-8")
    with pytest.raises(CutoverBlocked):
        validate_evidence(results, checksums, require_all=True)
