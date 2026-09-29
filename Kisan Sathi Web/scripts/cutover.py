from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


class CutoverBlocked(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_evidence(results_path: Path, checksums_path: Path, *, require_all: bool = False) -> dict:
    if not results_path.is_file() or not checksums_path.is_file():
        raise CutoverBlocked("machine-readable gate results and checksums are required")
    results = json.loads(results_path.read_text(encoding="utf-8"))
    checksums = json.loads(checksums_path.read_text(encoding="utf-8"))
    if results.get("schema_version") != 1 or results.get("status") != "pass":
        raise CutoverBlocked("gate-results status is not passing")
    if require_all and not results.get("release_ready"):
        raise CutoverBlocked("release evidence is not marked release_ready")
    entries = {item["path"]: item for item in checksums.get("files", [])}
    for path_text, entry in entries.items():
        path = results_path.parent.parent.parent / path_text
        if not path.is_file() or _sha256(path) != entry.get("sha256"):
            raise CutoverBlocked(f"artifact checksum mismatch: {path_text}")
    for item in results.get("results", []):
        if item.get("status") != "pass" or item.get("exit_code") != 0:
            raise CutoverBlocked(f"gate did not pass: {item.get('id', 'unknown')}")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed standalone cutover preflight")
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--checksums", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--require-precutover", action="store_true")
    parser.add_argument("--require-all", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        results = validate_evidence(args.results.resolve(), args.checksums.resolve(), require_all=args.require_all or args.apply)
    except (CutoverBlocked, OSError, json.JSONDecodeError) as exc:
        print(f"cutover: BLOCKED: {exc}")
        return 1
    if not args.dry_run and not args.apply:
        print("cutover: specify --dry-run or --apply")
        return 2
    if args.apply:
        print("cutover: BLOCKED: live traffic switching requires a separately reviewed operator release configuration")
        return 1
    print(json.dumps({"status": "preflight_pass", "mode": "dry-run", "release_ready": results.get("release_ready", False), "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
