"""Generate a deterministic ONNX smoke-test fixture for a placeholder model."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    package_root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    model_path = package_root / manifest["artifacts"]["model"]["path"]
    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    input_meta = session.get_inputs()[0]
    shape = [1 if not isinstance(value, int) else value for value in input_meta.shape]
    tensor = np.zeros(shape, dtype=np.float32)
    outputs = session.run(None, {input_meta.name: tensor})
    output_meta = session.get_outputs()[0]
    output = np.asarray(outputs[0], dtype=np.float32)
    fixture = {
        "schema_version": "1.0",
        "fixture_id": "zero-input-cpu-smoke-v1",
        "purpose": "runtime_compatibility_only_not_accuracy_evidence",
        "runtime": {
            "name": "onnxruntime",
            "version": ort.__version__,
            "provider": "CPUExecutionProvider"
        },
        "input": {
            "name": input_meta.name,
            "dtype": "float32",
            "shape": shape,
            "generator": "constant_zero"
        },
        "output": {
            "name": output_meta.name,
            "dtype": "float32",
            "shape": list(output.shape),
            "values": output.tolist(),
            "raw_float32_sha256": hashlib.sha256(output.tobytes(order="C")).hexdigest()
        }
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"fixture": str(args.output), "output_sha256": fixture["output"]["raw_float32_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

