"""Command-line entry points for registry inspection and candidate workflows."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from .contracts import PipelineError, load_json
from .evaluation import evaluate_release_candidate
from .packaging import package_candidate, register_candidate
from .quantization import quantize_onnx
from .registry import ModelRegistry


OPTIONAL_MODULES = {
    "pytorch": ("torch", "torchvision"),
    "tensorflow": ("tensorflow",),
    "tensorflow_hub": ("tensorflow_hub",),
    "onnx": ("onnx", "onnxruntime"),
    "tflite": ("tensorflow",),
}


def _doctor(required: list[str] | None = None) -> tuple[dict[str, Any], int]:
    required = required or []
    core = {
        name: importlib.util.find_spec(name) is not None
        for name in ("jsonschema", "pydantic")
    }
    groups = {
        group: {
            "available": all(importlib.util.find_spec(name) is not None for name in modules),
            "modules": {name: importlib.util.find_spec(name) is not None for name in modules},
        }
        for group, modules in OPTIONAL_MODULES.items()
    }
    missing_core = sorted(name for name, available in core.items() if not available)
    missing_required = sorted(
        group for group in required if not groups[group]["available"]
    )
    status = "ok" if not missing_core and not missing_required else "missing_dependencies"
    result = {
        "status": status,
        "core": core,
        "optional_backends": groups,
        "missing_core": missing_core,
        "missing_required_optional": missing_required,
    }
    return result, 0 if status == "ok" else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="Override models/pipeline root")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("registry-list")
    sub.add_parser("registry-validate")
    recipe = sub.add_parser("recipe-validate")
    recipe.add_argument("--file", type=Path)
    doctor = sub.add_parser("doctor")
    doctor.add_argument(
        "--require",
        action="append",
        choices=tuple(OPTIONAL_MODULES),
        default=[],
        help="return a failure when this optional backend group is unavailable",
    )
    evaluate = sub.add_parser("evaluate-release")
    evaluate.add_argument("--candidate", type=Path, required=True)
    evaluate.add_argument("--dataset-manifest", type=Path)
    evaluate.add_argument("--threshold-profile", type=Path)
    evaluate.add_argument("--output", type=Path, required=True)
    package = sub.add_parser("package-candidate")
    package.add_argument("--source-root", type=Path, required=True)
    package.add_argument("--destination", type=Path, required=True)
    package.add_argument("--metadata", type=Path, required=True)
    package.add_argument("--artifacts", type=Path, required=True, help="JSON object mapping artifact roles to relative source paths")
    package.add_argument("--created-at")
    register = sub.add_parser("register-candidate")
    register.add_argument("--manifest", type=Path, required=True)
    register.add_argument("--models-root", type=Path, required=True)
    quantize = sub.add_parser("quantize-onnx")
    quantize.add_argument("--source", type=Path, required=True)
    quantize.add_argument("--destination", type=Path, required=True)
    quantize.add_argument("--mode", choices=("static-int8", "dynamic-int8"), default="static-int8")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    registry = ModelRegistry(args.root) if args.root else ModelRegistry()
    try:
        if args.command == "registry-list":
            result = {
                "backbones": registry.backbones(),
                "recipes": registry.recipes(),
                "activation_allowed": False,
            }
        elif args.command == "registry-validate":
            result = registry.report()
        elif args.command == "recipe-validate":
            document = registry.recipe_document(args.file)
            result = {
                "status": "valid_template_catalog",
                "recipe_count": len(document["recipes"]),
                "activation_allowed": False,
            }
        elif args.command == "evaluate-release":
            result = evaluate_release_candidate(
                args.candidate,
                dataset_manifest=args.dataset_manifest,
                threshold_profile=args.threshold_profile,
                output=args.output,
            )
        elif args.command == "package-candidate":
            result = {"manifest": str(package_candidate(args.source_root, args.destination, candidate=load_json(args.metadata, "candidate metadata"), artifacts=load_json(args.artifacts, "artifact map"), created_at=args.created_at))}
        elif args.command == "register-candidate":
            result = register_candidate(args.manifest, args.models_root)
        elif args.command == "quantize-onnx":
            result = quantize_onnx(args.source, args.destination, mode=args.mode)
        else:
            result, exit_code = _doctor(args.require)
        print(json.dumps(result, sort_keys=True))
        return exit_code if args.command == "doctor" else 0
    except PipelineError as exc:
        print(f"model pipeline: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
