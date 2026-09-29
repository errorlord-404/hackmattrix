"""Validate quarantined model placeholders without granting release approval."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class PlaceholderError(ValueError):
    pass


def _load(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlaceholderError(f"unable to read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise PlaceholderError(f"{label} must be a JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _within(root: Path, relative: str, label: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise PlaceholderError(f"{label} escapes placeholder package") from exc
    return path


def _artifact(package_root: Path, record: dict[str, Any], label: str, require_installed: bool) -> Path:
    path = _within(package_root, record["path"], label)
    if not path.is_file():
        if require_installed:
            raise PlaceholderError(f"{label} is not installed: {record['path']}")
        return path
    if path.stat().st_size != record["size_bytes"]:
        raise PlaceholderError(f"{label} size mismatch")
    if _sha256(path) != record["sha256"]:
        raise PlaceholderError(f"{label} SHA-256 mismatch")
    return path


def validate_placeholders(index_path: Path, *, require_installed: bool = False, verify_graph: bool = False) -> dict[str, Any]:
    index_path = index_path.resolve()
    root = index_path.parent
    index = _load(index_path, "placeholder index")
    if index.get("policy", {}).get("activation_allowed") is not False:
        raise PlaceholderError("placeholder index must prohibit activation")
    packages = index.get("packages")
    if not isinstance(packages, list) or not packages:
        raise PlaceholderError("placeholder index must contain at least one package")
    coverage = _load(root / "top-15-india.json", "top-15 coverage") if index.get("schema_version") == "2.0" else None

    installed = 0
    research_checkpoints = 0
    structural_stubs = 0
    crop_slots: set[str] = set()
    for package in packages:
        manifest_path = _within(root, package["manifest"], "manifest")
        manifest = _load(manifest_path, "placeholder manifest")
        package_root = manifest_path.parent
        status = manifest.get("status")
        if status not in {"research_placeholder_unapproved", "structural_stub_untrained"}:
            raise PlaceholderError("placeholder manifest has an executable or unknown status")
        if manifest.get("enabled") is not False:
            raise PlaceholderError("placeholder manifest must be disabled")
        if manifest.get("approval", {}).get("release_approved") is not False:
            raise PlaceholderError("placeholder manifest must explicitly deny release approval")
        if status == "structural_stub_untrained":
            structural_stubs += 1
            if manifest.get("diagnostic_capability") is not False:
                raise PlaceholderError("structural stub must explicitly deny diagnostic capability")
            if manifest.get("approval", {}).get("activation_prohibited") is not True:
                raise PlaceholderError("structural stub must prohibit activation")
            if manifest.get("model_contract", {}).get("behavior") != "constant_zero_logits_non_diagnostic":
                raise PlaceholderError("structural stub must declare constant non-diagnostic behavior")
            routed = manifest.get("routing", {}).get("catalog_crop_ids", [])
            if len(routed) != 1:
                raise PlaceholderError("structural stub must map to exactly one catalog crop")
            crop_slots.add(routed[0])
        else:
            research_checkpoints += 1
        model = _artifact(package_root, manifest["artifacts"]["model"], "model", require_installed)
        labels_path = _artifact(package_root, manifest["artifacts"]["labels"], "labels", True)
        golden_path = _artifact(package_root, manifest["artifacts"]["golden_fixture"], "golden fixture", True)
        labels = _load(labels_path, "labels")
        golden = _load(golden_path, "golden fixture")
        classes = labels.get("classes")
        if not isinstance(classes, list) or [entry.get("index") for entry in classes] != list(range(len(classes))):
            raise PlaceholderError("labels must use a contiguous ordered index")
        if len(classes) != manifest["model_contract"]["output"]["class_count"]:
            raise PlaceholderError("label count does not match model output contract")
        if golden.get("purpose") != "runtime_compatibility_only_not_accuracy_evidence":
            raise PlaceholderError("golden fixture must not claim accuracy evidence")
        if model.is_file():
            installed += 1
        if verify_graph:
            try:
                import onnx
                import onnxruntime as ort
            except ModuleNotFoundError as exc:
                raise PlaceholderError("--verify-graph requires onnx and onnxruntime") from exc
            onnx.checker.check_model(onnx.load(str(model)))
            session = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])
            input_meta = session.get_inputs()[0]
            output_meta = session.get_outputs()[0]
            contract = manifest["model_contract"]
            if input_meta.name != contract["input"]["name"] or output_meta.name != contract["output"]["name"]:
                raise PlaceholderError("ONNX input/output names do not match manifest")
            if output_meta.shape[-1] != contract["output"]["class_count"]:
                raise PlaceholderError("ONNX output shape does not match label count")
            try:
                import numpy as np
            except ModuleNotFoundError as exc:
                raise PlaceholderError("--verify-graph requires numpy") from exc
            input_shape = golden["input"]["shape"]
            tensor = np.zeros(input_shape, dtype=np.float32)
            output = np.asarray(session.run(None, {input_meta.name: tensor})[0], dtype=np.float32)
            output_hash = hashlib.sha256(output.tobytes(order="C")).hexdigest()
            if output_hash != golden["output"]["raw_float32_sha256"]:
                raise PlaceholderError("ONNX output does not match golden fixture")

    if coverage is not None:
        expected_crops = {crop["crop_id"] for crop in coverage.get("crops", [])}
        if len(expected_crops) != 15 or crop_slots != expected_crops:
            raise PlaceholderError("placeholder crop slots do not exactly match top-15 coverage")
        if index.get("coverage_id") != coverage.get("coverage_id"):
            raise PlaceholderError("placeholder index coverage ID does not match top-15 coverage")
    return {
        "package_count": len(packages),
        "installed_count": installed,
        "research_checkpoint_count": research_checkpoints,
        "structural_stub_count": structural_stubs,
        "crop_slot_count": len(crop_slots),
        "status": "research_placeholders_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=Path(__file__).resolve().parents[1] / "models" / "placeholders" / "index.json")
    parser.add_argument("--require-installed", action="store_true")
    parser.add_argument("--verify-graph", action="store_true")
    args = parser.parse_args()
    try:
        report = validate_placeholders(args.index, require_installed=args.require_installed, verify_graph=args.verify_graph)
    except PlaceholderError as exc:
        print(f"placeholder models: FAIL: {exc}")
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
