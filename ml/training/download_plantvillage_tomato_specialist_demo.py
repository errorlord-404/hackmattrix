"""Download a bounded controlled-image sample for a tomato disease specialist demo."""

from __future__ import annotations

import argparse
import random
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path


SOURCES = {
    "Tomato___healthy": "healthy",
    "Tomato___Early_blight": "early_blight",
    "Tomato___Late_blight": "late_blight",
    "Tomato___Leaf_Mold": "leaf_mold",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-label", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--revision", default="master")
    args = parser.parse_args()
    manifest = subprocess.check_output(
        ["git", "-C", str(args.repository), "ls-tree", "-r", "--name-only", "HEAD", "raw/color"], text=True, encoding="utf-8"
    ).splitlines()
    randomizer = random.Random(args.seed)
    for source, label in SOURCES.items():
        prefix = f"raw/color/{source}/"
        files = [line for line in manifest if line.startswith(prefix) and line.lower().endswith((".jpg", ".jpeg", ".png"))]
        if len(files) < args.per_label:
            raise SystemExit(f"Only {len(files)} files found for {source}")
        randomizer.shuffle(files)
        destination = args.output / label
        destination.mkdir(parents=True, exist_ok=True)
        for index, relative_path in enumerate(files[:args.per_label]):
            encoded_path = "/".join(urllib.parse.quote(segment) for segment in relative_path.split("/"))
            target = destination / f"{label}-{index:04d}{Path(relative_path).suffix.lower()}"
            url = f"https://raw.githubusercontent.com/spMohanty/PlantVillage-Dataset/{args.revision}/{encoded_path}"
            with urllib.request.urlopen(url, timeout=20) as response, target.open("wb") as destination_file:
                destination_file.write(response.read())
        print(f"downloaded {args.per_label} images for {label}")


if __name__ == "__main__":
    main()
