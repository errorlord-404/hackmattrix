"""Measure repeatable local TFLite inference latency without making device claims."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--warmup-runs", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.runs < 1 or args.warmup_runs < 0:
        raise SystemExit("runs must be positive and warmup-runs cannot be negative")

    import numpy as np
    import tensorflow as tf
    from PIL import Image

    interpreter = tf.lite.Interpreter(model_path=str(args.model))
    interpreter.allocate_tensors()
    input_info = interpreter.get_input_details()[0]
    _, height, width, _ = input_info["shape"]
    image = np.asarray(Image.open(args.image).convert("RGB").resize((width, height)), dtype=np.float32)[None, ...]
    scale, zero = input_info["quantization"]
    if input_info["dtype"] != np.float32:
        if not scale:
            raise SystemExit("Quantized input has no scale")
        image = np.clip(np.round(image / scale + zero), 0, 255).astype(input_info["dtype"])

    def invoke() -> None:
        interpreter.set_tensor(input_info["index"], image)
        interpreter.invoke()

    for _ in range(args.warmup_runs):
        invoke()
    timings = []
    for _ in range(args.runs):
        started = time.perf_counter()
        invoke()
        timings.append((time.perf_counter() - started) * 1000)
    report = {
        "model": str(args.model),
        "runs": args.runs,
        "warmup_runs": args.warmup_runs,
        "mean_ms": float(np.mean(timings)),
        "p50_ms": float(np.percentile(timings, 50)),
        "p95_ms": float(np.percentile(timings, 95)),
        "minimum_ms": float(np.min(timings)),
        "maximum_ms": float(np.max(timings)),
        "evidence_scope": "current host only; not a target-device latency, thermal, memory, or battery result",
    }
    payload = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
