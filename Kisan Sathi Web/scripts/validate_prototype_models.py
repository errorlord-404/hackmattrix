"""Validate the locally installed research models for prototype use only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.crop_disease.prototype import build_prototype_profile  # noqa: E402
from models.crop_disease.registry import CropDiseaseRegistry, default_registry_path  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify installed research checkpoints for prototype inference")
    parser.add_argument("--registry", type=Path, default=default_registry_path())
    parser.add_argument("--root", type=Path, default=ROOT / "models" / "crop_disease" / "downloaded")
    parser.add_argument("--write-profile", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    registry = CropDiseaseRegistry.from_path(args.registry)
    profile = build_prototype_profile(registry, args.root)
    if args.write_profile:
        args.write_profile.parent.mkdir(parents=True, exist_ok=True)
        args.write_profile.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

    if args.as_json:
        print(json.dumps(profile, indent=2))
    else:
        print(
            f"prototype_status={profile['status']} "
            f"models={profile['model_count']} "
            f"supported_crops={len(profile['supported_crops'])}"
        )
        for model in profile["models"]:
            print(f"{model['id']}: {model['status']}")
        print("production_approved=false diagnostic_use_allowed=false")

    return 0 if profile["model_count"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
