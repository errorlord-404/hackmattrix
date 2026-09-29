"""Capture and validate the immutable parent-tree evidence for Phase 7.

This module deliberately uses Git's file lists rather than importing any application
package.  It can therefore be run from a clean checkout or from the standalone tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


class ManifestError(ValueError):
    pass


class BaselineExistsError(FileExistsError):
    pass


@dataclass(frozen=True)
class ManifestEntry:
    source: str
    target: str
    disposition: str
    source_sha256: str
    rationale: str


REQUIRED_DISPOSITIONS = {"copy", "adapt", "replace", "exclude"}
APPROVED_PLANNING_PREFIX = ".planning/"


def _cells(line: str) -> list[str]:
    if not line.strip().startswith("|"):
        return []
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_manifest(path: Path) -> list[ManifestEntry]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header_index = next(
        (index for index, line in enumerate(lines) if "Source" in _cells(line) and "Target" in _cells(line)),
        None,
    )
    if header_index is None:
        raise ManifestError("manifest is missing its source/target table")
    headers = [cell.lower().replace("-", "_").replace(" ", "_") for cell in _cells(lines[header_index])]
    positions = {name: headers.index(name) for name in ("source", "target", "disposition", "sha_256", "rationale") if name in headers}
    if set(positions) != {"source", "target", "disposition", "sha_256", "rationale"}:
        raise ManifestError("manifest table must contain Source, Target, Disposition, SHA-256, and Rationale")
    entries: list[ManifestEntry] = []
    for line in lines[header_index + 2 :]:
        cells = _cells(line)
        if not cells or len(cells) < len(headers):
            continue
        values = {name: cells[index] for name, index in positions.items()}
        entries.append(ManifestEntry(
            source=values["source"], target=values["target"], disposition=values["disposition"].lower(),
            source_sha256="" if values["sha_256"] in {"—", "-", "", "none"} else values["sha_256"].lower(),
            rationale=values["rationale"],
        ))
    return entries


def _relative(path: str) -> str:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _has_symlink_component(root: Path, relative: str) -> bool:
    current = root
    for part in Path(relative).parts:
        current /= part
        if current.is_symlink():
            return True
    return False


def validate_manifest(entries: Iterable[ManifestEntry], repo_root: Path, target_root: Path) -> None:
    entries = list(entries)
    if not entries:
        raise ManifestError("manifest has no entries")
    seen_sources: set[tuple[str, str]] = set()
    seen_targets: set[str] = set()
    for entry in entries:
        source = _relative(entry.source)
        target = _relative(entry.target)
        if entry.disposition not in REQUIRED_DISPOSITIONS:
            raise ManifestError(f"unsupported disposition: {entry.disposition}")
        if not source or not target or not entry.rationale:
            raise ManifestError("every manifest row requires source, target, disposition, and rationale")
        if (source, target) in seen_sources or (target in seen_targets and entry.disposition != "exclude"):
            raise ManifestError(f"duplicate manifest path: {source} -> {target}")
        seen_sources.add((source, target))
        if entry.disposition == "exclude":
            continue
        if target.startswith("../") or Path(target).is_absolute() or not _inside(target_root, target_root / target):
            raise ManifestError(f"target escapes standalone root: {target}")
        if _has_symlink_component(target_root, target):
            raise ManifestError(f"target traverses a symlink: {target}")
        source_path = repo_root / source
        # `replace` rows may describe new standalone-owned files with no
        # parent source counterpart. Copy/adapt rows must always resolve to a
        # real parent file and retain its checksum.
        if entry.disposition != "replace" and "*" not in source and "?" not in source and not source_path.is_file():
            raise ManifestError(f"source does not exist: {source}")
        if entry.disposition in {"copy", "adapt"}:
            if not entry.source_sha256 or len(entry.source_sha256) != 64:
                raise ManifestError(f"copy/adapt row has no SHA-256: {source}")
            if source_path.is_file() and sha256(source_path) != entry.source_sha256:
                raise ManifestError(f"source hash mismatch: {source}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(repo_root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True, encoding="utf-8", errors="replace")


def _git_paths(repo_root: Path) -> list[str]:
    raw = _git(repo_root, "ls-files", "-co", "--exclude-standard", "-z")
    return sorted(path.replace("\\", "/") for path in raw.split("\0") if path)


def _is_excluded(path: str, target_root: Path, repo_root: Path) -> bool:
    target_prefix = target_root.resolve().relative_to(repo_root.resolve()).as_posix().rstrip("/") + "/"
    return path == target_prefix.rstrip("/") or path.startswith(target_prefix) or path == ".git" or path.startswith(".git/") or path.startswith(APPROVED_PLANNING_PREFIX)


def capture_baseline(repo_root: Path, target_root: Path) -> dict:
    repo_root = repo_root.resolve()
    target_root = target_root.resolve()
    paths = [path for path in _git_paths(repo_root) if not _is_excluded(path, target_root, repo_root)]
    files = {path: sha256(repo_root / path) for path in paths if (repo_root / path).is_file()}
    return {
        "schema_version": 1,
        "capture_root": ".",
        "head": _git(repo_root, "rev-parse", "HEAD").strip(),
        "porcelain_v2": _git(repo_root, "status", "--porcelain=v2", "--untracked-files=all"),
        "files": files,
        "excluded_paths": [".git/**", ".planning/**", f"{target_root.relative_to(repo_root).as_posix()}/**"],
        "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def write_baseline(path: Path, snapshot: dict, *, refresh: bool = False) -> None:
    if path.exists() and not refresh:
        raise BaselineExistsError(f"refusing to overwrite existing baseline: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_baseline(path: Path, repo_root: Path, target_root: Path) -> bool:
    if not path.is_file():
        return False
    expected = json.loads(path.read_text(encoding="utf-8"))
    actual = capture_baseline(repo_root, target_root)
    return expected.get("schema_version") == 1 and expected.get("files") == actual.get("files")


def validate_frontend_parity(payload: dict) -> None:
    rows = payload.get("workflows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("frontend parity baseline must contain workflows")
    required = {"id", "route", "workflow", "baseline_source", "visible_states", "input", "output", "safety_boundary", "frozen_contract_fixture", "standalone_feature_owner", "final_black_box_test_id"}
    ids: set[str] = set()
    tests: set[str] = set()
    for row in rows:
        if not required <= row.keys() or not all(row.get(key) for key in required):
            raise ValueError("frontend parity row is incomplete")
        if set(("success", "degraded", "empty", "error")) - set(row["visible_states"]):
            raise ValueError(f"frontend parity row omits a visible state: {row.get('id')}")
        for key, seen in (("id", ids), ("final_black_box_test_id", tests)):
            if row[key] in seen:
                raise ValueError(f"duplicate frontend parity {key}: {row[key]}")
            seen.add(row[key])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    target_root = repo_root / "Kisan Sathi Web"
    if args.check:
        ok = check_baseline(args.output, repo_root, target_root)
        print("parent baseline: PASS" if ok else "parent baseline: FAIL")
        return 0 if ok else 1
    write_baseline(args.output, capture_baseline(repo_root, target_root), refresh=args.refresh)
    print(f"parent baseline written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
