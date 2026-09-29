"""Create a deterministic ImageFolder split for the first tomato specialist."""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path


LABELS = {
    "Tomato_healthy": "healthy",
    "Tomato_Early_blight": "early_blight",
    "Tomato_Late_blight": "late_blight",
    "Tomato_Leaf_Mold": "leaf_mold",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Directory containing extracted PlantVillage tomato class folders")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-label", type=int, default=500)
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output: {args.output}")
    if args.per_label < 2 or not 0 < args.val_fraction < 1:
        raise SystemExit("per-label must be >=2 and val-fraction must be between 0 and 1")
    randomizer = random.Random(args.seed)
    for source_name, label in LABELS.items():
        images = sorted(path for path in (args.source / source_name).iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"})
        if len(images) < args.per_label:
            raise SystemExit(f"{source_name} has {len(images)} images but needs {args.per_label}")
        randomizer.shuffle(images)
        images = images[:args.per_label]
        cutoff = max(1, min(len(images) - 1, round(len(images) * (1 - args.val_fraction))))
        for split, selected in (("train", images[:cutoff]), ("val", images[cutoff:])):
            destination = args.output / split / label
            destination.mkdir(parents=True, exist_ok=True)
            for index, image in enumerate(selected):
                shutil.copy2(image, destination / f"{label}-{index:04d}{image.suffix.lower()}")
        print(f"{label}: train={cutoff} val={len(images) - cutoff}")


if __name__ == "__main__":
    main()
