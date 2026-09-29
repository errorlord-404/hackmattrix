"""Validate quarantined model candidates without activating them.

This validator is intentionally separate from the production catalog validator:
candidate artifacts may be real and executable, but they are not releases. The
script checks the immutable source manifest, file sizes, SHA-256 digests, and
basic ONNX integrity while preserving the fail-closed activation policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class CandidateError(ValueError):
    """Raised when a candidate package is incomplete or inconsistent."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateError(f"unable to read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise CandidateError(f"{label} must be a JSON object")
    return value


def _validate_candidate(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    root = manifest_path.parent
    manifest = _load_json(manifest_path, "candidate source manifest")
    candidate_id = manifest.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id:
        raise CandidateError("candidate_id is required")
    if manifest.get("status") != "research_candidate_not_approved":
        raise CandidateError(f"{candidate_id} must remain research_candidate_not_approved")
    if manifest.get("activation_allowed") is not False or manifest.get("diagnostic_use_allowed") is not False:
        raise CandidateError(f"{candidate_id} must be disabled for activation and diagnosis")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise CandidateError(f"{candidate_id} has no artifact manifest")
    checked: list[dict[str, Any]] = []
    for relative_name, descriptor in artifacts.items():
        if not isinstance(relative_name, str) or not isinstance(descriptor, dict):
            raise CandidateError(f"{candidate_id} has an invalid artifact descriptor")
        path = (root / relative_name).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise CandidateError(f"artifact escapes candidate root: {relative_name}") from exc
        if not path.is_file():
            raise CandidateError(f"missing artifact: {relative_name}")
        expected_size = descriptor.get("size_bytes")
        expected_hash = descriptor.get("sha256")
        if not isinstance(expected_size, int) or not isinstance(expected_hash, str):
            raise CandidateError(f"artifact needs size_bytes and sha256: {relative_name}")
        actual_size = path.stat().st_size
        actual_hash = _sha256(path)
        if actual_size != expected_size:
            raise CandidateError(f"size mismatch for {relative_name}: {actual_size} != {expected_size}")
        if actual_hash.lower() != expected_hash.lower():
            raise CandidateError(f"SHA-256 mismatch for {relative_name}")
        checked.append({"path": relative_name, "size_bytes": actual_size, "sha256": actual_hash})

    onnx_files = [item["path"] for item in checked if item["path"].lower().endswith(".onnx")]
    onnx_status = "not_present"
    if onnx_files:
        try:
            import onnx  # type: ignore
        except ImportError:
            onnx_status = "not_checked_dependency_missing"
        else:
            for relative_name in onnx_files:
                try:
                    onnx.checker.check_model(str(root / relative_name))
                except Exception as exc:  # ONNX exposes several checker exception types.
                    raise CandidateError(f"ONNX integrity check failed for {relative_name}: {exc}") from exc
            onnx_status = "checked"

    return {
        "candidate_id": candidate_id,
        "status": manifest["status"],
        "activation_allowed": False,
        "diagnostic_use_allowed": False,
        "artifact_count": len(checked),
        "onnx_files": onnx_files,
        "onnx_integrity": onnx_status,
        "checked_artifacts": checked,
    }


def validate_candidates(candidates_root: Path, candidate_id: str | None = None) -> dict[str, Any]:
    candidates_root = candidates_root.resolve()
    index_path = candidates_root / "index.json"
    index = _load_json(index_path, "candidate index")
    entries = index.get("candidates")
    if not isinstance(entries, list):
        raise CandidateError("candidate index must contain a candidates array")
    selected = [entry for entry in entries if candidate_id is None or entry.get("candidate_id") == candidate_id]
    if candidate_id is not None and not selected:
        raise CandidateError(f"candidate is not registered: {candidate_id}")
    reports = []
    for entry in selected:
        if not isinstance(entry, dict) or not isinstance(entry.get("source_manifest"), str):
            raise CandidateError("candidate index entry has no source_manifest")
        report = _validate_candidate(candidates_root / entry["source_manifest"])
        if report["candidate_id"] != entry.get("candidate_id"):
            raise CandidateError("candidate index and source manifest IDs differ")
        if entry.get("activation_allowed") is not False or entry.get("diagnostic_use_allowed") is not False:
            raise CandidateError(f"candidate index enables {report['candidate_id']}")
        reports.append(report)
    return {"status": "valid_quarantined_candidates", "candidate_count": len(reports), "candidates": reports}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--candidates-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "models" / "candidates",
    )
    parser.add_argument("--candidate-id")
    args = parser.parse_args()
    try:
        print(json.dumps(validate_candidates(args.candidates_root, args.candidate_id), sort_keys=True))
    except CandidateError as exc:
        print(f"model candidates: FAIL: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
