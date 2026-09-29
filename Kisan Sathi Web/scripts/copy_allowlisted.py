"""Copy only manifest-approved sources into the standalone tree."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

try:
    from capture_parent_baseline import ManifestEntry, ManifestError, parse_manifest, sha256, validate_manifest
except ModuleNotFoundError:  # Imported by a test loader rather than executed as a script.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from capture_parent_baseline import ManifestEntry, ManifestError, parse_manifest, sha256, validate_manifest


class CopySafetyError(ValueError):
    pass


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(root.resolve())
        return True
    except ValueError:
        return False


def copy_entries(entries: list[ManifestEntry], source_root: Path, target_root: Path, *, dry_run: bool) -> list[dict[str, str]]:
    source_root = source_root.resolve()
    target_root = target_root.resolve()
    try:
        validate_manifest(entries, source_root, target_root)
    except ManifestError as exc:
        raise CopySafetyError(str(exc)) from exc
    operations: list[dict[str, str]] = []
    for entry in entries:
        if entry.disposition not in {"copy", "adapt"}:
            continue
        source = (source_root / entry.source.replace("\\", "/")).resolve()
        destination = target_root / entry.target.replace("\\", "/")
        if not _inside(target_root, destination):
            raise CopySafetyError(f"target escapes standalone root: {entry.target}")
        if destination.is_symlink() or any(part.is_symlink() for part in destination.parents if part != target_root.parent):
            raise CopySafetyError(f"destination traverses a symlink: {entry.target}")
        if not source.is_file() or sha256(source) != entry.source_sha256:
            raise CopySafetyError(f"source hash mismatch: {entry.source}")
        relative = destination.relative_to(target_root).as_posix()
        operation = "update" if destination.exists() else "create"
        operations.append({"operation": operation, "target": relative})
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    return operations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    entries = parse_manifest(args.manifest)
    operations = copy_entries(entries, args.source_root, args.target_root, dry_run=args.dry_run)
    for operation in operations:
        print(f"{operation['operation']}: {operation['target']}")
    print(f"allowlisted operations: {len(operations)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
