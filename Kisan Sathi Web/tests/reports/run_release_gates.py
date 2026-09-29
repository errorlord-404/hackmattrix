from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _approval_digest(path: Path) -> str:
    record = json.loads(path.read_text(encoding="utf-8"))
    record.pop("record_digest", None)
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _commands() -> list[tuple[str, list[str]]]:
    py = sys.executable
    npm = "npm.cmd" if os.name == "nt" else "npm"
    return [
        ("api-tests", [py, "-m", "pytest", "-q", "services/api"]),
        ("harness-tests", [py, "-m", "pytest", "-q", "services/harness"]),
        ("model-tests", [py, "-m", "pytest", "-q", "models/crop_disease", "models/pipeline"]),
        ("model-catalog", [py, "scripts/validate_model_catalog.py"]),
        ("contract-tests", [py, "-m", "pytest", "-q", "tests/contract", "tests/security"]),
        ("load-failure-tests", [py, "-m", "pytest", "-q", "tests/load", "tests/failure"]),
        ("browser-matrix", [py, "tests/reports/run_browser_matrix.py"]),
        ("browser-vision-tests", [npm, "--prefix", "packages/browser-vision", "test"]),
        ("frontend-tests", [npm, "--prefix", "apps/web", "run", "test:ui"]),
        ("frontend-build", [npm, "--prefix", "apps/web", "run", "build"]),
        ("deployment-contract", [py, "scripts/health_check.py", "--compose", "deploy/compose.yaml", "--config-only"]),
        ("clean-checkout-tests", [py, "-m", "pytest", "-q", "tests/deploy/test_clean_checkout.py"]),
        ("rollback-tests", [py, "-m", "pytest", "-q", "tests/deploy/test_rollback.py"]),
        ("standalone-boundary", [py, "scripts/check_standalone_boundary.py", "--root", ".", "--manifest", "docs/MIGRATION_MANIFEST.md", "--standalone-copy-check"]),
        ("cv-approval", [py, "scripts/validate_approved_releases.py", "--record", "docs/APPROVED_RELEASES.json", "--require-all"]),
    ]


def run(profile: str, output: Path, checksums: Path) -> int:
    output = output.resolve()
    checksums = checksums.resolve()
    started = _now()
    logs = output.parent / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    artifacts: list[dict[str, object]] = []
    for result_id, command in _commands():
        item_started = _now()
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        stdout = logs / f"{result_id}.stdout.log"
        stderr = logs / f"{result_id}.stderr.log"
        stdout.write_text(completed.stdout, encoding="utf-8")
        stderr.write_text(completed.stderr, encoding="utf-8")
        for artifact in (stdout, stderr):
            artifacts.append({"path": artifact.relative_to(ROOT).as_posix(), "sha256": _sha256(artifact), "size_bytes": artifact.stat().st_size})
        results.append({"id": result_id, "command": command, "exit_code": completed.returncode, "status": "pass" if completed.returncode == 0 else "fail", "started_at": item_started, "finished_at": _now(), "stdout_path": stdout.relative_to(ROOT).as_posix(), "stderr_path": stderr.relative_to(ROOT).as_posix()})
    approval_path = ROOT / "docs/APPROVED_RELEASES.json"
    approval_digest = _approval_digest(approval_path)
    status = "pass" if all(item["status"] == "pass" for item in results) else "fail"
    payload = {"schema_version": 1, "profile": profile, "started_at": started, "finished_at": _now(), "status": status, "release_ready": status == "pass", "approval_record_digest": approval_digest, "results": results, "artifacts": artifacts}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, output)
    checksum_payload = {"schema_version": 1, "generated_at": _now(), "files": [{"path": output.relative_to(ROOT).as_posix(), "sha256": _sha256(output), "size_bytes": output.stat().st_size}, *artifacts]}
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=checksums.parent, delete=False) as handle:
        json.dump(checksum_payload, handle, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, checksums)
    print(json.dumps({"status": status, "results": len(results), "output": str(output), "approval_record_digest": approval_digest}))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="ci")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checksums", type=Path, required=True)
    parser.add_argument("--append-rollback", type=Path)
    parser.add_argument("--append-final-integrity", action="store_true")
    args = parser.parse_args()
    raise SystemExit(run(args.profile, args.output, args.checksums))
