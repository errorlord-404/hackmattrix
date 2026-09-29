from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT))

from model_pipeline.contracts import PipelineError, sha256_file  # noqa: E402
from model_pipeline.packaging import (  # noqa: E402
    REQUIRED_ARTIFACTS,
    package_candidate,
    register_candidate,
    verify_candidate_bundle,
)


def _inputs(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    root = tmp_path / "build"
    root.mkdir()
    names = {
        "onnx": "model.onnx",
        "labels": "labels.json",
        "preprocess": "preprocess.json",
        "evaluation": "eval-report.json",
        "model_card": "MODEL_CARD.md",
        "license": "LICENSE.txt",
        "golden": "golden.json",
    }
    for index, name in enumerate(names.values(), start=1):
        (root / name).write_bytes(f"artifact-{index}-{name}".encode())
    return root, names


def _candidate() -> dict[str, object]:
    digest = "a" * 64
    return {
        "candidate_id": "rice-router-2026-09-18.1",
        "model": {
            "model_id": "rice-router-v1",
            "task": "crop_identification",
            "role": "crop_identifier",
            "crop_id": None,
            "training_status": "trained",
        },
        "provenance": {
            "run_id": "run-2026-09-18.1",
            "source_revision": "1234567",
            "training_code_revision": "7654321",
            "trained_at": "2026-09-18T08:00:00Z",
            "seed": 17,
        },
        "dataset": {
            "manifest_id": "field-data-v1",
            "manifest_sha256": digest,
            "split_strategy": "grouped",
            "group_keys": ["farm_id", "plant_id", "near_duplicate_cluster_id"],
        },
        "quantization": {
            "mode": "static-int8",
            "calibration": {
                "dataset_manifest_id": "calibration-v1",
                "dataset_manifest_sha256": "b" * 64,
                "sample_count": 320,
                "disjoint_from_test": True,
            },
        },
        "governance": {
            "dataset_license": {
                "identifier": "permission-record-17",
                "rights_holder": "Example cooperative",
                "training_allowed": True,
                "evaluation_allowed": True,
            },
            "consent": {
                "required": True,
                "lawful_basis": "documented consent",
                "scope_verified": True,
                "retention_policy": "project policy v1",
            },
            "agronomist_review": {"status": "pending", "crop_scope": ["rice"]},
            "redistribution": {"status": "pending", "scope": "ONNX release bundle"},
        },
        "rollback": {
            "previous_approved_release_id": None,
            "reason": "No prior approved release; activation remains blocked",
            "validated": False,
        },
        "gates": {
            "automated": {
                "dataset_contract": {"status": "passed", "evidence": "dataset report hash"}
            },
            "human": {},
        },
    }


def _package(tmp_path: Path) -> Path:
    source, artifacts = _inputs(tmp_path)
    return package_candidate(
        source,
        tmp_path / "bundle",
        candidate=_candidate(),
        artifacts=artifacts,
        created_at="2026-09-18T09:00:00Z",
    )


def test_packager_copies_and_hashes_every_required_artifact(tmp_path: Path) -> None:
    manifest_path = _package(tmp_path)
    manifest = verify_candidate_bundle(manifest_path)

    assert manifest["status"] == "candidate"
    assert manifest["immutable"] is True
    assert manifest["approval"] == {
        "activation_allowed": False,
        "approved": False,
        "authority": "docs/APPROVED_RELEASES.json",
    }
    assert set(manifest["artifacts"]) == set(REQUIRED_ARTIFACTS)
    for record in manifest["artifacts"].values():
        artifact = manifest_path.parent / record["path"]
        assert artifact.is_file()
        assert artifact.stat().st_size == record["size_bytes"]
        assert sha256_file(artifact) == record["sha256"]


def test_packager_refuses_unsafe_paths_and_existing_destination(tmp_path: Path) -> None:
    source, artifacts = _inputs(tmp_path)
    outside = tmp_path / "outside.onnx"
    outside.write_bytes(b"outside")
    unsafe = dict(artifacts)
    unsafe["onnx"] = "../outside.onnx"

    with pytest.raises(PipelineError, match="relative path|parent traversal"):
        package_candidate(source, tmp_path / "unsafe", candidate=_candidate(), artifacts=unsafe)

    destination = tmp_path / "existing"
    destination.mkdir()
    with pytest.raises(PipelineError, match="immutable"):
        package_candidate(source, destination, candidate=_candidate(), artifacts=artifacts)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda value: value["model"].update(training_status="untrained"), "untrained"),
        (lambda value: value.update(release_ready=True), "approval or activation"),
        (lambda value: value.update(candidate_id="demo-rice-router"), "placeholder, demo, or untrained"),
    ],
)
def test_packager_rejects_unsafe_status_or_claims(
    tmp_path: Path, mutation, message: str
) -> None:
    source, artifacts = _inputs(tmp_path)
    candidate = _candidate()
    mutation(candidate)

    with pytest.raises(PipelineError, match=message):
        package_candidate(source, tmp_path / "bundle", candidate=candidate, artifacts=artifacts)


def test_verification_detects_tampering_and_unhashed_files(tmp_path: Path) -> None:
    manifest_path = _package(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact = manifest_path.parent / manifest["artifacts"]["labels"]["path"]
    artifact.write_bytes(b"tampered")
    with pytest.raises(PipelineError, match="size|hash"):
        verify_candidate_bundle(manifest_path)

    # Restore by building a separate bundle, then ensure unlisted files fail too.
    other = tmp_path / "other"
    other.mkdir()
    source, artifacts = _inputs(other)
    clean_manifest = package_candidate(source, other / "bundle", candidate=_candidate(), artifacts=artifacts)
    (clean_manifest.parent / "unhashed.txt").write_text("not in manifest", encoding="utf-8")
    with pytest.raises(PipelineError, match="unhashed"):
        verify_candidate_bundle(clean_manifest)


def test_registration_only_stages_and_reports_missing_gates(tmp_path: Path) -> None:
    manifest_path = _package(tmp_path)

    report = register_candidate(manifest_path, tmp_path / "models")

    destination = tmp_path / "models" / "candidates" / _candidate()["candidate_id"]
    assert Path(report["registration_path"]) == destination
    assert Path(report["manifest_path"]) == destination / "manifest.json"
    assert report["registration_status"] == "staged_candidate"
    assert report["approved"] is False
    assert report["activation_allowed"] is False
    assert report["promotion_performed"] is False
    assert "static_int8_calibration" in report["missing_automated_gates"]
    assert "agronomist_review" in report["missing_human_gates"]
    assert report["all_gates_complete"] is False
    verify_candidate_bundle(destination / "manifest.json")

    with pytest.raises(PipelineError, match="immutable"):
        register_candidate(manifest_path, tmp_path / "models")
