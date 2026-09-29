"""Build a bounded PlantDoc crop-router train/validation split from a Git SHA.

This is an external-image benchmark and demo-data utility. Its output can only
suggest a crop; backend policy still requires farmer confirmation before a
crop-specific disease specialist is invoked.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from materialize_plantdoc_tomato_external_test import IMAGE_SUFFIXES, git_output, safe_name, tree_paths


PLANTDOC_CROPS = {
    "Tomato": "tomato",
    "Corn": "maize",
    "Potato": "potato",
    "Bell_pepper": "bell_pepper",
}
# Git for Windows may fail to materialize a blob when its virtual repository
# path exceeds the legacy Win32 path limit, even though our destination name is
# short. Keep the source-path rule explicit and record every retained path.
MAX_GIT_SOURCE_PATH_CHARS = 160


def crop_paths(paths: list[str], split: str, source_crop: str) -> list[str]:
    prefix = f"{split}/{source_crop} "
    return [
        path
        for path in paths
        if path.startswith(prefix)
        and Path(path).suffix.lower() in IMAGE_SUFFIXES
        and len(path) <= MAX_GIT_SOURCE_PATH_CHARS
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True, help="New directory containing train/ and val/ ImageFolder labels")
    parser.add_argument("--per-crop", type=int, default=100, help="Bounded number of source training images per crop")
    parser.add_argument("--val-per-crop", type=int, default=16, help="Bounded number of source test images per crop")
    args = parser.parse_args()
    if args.per_crop < 1 or args.val_per_crop < 1:
        raise SystemExit("per-crop and val-per-crop must be positive")
    if not args.repository.is_dir():
        raise SystemExit("repository is not a directory")
    if args.output.exists() and any(args.output.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output: {args.output}")
    paths = tree_paths(args.repository, args.revision)
    selections = {
        (split, source_crop): crop_paths(paths, split, source_crop)[:limit]
        for split, limit in (("train", args.per_crop), ("test", args.val_per_crop))
        for source_crop in PLANTDOC_CROPS
    }
    for (split, source_crop), selected in selections.items():
        limit = args.per_crop if split == "train" else args.val_per_crop
        if len(selected) < limit:
            raise SystemExit(f"{split}/{source_crop} has only {len(selected)} eligible images; needs {limit}")
    manifest = [
        "# PlantDoc crop-router source subset",
        f"repository: {args.repository}",
        f"revision: {args.revision}",
        "license: CC-BY-4.0 (verify upstream attribution before redistribution)",
        "scope: crop-router benchmark/demo only; requires farmer confirmation",
        "",
    ]
    for source_split, output_split in (("train", "train"), ("test", "val")):
        for source_crop, label in PLANTDOC_CROPS.items():
            destination = args.output / output_split / label
            destination.mkdir(parents=True, exist_ok=True)
            for index, source_path in enumerate(selections[(source_split, source_crop)]):
                target = destination / safe_name(label, index, source_path)
                target.write_bytes(git_output(args.repository, "show", f"{args.revision}:{source_path}"))
                manifest.append(f"{output_split}\t{label}\t{target.name}\t{source_path}")
    (args.output / "SOURCE_MANIFEST.tsv").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"Materialized PlantDoc crop-router split at {args.output}")


if __name__ == "__main__":
    main()
