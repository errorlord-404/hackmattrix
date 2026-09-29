import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.validate_model_candidates import CandidateError, validate_candidates


def _write_candidate(root: Path, *, enabled: bool = False) -> None:
    candidate = root / "demo"
    candidate.mkdir(parents=True)
    payload = b"candidate-bytes"
    artifact = candidate / "model.bin"
    artifact.write_bytes(payload)
    import hashlib

    manifest = {
        "candidate_id": "demo",
        "status": "research_candidate_not_approved",
        "activation_allowed": enabled,
        "diagnostic_use_allowed": False,
        "artifacts": {
            "model.bin": {
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        },
    }
    (candidate / "source-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "index.json").write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "candidate_id": "demo",
                        "source_manifest": "demo/source-manifest.json",
                        "activation_allowed": enabled,
                        "diagnostic_use_allowed": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_candidate_validation_checks_hashes_and_disabled_policy(tmp_path: Path):
    _write_candidate(tmp_path)
    report = validate_candidates(tmp_path)
    assert report["status"] == "valid_quarantined_candidates"
    assert report["candidates"][0]["activation_allowed"] is False


def test_candidate_validation_rejects_enabled_candidate(tmp_path: Path):
    _write_candidate(tmp_path, enabled=True)
    with pytest.raises(CandidateError, match="must be disabled"):
        validate_candidates(tmp_path)
