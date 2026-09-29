# Tomato TF Hub controlled benchmark — 9 September 2026

## Outcome

EfficientNetV2-B0 is the strongest controlled-image tomato specialist tested in
this repository. Its dynamic-range TFLite export achieved **97.75% raw
accuracy** and **0.9775 macro-F1** on the same deterministic 400-image
PlantVillage validation split. This improves raw accuracy by 2.25 percentage
points over the previous MobileNetV3-Small runtime artifact.

This is not a field-accuracy claim. The benchmark lacks Indian farmer-phone
images, a field/date-held-out test, unknown/OOD images, agronomist review and
target-device latency, thermal and battery measurements.

## Like-for-like setup

- Source: Kaggle `emmarex/plantdisease`, an extracted PlantVillage mirror.
- Labels: `early_blight`, `healthy`, `late_blight`, `leaf_mold`.
- Sampling: 500 images per label, deterministic seed 42.
- Split: 400 training and 100 validation images per label (1,600/400 total).
- Input: 224 × 224 RGB, scaled by `1/255` inside the model.
- Transfer learning: three frozen-head warm-up epochs, then ImageNet backbone
  fine-tuning at `3e-5` with field-like augmentation.
- Export: FP32, dynamic-range and representative-data-calibrated full INT8.

## Results

| Dynamic TFLite candidate | Size | Accuracy | Macro-F1 | Early blight recall | Healthy recall | Late blight recall | Leaf mold recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| MobileNetV3-Small (previous) | 1.76 MB | 95.50% | 0.9546 | 93% | 100% | 90% | 99% |
| MobileNetV3-Large | 4.58 MB | 96.50% | 0.9650 | 89% | 100% | 98% | 99% |
| **EfficientNetV2-B0** | **6.58 MB** | **97.75%** | **0.9775** | **97%** | **100%** | **95%** | **99%** |

An XNNPACK workstation-only smoke benchmark (50 timed runs after five warm-ups)
measured about 24.8 ms mean for MobileNetV3-Small, 69.9 ms for
MobileNetV3-Large and 63.2 ms for EfficientNetV2-B0. These figures establish
only that the artifacts execute locally; they are not Qualcomm/Android latency,
thermal, memory or battery evidence.

EfficientNetV2-B0 full INT8 scored 96.50%, a 1.25-point loss from dynamic
TFLite. It remains unselected until measured on the target Qualcomm/Android
device; compactness alone is not sufficient evidence.

With the runtime abstention gate (`top-1 >= 0.70`, margin `>= 0.15`), the
dynamic model accepted 381/400 supported images (95.25% coverage) and was
98.69% accurate among accepted images. Rejection performance on true unknowns
is unavailable, so these thresholds are provisional.

## Artifacts and integrity

- SavedModel: `ml/private-artifacts/tomato-efficientnetv2-b0-benchmark-v2/`
- TFLite exports: `ml/private-artifacts/tomato-efficientnetv2-b0-benchmark-v2-tflite/`
- Dynamic SHA-256: `7285ee01a1e808b029f6578956735edb73774c192173b98b837617e61ccc300c`
- Labels SHA-256: `9250ed3c6db2219237dc307a11deccdeb7fffd6bfffd421e1e4ce363f98e55ab`
- Comparable machine-readable report (ignored local evidence):
  `ml/private-artifacts/tomato-backbone-comparison-v2.json`
- Auditable demo manifest:
  `ml/releases/crop-health-tfhub-tomato-controlled-demo-v0.3.yaml`

The weights and dataset are intentionally ignored by Git. The manifest binds
the exact local bytes and keeps distribution prohibited until licensing and
release gates are resolved.

## Runtime decision

The explicit controlled-demo launcher now selects the EfficientNetV2-B0
dynamic artifact and supplies its manifest to the backend. The manifest status
remains `demo_only_rejected_for_field_release`, so the API must return ranked
screening evidence under `needs_expert_review`; it cannot produce treatment or
trigger irrigation/pump action.

## Next evidence required

1. Gather consented tomato images across farms, phones, stages, lighting and
   disease severity, with agronomist labels and field/date grouping.
2. Build a separate non-tomato, abiotic-stress, pest, soil/background, blurry
   and healthy-lookalike OOD challenge set.
3. Re-train and evaluate using field/date-held-out partitions; report confidence
   intervals and calibration, not only accuracy.
4. Benchmark dynamic and INT8 artifacts on the actual target phone/Qualcomm
   hardware for p50/p95 latency, memory, thermal behavior and battery cost.
5. Approve a field manifest only after artifact integrity, agronomist review,
   unknown rejection and treatment-content gates pass.
