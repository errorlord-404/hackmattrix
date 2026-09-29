# ML implementation checkpoint — 9 September 2026

## Completed in this checkpoint

1. Restored a balanced controlled tomato dataset from Kaggle
   `emmarex/plantdisease` into the local Kaggle cache.
2. Recreated the deterministic seed-42 specialist split at
   `C:\Users\prana\AppData\Local\Temp\kisansathi-tomato-specialist-benchmark-v2`:
   400 train + 100 validation images for each of early blight, healthy, late
   blight and leaf mold.
3. Fine-tuned TensorFlow Hub MobileNetV3-Large and EfficientNetV2-B0 with the
   same 1,600/400 split and training policy.
4. Exported FP32, dynamic-range and calibrated INT8 TFLite variants.
5. Evaluated all variants and generated a like-for-like comparison against the
   existing MobileNetV3-Small artifact.
6. Selected EfficientNetV2-B0 dynamic TFLite for the explicit controlled demo:
   97.75% raw accuracy, 0.9775 macro-F1, 6.58 MB.
7. Added manifest v0.3 with exact SHA-256 and explicit missing release gates.
8. Connected the launcher to the new model, labels and manifest.
9. Changed backend model evidence to use manifest identity rather than stale
   hard-coded MobileNet metadata.
10. Hardened the trainer so a regressed fine-tuning stage cannot replace a
    better warm-up checkpoint and metadata reports completed, not merely
    planned, training epochs.
11. Added a reusable host-only TFLite latency benchmark utility.
12. Added a bounded PlantDoc external-evaluation importer and evaluated the
    chosen model on a separate tomato/OOD image source.
13. Built and evaluated a bounded four-crop PlantDoc router experiment. It is
    rejected: raw validation accuracy was 64.06% and tomato recall 12.5%; the
    normal confidence gate rejected every tomato image. The runtime remains
    farmer-confirmation-first.
14. Built a source-split PlantDoc external-domain tomato adaptation experiment
    with EfficientNetV2-B0. It is rejected: 55.00% development validation and
    29.17% raw accuracy on the reserved external source-test subset; the
    normal gate accepted none of 24 images.
15. Added the versioned field-data datasheet/capture protocol that connects
    farmer consent and metadata to the existing expert-review and
    field-disjoint split tooling.

## Verification

- `python -m pytest tests -q` from `ml`: 26 passed.
- `python -m pytest tests/test_crop_health.py -q` from `backend`: 9 passed.
- `backend/scripts/run_local_tflite_demo.ps1 -CheckOnly`: artifact and label
  hashes match manifest v0.3; completed output is not approved.
- Live HTTP `POST /v1/diagnoses` with a held-out late-blight image:
  `needs_expert_review`, EfficientNetV2-B0/v0.3 identity, late blight top
  candidate at 0.9235, no treatment and no action authority.
- PlantDoc exploratory cross-domain result: 45.83% raw accuracy on 24 tomato
  images; current gate rejects 15/18 non-tomato images but accepts only 13/24
  known tomato images. The release remains demo-only.

## Important local paths

- Dataset cache:
  `C:\Users\prana\.cache\kagglehub\datasets\emmarex\plantdisease\versions\1\PlantVillage`
- Fixed benchmark split:
  `C:\Users\prana\AppData\Local\Temp\kisansathi-tomato-specialist-benchmark-v2`
- Selected SavedModel (Git-ignored):
  `ml/private-artifacts/tomato-efficientnetv2-b0-benchmark-v2`
- Selected TFLite bundle (Git-ignored):
  `ml/private-artifacts/tomato-efficientnetv2-b0-benchmark-v2-tflite`
- Auditable manifest:
  `ml/releases/crop-health-tfhub-tomato-controlled-demo-v0.3.yaml`
- Detailed benchmark:
  `ml/evaluation/TOMATO_TFHUB_BENCHMARK_2026_09_09.md`
- External-domain warning:
  `ml/evaluation/PLANTDOC_EXTERNAL_CHECK_2026_09_09.md`
- Crop-router rejection record:
  `ml/evaluation/PLANTDOC_CROP_ROUTER_CHECK_2026_09_09.md`
- Tomato adaptation rejection record:
  `ml/evaluation/PLANTDOC_TOMATO_ADAPTATION_CHECK_2026_09_09.md`
- Data-collection protocol:
  `ml/data/DATASHEET.md`

## What remains before a truthful field release

- Collect consented Indian farmer-phone tomato images grouped by farm, date,
  device, stage and disease severity; obtain agronomist labels.
- Create a true unknown/OOD set including other crops, pests, nutrient and water
  stress, soil/background, blur and healthy lookalikes.
- Train/evaluate on farm/date-held-out partitions and measure calibration plus
  confidence intervals.
- Benchmark dynamic and INT8 artifacts on the actual target Qualcomm/Android
  device for p50/p95 latency, memory, heat and battery.
- Review disease classes and treatment content with an agronomist.
- Only then create a signed `approved_for_field_release` manifest. Do not edit
  v0.3 into an approval.

## Continuation prompt

> Continue KisanSathi from `docs/sih26180/ML_CHECKPOINT_2026_09_09.md`. Read
> `ml/evaluation/TOMATO_TFHUB_BENCHMARK_2026_09_09.md`,
> `ml/MODEL_DECISION_RECORD.md`, manifest
> `ml/releases/crop-health-tfhub-tomato-controlled-demo-v0.3.yaml`,
> `backend/AGENTS.md`, `backend/app/services/tflite_crop_health.py`, and
> `backend/scripts/run_local_tflite_demo.ps1` before editing. Preserve the
> explicit demo-only safety boundary. First obtain or inventory independent
> farmer-phone field and unknown/OOD images plus the actual target-device
> specification. Then build reviewed field/date-held-out manifests, evaluate
> EfficientNetV2-B0 dynamic and INT8 using the existing scripts, benchmark both
> on target hardware, and update the release decision only from that evidence.
> Run ML and backend crop-health tests and update backend ChangeLog, Decisions
> and Flow for every backend change. Do not claim PlantVillage accuracy as
> field accuracy and do not allow vision output to trigger treatment or pumps.
> The evaluated PlantDoc router is rejected; do not set its artifact paths in
> the backend. Improve crop routing only with consented target-region,
> field/date/device-disjoint data and a genuine unknown class.
> The PlantDoc tomato-adaptation model is also rejected. Do not refer to its
> source-test folder as a field test and do not use public-image fine-tuning as
> a substitute for target-region farmer-phone data.
