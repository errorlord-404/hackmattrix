"""Convert a fine-tuned SavedModel to float and calibrated INT8 TFLite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saved-model", type=Path, required=True)
    parser.add_argument("--representative-data", type=Path, required=True, help="Label-folder root used only for quantization calibration")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=100)
    args = parser.parse_args()
    try:
        import tensorflow as tf
    except ImportError as exc:
        raise SystemExit("Install ml/training/requirements-tfhub.txt in a dedicated training environment.") from exc
    metadata = json.loads((args.saved_model / "kisansathi_metadata.json").read_text(encoding="utf-8"))
    size = int(metadata["image_size"])
    files = [path for suffix in ("*.jpg", "*.jpeg", "*.png") for path in args.representative_data.rglob(suffix)][:args.samples]
    if not files:
        raise SystemExit("Representative-data must contain JPG/JPEG/PNG images.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    float_converter = tf.lite.TFLiteConverter.from_saved_model(str(args.saved_model))
    (args.output_dir / "model-fp32.tflite").write_bytes(float_converter.convert())

    # Dynamic-range quantization is an intermediate CPU-friendly candidate.
    # It is not equivalent to fully-integer accelerator deployment, but its
    # accuracy is valuable evidence when diagnosing an INT8 calibration loss.
    dynamic_converter = tf.lite.TFLiteConverter.from_saved_model(str(args.saved_model))
    dynamic_converter.optimizations = [tf.lite.Optimize.DEFAULT]
    (args.output_dir / "model-dynamic.tflite").write_bytes(dynamic_converter.convert())

    def representative_dataset():
        for path in files:
            image = tf.io.decode_image(tf.io.read_file(str(path)), channels=3, expand_animations=False)
            image = tf.image.resize(image, (size, size))
            yield [tf.cast(tf.expand_dims(image, 0), tf.float32)]

    int8_converter = tf.lite.TFLiteConverter.from_saved_model(str(args.saved_model))
    int8_converter.optimizations = [tf.lite.Optimize.DEFAULT]
    int8_converter.representative_dataset = representative_dataset
    int8_converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    int8_converter.inference_input_type = tf.uint8
    int8_converter.inference_output_type = tf.uint8
    (args.output_dir / "model-int8.tflite").write_bytes(int8_converter.convert())
    (args.output_dir / "labels.json").write_text(json.dumps(metadata["classes"], indent=2), encoding="utf-8")
    print(f"Exported FP32, dynamic-range, and calibrated INT8 TFLite models to {args.output_dir}")


if __name__ == "__main__":
    main()
