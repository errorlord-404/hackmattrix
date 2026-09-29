"""Download a bounded PlantVillage sample using a local repository's Git manifest.

Use only for the controlled-image crop-router demo. It intentionally downloads
no full dataset and preserves the source directory in filenames. Confirm the
upstream license/revision before use.
"""

from __future__ import annotations

import argparse
import random
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

from prepare_plantvillage_crop_router import DEFAULT_CROPS


def paths_for(repository: Path, source_crop: str) -> list[str]:
    command = ["git", "-C", str(repository), "ls-tree", "-r", "--name-only", "HEAD", "raw/color"]
    output = subprocess.check_output(command, text=True, encoding="utf-8")
    prefix = f"raw/color/{source_crop}___"
    return [line for line in output.splitlines() if line.startswith(prefix) and line.lower().endswith((".jpg", ".jpeg", ".png"))]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True, help="Local metadata checkout of spMohanty/PlantVillage-Dataset")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-crop", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--revision", default="master", help="Public raw GitHub branch/revision")
    args = parser.parse_args()
    if args.per_crop < 2:
        raise SystemExit("per-crop must be at least 2")
    randomizer = random.Random(args.seed)
    for source_crop, label in DEFAULT_CROPS.items():
        files = paths_for(args.repository, source_crop)
        if len(files) < args.per_crop:
            raise SystemExit(f"Only {len(files)} files found for {source_crop}; need {args.per_crop}")
        randomizer.shuffle(files)
        destination = args.output / label
        destination.mkdir(parents=True, exist_ok=True)
        for index, relative_path in enumerate(files[:args.per_crop]):
            encoded_path = "/".join(urllib.parse.quote(segment) for segment in relative_path.split("/"))
            url = f"https://raw.githubusercontent.com/spMohanty/PlantVillage-Dataset/{args.revision}/{encoded_path}"
            suffix = Path(relative_path).suffix.lower()
            target = destination / f"{label}-{index:04d}{suffix}"
            with urllib.request.urlopen(url, timeout=20) as response, target.open("wb") as destination_file:
                destination_file.write(response.read())
        print(f"downloaded {args.per_crop} images for {label}")


if __name__ == "__main__":
    main()
