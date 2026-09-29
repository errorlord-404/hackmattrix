"""Prepare a small, reproducible PlantVillage crop-router demonstration split.

This is deliberately an *illustrative controlled-image* demo, not a field
validation dataset. It groups PlantVillage's disease directories by crop and
keeps images from each source directory in both labels only through a
deterministic split. Use external target-region field data for release testing.
"""

from __future__ import annotations

import argparse
import random
import shutil
from collections import defaultdict
from pathlib import Path


DEFAULT_CROPS = {"Tomato": "tomato", "Corn_(maize)": "maize", "Potato": "potato", "Pepper,_bell": "bell_pepper"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plantvillage-color", type=Path, required=True, help="Path to PlantVillage raw/color directory")
    parser.add_argument("--output", type=Path, required=True, help="New ImageFolder output directory")
    parser.add_argument("--per-crop", type=int, default=500, help="Maximum images per target crop")
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output: {args.output}")
    if args.per_crop < 2 or not 0 < args.val_fraction < 1:
        raise SystemExit("per-crop must be >=2 and val-fraction must be between 0 and 1")
    randomizer = random.Random(args.seed)
    grouped: dict[str, list[Path]] = defaultdict(list)
    for source_dir in sorted(args.plantvillage_color.iterdir()):
        if not source_dir.is_dir():
            continue
        source_crop = source_dir.name.split("___", 1)[0]
        label = DEFAULT_CROPS.get(source_crop)
        if label:
            grouped[label].extend(sorted(path for path in source_dir.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"}))
    missing = set(DEFAULT_CROPS.values()) - set(grouped)
    if missing:
        raise SystemExit(f"No image directories found for {sorted(missing)}")
    for label, images in grouped.items():
        randomizer.shuffle(images)
        images = images[:args.per_crop]
        cutoff = max(1, min(len(images) - 1, round(len(images) * (1 - args.val_fraction))))
        for split, selected in (("train", images[:cutoff]), ("val", images[cutoff:])):
            destination = args.output / split / label
            destination.mkdir(parents=True, exist_ok=True)
            for index, image in enumerate(selected):
                shutil.copy2(image, destination / f"{label}-{index:04d}{image.suffix.lower()}")
        print(f"{label}: train={cutoff} val={len(images) - cutoff}")


if __name__ == "__main__":
    main()
