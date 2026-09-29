"""Build a bounded PlantDoc tomato-specialist train/validation experiment.

PlantDoc is an external web-image source, not target-region farmer-phone
evidence. This utility keeps its source revision and subset manifest explicit.
It splits PlantDoc's source ``train`` folder into development train/validation
and reserves its source ``test`` folder as a final external check. It
intentionally calls that folder ``external_test``, not ``field_test``: PlantDoc
does not establish farmer-phone field performance.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from materialize_plantdoc_tomato_external_test import (
    IMAGE_SUFFIXES,
    PLANTDOC_TOMATO_LABELS,
    git_output,
    safe_name,
    tree_paths,
)


# `git show` on Git for Windows can reject long virtual source paths even when
# the output filename is safe. Bound the input path before materializing it.
MAX_GIT_SOURCE_PATH_CHARS = 160


def label_paths(paths: list[str], split: str, source_label: str) -> list[str]:
    """Return image paths for exactly one PlantDoc split/label, safely bounded."""
    prefix = f"{split}/{source_label}/"
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
    parser.add_argument("--output", type=Path, required=True, help="New directory containing train/, val/ and external_test/ ImageFolder labels")
    parser.add_argument("--train-per-label", type=int, default=45, help="Bounded number of PlantDoc source-train images per output training label")
    parser.add_argument("--val-per-label", type=int, default=10, help="Bounded number of disjoint PlantDoc source-train images per output validation label")
    parser.add_argument("--field-test-per-label", type=int, default=6, help="Bounded number of PlantDoc source-test images per final external label")
    args = parser.parse_args()
    if min(args.train_per_label, args.val_per_label, args.field_test_per_label) < 1:
        raise SystemExit("train-per-label, val-per-label and field-test-per-label must be positive")
    if not args.repository.is_dir():
        raise SystemExit("repository is not a directory")
    if args.output.exists() and any(args.output.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output: {args.output}")

    paths = tree_paths(args.repository, args.revision)
    source_train = {label: label_paths(paths, "train", label) for label in PLANTDOC_TOMATO_LABELS}
    source_test = {label: label_paths(paths, "test", label) for label in PLANTDOC_TOMATO_LABELS}
    selections: dict[tuple[str, str], list[str]] = {}
    for source_label in PLANTDOC_TOMATO_LABELS:
        required_development = args.train_per_label + args.val_per_label
        if len(source_train[source_label]) < required_development:
            raise SystemExit(f"train/{source_label} has only {len(source_train[source_label])} eligible images; needs {required_development}")
        if len(source_test[source_label]) < args.field_test_per_label:
            raise SystemExit(f"test/{source_label} has only {len(source_test[source_label])} eligible images; needs {args.field_test_per_label}")
        selections[("train", source_label)] = source_train[source_label][: args.train_per_label]
        selections[("val", source_label)] = source_train[source_label][args.train_per_label : required_development]
        selections[("external_test", source_label)] = source_test[source_label][: args.field_test_per_label]

    manifest = [
        "# PlantDoc tomato specialist source subset",
        f"repository: {args.repository}",
        f"revision: {args.revision}",
        "license: CC-BY-4.0 (verify upstream attribution before redistribution)",
        "scope: external domain-adaptation benchmark/demo only; not farmer-phone release evidence",
        "partitioning: train/val come from disjoint source train paths; external_test comes from source test paths",
        "",
    ]
    for output_split in ("train", "val", "external_test"):
        for source_label, output_label in PLANTDOC_TOMATO_LABELS.items():
            destination = args.output / output_split / output_label
            destination.mkdir(parents=True, exist_ok=True)
            for index, source_path in enumerate(selections[(output_split, source_label)]):
                target = destination / safe_name(output_label, index, source_path)
                target.write_bytes(git_output(args.repository, "show", f"{args.revision}:{source_path}"))
                manifest.append(f"{output_split}\t{output_label}\t{target.name}\t{source_path}")
    (args.output / "SOURCE_MANIFEST.tsv").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"Materialized PlantDoc tomato specialist split at {args.output}")


if __name__ == "__main__":
    main()
