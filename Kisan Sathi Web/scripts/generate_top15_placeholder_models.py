"""Generate deterministic, non-diagnostic ONNX structural stubs for crop slots.

These graphs intentionally emit zero logits. They exist only to exercise model
discovery, lazy loading, tensor contracts, and rollback-safe packaging while
real trained releases are unavailable. The generated manifests make activation
and diagnostic use explicitly invalid.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _artifact(path: str, value: bytes) -> dict[str, Any]:
    return {"path": path, "size_bytes": len(value), "sha256": _sha256_bytes(value)}


def _model_bytes(class_count: int, crop_id: str) -> bytes:
    input_info = helper.make_tensor_value_info("input", TensorProto.FLOAT, ["batch", 3, 224, 224])
    output_info = helper.make_tensor_value_info("logits", TensorProto.FLOAT, ["batch", class_count])
    axes_unsqueeze = numpy_helper.from_array(np.asarray([1], dtype=np.int64), name="unsqueeze_axes")
    zero_weights = numpy_helper.from_array(np.zeros((1, class_count), dtype=np.float32), name="zero_weights")
    nodes = [
        helper.make_node("ReduceMean", ["input"], ["image_mean"], axes=[1, 2, 3], keepdims=0),
        helper.make_node("Unsqueeze", ["image_mean", "unsqueeze_axes"], ["image_mean_column"]),
        helper.make_node("MatMul", ["image_mean_column", "zero_weights"], ["logits"]),
    ]
    graph = helper.make_graph(
        nodes,
        f"kisansathi_{crop_id}_structural_stub",
        [input_info],
        [output_info],
        [axes_unsqueeze, zero_weights],
    )
    model = helper.make_model(
        graph,
        producer_name="kisansathi-placeholder-generator",
        producer_version="1.0",
        opset_imports=[helper.make_opsetid("", 17)],
    )
    model.ir_version = 8
    model.doc_string = "NON-DIAGNOSTIC STRUCTURAL STUB: emits constant zero logits"
    onnx.checker.check_model(model)
    return model.SerializeToString()


def _labels(crop: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "model_id": f"stub-disease-{crop['crop_id']}",
        "taxonomy_status": "draft_requires_agronomist_review",
        "classes": [
            {
                "index": index,
                "label": disease_id.replace("_", " "),
                "crop_id": crop["crop_id"],
                "disease_id": disease_id,
                "catalog_crop_id": crop["crop_id"],
            }
            for index, disease_id in enumerate(crop["classes"])
        ],
    }


def _golden(class_count: int) -> dict[str, Any]:
    output = np.zeros((1, class_count), dtype=np.float32)
    return {
        "schema_version": "1.0",
        "fixture_id": "zero-input-cpu-smoke-v1",
        "purpose": "runtime_compatibility_only_not_accuracy_evidence",
        "runtime": {"name": "onnxruntime", "version": "1.30.0", "provider": "CPUExecutionProvider"},
        "input": {"name": "input", "dtype": "float32", "shape": [1, 3, 224, 224], "generator": "constant_zero"},
        "output": {
            "name": "logits",
            "dtype": "float32",
            "shape": [1, class_count],
            "values": output.tolist(),
            "raw_float32_sha256": hashlib.sha256(output.tobytes(order="C")).hexdigest(),
        },
    }


def _manifest(crop: dict[str, Any], artifacts: dict[str, Any]) -> dict[str, Any]:
    crop_id = crop["crop_id"]
    class_count = len(crop["classes"])
    return {
        "schema_version": "1.0",
        "model_id": f"stub-disease-{crop_id}",
        "version": "structural-stub-v1",
        "status": "structural_stub_untrained",
        "enabled": False,
        "diagnostic_capability": False,
        "roles": ["disease_specialist_integration_slot"],
        "routing": {
            "source_crop_ids": [crop_id],
            "catalog_crop_ids": [crop_id],
            "farmer_confirmation_required": True,
            "unsupported_crop_action": "provider_unavailable",
        },
        "source": {
            "kind": "locally_generated_structural_stub",
            "generator": "scripts/generate_top15_placeholder_models.py",
            "training_data": None,
            "trained_weights": False,
        },
        "artifacts": artifacts,
        "model_contract": {
            "format": "onnx",
            "ir_version": 8,
            "opset": 17,
            "input": {"name": "input", "dtype": "float32", "shape": ["batch", 3, 224, 224]},
            "output": {"name": "logits", "dtype": "float32", "shape": ["batch", class_count], "class_count": class_count},
            "behavior": "constant_zero_logits_non_diagnostic",
        },
        "preprocessing": {
            "color_space": "RGB",
            "resize": [224, 224],
            "rescale": "uint8_to_float32_0_1",
            "normalization": {"mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
        },
        "runtime": {
            "server_cpu": "compatibility_test_only",
            "browser_wasm": "compatibility_test_only",
            "browser_webgpu": "not_claimed",
            "lazy_load": True,
        },
        "license": {
            "artifact_owner": "Kisan Sathi Web project",
            "redistribution_status": "project_generated_code_artifact",
            "training_data_terms": "not_applicable_no_training_data",
        },
        "evidence": {
            "training": "absent",
            "accuracy": "absent",
            "independent_indian_farmer_phone_field_test": "missing",
            "unknown_ood_test": "missing",
            "agronomist_review": "missing",
            "taxonomy_review": "missing",
        },
        "approval": {
            "release_approved": False,
            "activation_prohibited": True,
            "reason": "Untrained constant-output graph for integration testing only.",
            "missing_gates": [
                "trained_weights",
                "independent_indian_farmer_phone_field_test",
                "unknown_ood_evaluation",
                "agronomist_review",
                "browser_server_parity",
                "release_redistribution_review",
                "rollback_release_identity",
            ],
        },
        "rollback": {"previous_approved_release": None},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] / "models" / "placeholders" / "top-15-india.json")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1] / "models" / "placeholders")
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    root = args.root.resolve()
    packages = [{"model_id": "placeholder-ktt-mobilenetv3-int8", "kind": "research_checkpoint", "manifest": "ktt-mobilenetv3-int8/manifest.json"}]
    for crop in config["crops"]:
        package_name = f"stub-disease-{crop['crop_id']}"
        package_root = root / package_name
        (package_root / "golden").mkdir(parents=True, exist_ok=True)

        model_bytes = _model_bytes(len(crop["classes"]), crop["crop_id"])
        labels_bytes = _json_bytes(_labels(crop))
        golden_bytes = _json_bytes(_golden(len(crop["classes"])))
        (package_root / "model.onnx").write_bytes(model_bytes)
        (package_root / "labels.json").write_bytes(labels_bytes)
        (package_root / "golden" / "zero-input.json").write_bytes(golden_bytes)
        artifacts = {
            "model": _artifact("model.onnx", model_bytes),
            "labels": _artifact("labels.json", labels_bytes),
            "golden_fixture": {
                **_artifact("golden/zero-input.json", golden_bytes),
                "purpose": "runtime_compatibility_only_not_accuracy_evidence",
            },
        }
        (package_root / "manifest.json").write_bytes(_json_bytes(_manifest(crop, artifacts)))
        packages.append({"model_id": package_name, "kind": "structural_stub", "crop_id": crop["crop_id"], "manifest": f"{package_name}/manifest.json"})

    index = {
        "schema_version": "2.0",
        "coverage_id": config["coverage_id"],
        "policy": {
            "activation_allowed": False,
            "catalog_registration_allowed": False,
            "diagnostic_use_allowed": False,
            "purpose": "research_and_compatibility_only",
        },
        "packages": packages,
    }
    (root / "index.json").write_bytes(_json_bytes(index))
    print(json.dumps({"crop_slots": len(config["crops"]), "package_count": len(packages), "root": str(root)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
