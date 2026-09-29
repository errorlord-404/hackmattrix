"""Check that Docker cannot package quarantined or runtime model bytes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_EXCLUSIONS = ("models/candidates", "models/placeholders", "models/releases", "models/crop_disease/downloaded")


def validate_dockerignore(path: Path) -> dict[str, object]:
    lines = {line.strip().rstrip("/") for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")}
    missing = [entry for entry in REQUIRED_EXCLUSIONS if entry not in lines]
    if missing:
        raise ValueError(f"Docker context exclusions are missing: {missing}")
    return {"status": "valid_docker_context_exclusions", "required_exclusions": list(REQUIRED_EXCLUSIONS)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dockerignore", type=Path, default=Path(__file__).resolve().parents[1] / ".dockerignore")
    args = parser.parse_args()
    try:
        print(json.dumps(validate_dockerignore(args.dockerignore), sort_keys=True))
    except (OSError, ValueError) as exc:
        print(f"docker context: FAIL: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
