"""Static guard for standalone ownership and parent-runtime independence."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

try:
    from capture_parent_baseline import parse_manifest, validate_manifest
except ModuleNotFoundError:  # Imported by a test loader rather than executed as a script.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from capture_parent_baseline import parse_manifest, validate_manifest


CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".yaml", ".yml", ".toml", ".Dockerfile"}
GENERATED_PARTS = {"__pycache__", ".pytest_cache", "node_modules", "dist", "logs", "downloaded", "test-results"}
EVIDENCE_FILES = {
    "docs/MIGRATION_MANIFEST.md",
    "docs/PARENT_BASELINE.json",
    "docs/PARITY_REPORT.md",
    "scripts/check_standalone_boundary.py",
    "tests/results/gate-results.json",
    "tests/results/artifact-checksums.json",
}
PARENT_IMPORT_PATTERNS = (
    (re.compile(r"(?:from|import)\s+\.\."), "parent-relative import"),
    (re.compile(r"(?:from|import)\s+\.\\\\"), "parent-relative import"),
    (re.compile(r"(?:context|COPY|ADD)\s*[: ]+\.\.(?:[/\\]|$)", re.IGNORECASE), "parent Docker/build context"),
    # Match a runtime directory token, not ordinary Python attributes such as
    # ``settings.runtime_db_dir`` used by the standalone configuration.
    (re.compile(r"(?:KISANSATHI_AGENT_ROOT|KISANSATHI_BACKEND_URL|/backend/|\\\\backend\\\\|(?<![A-Za-z0-9_])\.runtime(?![A-Za-z0-9_]))", re.IGNORECASE), "parent runtime path"),
)


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def scan_boundary(root: Path, declared: set[str] | None = None) -> list[str]:
    root = root.resolve()
    problems: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = _relative(root, path)
        if any(part in GENERATED_PARTS for part in path.relative_to(root).parts) or path.suffix == ".pyc":
            continue
        if relative in EVIDENCE_FILES:
            continue
        if path.is_symlink():
            try:
                path.resolve().relative_to(root)
            except ValueError:
                problems.append(f"symlink escape: {relative}")
            continue
        if not path.is_file():
            continue
        if declared is not None and relative not in declared and relative != ".gitkeep":
            problems.append(f"undeclared standalone file: {relative}")
        # Contract tests intentionally contain unsafe import/path examples to
        # exercise this scanner; they are not shipped runtime code.
        if "tests" in path.relative_to(root).parts:
            continue
        if path.suffix not in CODE_SUFFIXES and path.name not in {"Dockerfile", "compose.yaml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern, label in PARENT_IMPORT_PATTERNS:
            if pattern.search(text):
                problems.append(f"{label}: {relative}")
        if path.name in {"package.json", "package-lock.json"}:
            try:
                package = json.loads(text)
                if any(str(value).startswith(("file:", "../", "..\\")) for value in package.get("dependencies", {}).values()):
                    problems.append(f"parent package dependency: {relative}")
            except json.JSONDecodeError:
                problems.append(f"invalid package JSON: {relative}")
    return sorted(set(problems))


def declared_targets(manifest: Path, repo_root: Path, target_root: Path) -> set[str]:
    entries = parse_manifest(manifest)
    validate_manifest(entries, repo_root, target_root)
    targets: set[str] = set()
    for entry in entries:
        if entry.disposition == "exclude" or entry.target in {"none", ""}:
            continue
        target = entry.target.replace("\\", "/")
        while target.startswith("./"):
            target = target[2:]
        targets.add(target)
    return targets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--standalone-copy-check", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    repo_root = root.parent
    declared = declared_targets(args.manifest, repo_root, root)
    problems = scan_boundary(root, declared)
    if args.standalone_copy_check:
        with tempfile.TemporaryDirectory(prefix="kisansathi-boundary-") as directory:
            copy = Path(directory) / root.name
            shutil.copytree(root, copy, symlinks=True)
            problems.extend(scan_boundary(copy, declared))
    problems = sorted(set(problems))
    if problems:
        print("standalone boundary: FAIL")
        print("\n".join(problems))
        return 1
    print("standalone boundary: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
