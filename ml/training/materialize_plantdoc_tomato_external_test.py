"""Materialize a bounded external PlantDoc tomato test set from a Git revision.

The output is evaluation-only. It must never be mixed into the controlled
PlantVillage training split or used as a farmer-phone field-release claim.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


PLANTDOC_TOMATO_LABELS = {
    "Tomato Early blight leaf": "early_blight",
    "Tomato leaf": "healthy",
    "Tomato leaf late blight": "late_blight",
    "Tomato mold leaf": "leaf_mold",
}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def safe_name(label: str, index: int, source_path: str) -> str:
    """Create a Windows-safe output name without retaining URL-like source names."""
    suffix = Path(source_path).suffix.lower()
    if suffix not in IMAGE_SUFFIXES:
        suffix = ".jpg"
    return f"{label}-{index:04d}{suffix}"


def git_output(repository: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ).stdout


def tree_paths(repository: Path, revision: str) -> list[str]:
    raw = git_output(repository, "ls-tree", "-r", "-z", "--name-only", revision)
    return [path.decode("utf-8") for path in raw.split(b"\0") if path]


def eligible_paths(paths: list[str], source_label: str) -> list[str]:
    prefix = f"test/{source_label}/"
    return [path for path in paths if path.startswith(prefix) and Path(path).suffix.lower() in IMAGE_SUFFIXES]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True, help="Local partial/full clone of PlantDoc-Dataset")
    parser.add_argument("--revision", required=True, help="Immutable Git commit SHA")
    parser.add_argument("--output", type=Path, required=True, help="New empty ImageFolder-style output directory")
    parser.add_argument("--per-label", type=int, default=20)
    parser.add_argument(
        "--unknown-source-label",
        action="append",
        default=[],
        help="Optional PlantDoc test directory to copy as non-tomato/OOD evidence; repeat the flag for multiple labels.",
    )
    parser.add_argument("--unknown-output", type=Path, help="New empty output directory for unknown/OOD images")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-fA-F]{7,64}", args.revision):
        raise SystemExit("revision must be an immutable hexadecimal Git SHA")
    if args.per_label < 1:
        raise SystemExit("per-label must be positive")
    if not args.repository.is_dir():
        raise SystemExit("repository is not a directory")
    if args.output.exists() and any(args.output.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output: {args.output}")
    if bool(args.unknown_source_label) != bool(args.unknown_output):
        raise SystemExit("--unknown-source-label and --unknown-output must be supplied together")
    if args.unknown_output and args.unknown_output.exists() and any(args.unknown_output.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty unknown output: {args.unknown_output}")

    paths = tree_paths(args.repository, args.revision)
    selected_known = {
        source_label: eligible_paths(paths, source_label)[: args.per_label]
        for source_label in PLANTDOC_TOMATO_LABELS
    }
    selected_unknown = {
        source_label: eligible_paths(paths, source_label)[: args.per_label]
        for source_label in args.unknown_source_label
    }
    for source_label, selected in {**selected_known, **selected_unknown}.items():
        if len(selected) < args.per_label:
            raise SystemExit(f"{source_label} has only {len(selected)} eligible images; needs {args.per_label}")
    manifest_lines = [
        "# PlantDoc external tomato evaluation subset",
        f"repository: {args.repository}",
        f"revision: {args.revision}",
        "license: CC-BY-4.0 (verify upstream attribution before redistribution)",
        "scope: external controlled/field-style benchmark only; not farmer-phone release evidence",
        "",
    ]
    for source_label, label in PLANTDOC_TOMATO_LABELS.items():
        destination = args.output / label
        destination.mkdir(parents=True, exist_ok=True)
        for index, source_path in enumerate(selected_known[source_label]):
            blob = git_output(args.repository, "show", f"{args.revision}:{source_path}")
            target = destination / safe_name(label, index, source_path)
            target.write_bytes(blob)
            manifest_lines.append(f"{label}\t{target.name}\t{source_path}")
    if args.unknown_output:
        args.unknown_output.mkdir(parents=True, exist_ok=True)
        unknown_manifest = [
            "# PlantDoc non-tomato/OOD evaluation subset",
            f"repository: {args.repository}",
            f"revision: {args.revision}",
            "license: CC-BY-4.0 (verify upstream attribution before redistribution)",
            "scope: unknown-rejection benchmark only; not farmer-phone release evidence",
            "",
        ]
        for label_index, source_label in enumerate(args.unknown_source_label):
            for index, source_path in enumerate(selected_unknown[source_label]):
                blob = git_output(args.repository, "show", f"{args.revision}:{source_path}")
                target = args.unknown_output / safe_name(f"unknown-{label_index}", index, source_path)
                target.write_bytes(blob)
                unknown_manifest.append(f"unknown\t{target.name}\t{source_path}")
        (args.unknown_output / "SOURCE_MANIFEST.tsv").write_text("\n".join(unknown_manifest) + "\n", encoding="utf-8")
    (args.output / "SOURCE_MANIFEST.tsv").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    print(f"Materialized {args.per_label * len(PLANTDOC_TOMATO_LABELS)} external PlantDoc images at {args.output}")


if __name__ == "__main__":
    main()
