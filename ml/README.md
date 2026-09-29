# KisanSathi ML workspace

This directory is the versioned home for the crop-health model package, training
manifests, model cards, evaluation evidence and release metadata. It is not a
place to download unreviewed model weights into Git.

The current technical decision and implementation sequence are in
[`MODEL_DECISION_RECORD.md`](MODEL_DECISION_RECORD.md). The first release
contract is in [`contracts/crop-health-result.schema.json`](contracts/crop-health-result.schema.json).

Before any farmer-photo collection, use [the field-data datasheet](data/DATASHEET.md).
It defines consent, anonymised grouping, agronomist review and field-disjoint
requirements for the review-queue and split tooling.

`orchestration/hierarchical_inference.py` is the executable local chain:
router checkpoint → farmer confirmation when needed → only a released
crop-specific checkpoint. It fails closed when a specialist is absent.

## Rules

- A model may only call a crop/disease class that appears in its release
  manifest. Everything else is `unknown`, `unsupported_crop`, or
  `needs_expert_review`.
- Keep images, labels, train/validation/test split manifests and model weights
  outside Git unless they are intentionally licensed and small. Commit hashes,
  checksums, licenses and access instructions instead.
- Do not use a classifier score as a calibrated probability until calibration
  has been evaluated on an independent local field set.
- A vision result is screening evidence. Treatment text comes from a reviewed,
  versioned crop-content pack, never from free-form model output.
- The phone must remain capable of local inference with WAN disabled. A hosted
  API is permitted only as an optional secondary opinion.

The current TensorFlow Hub dynamic-TFLite controlled demo is documented in
[`releases/crop-health-tfhub-tomato-controlled-demo-v0.3.yaml`](releases/crop-health-tfhub-tomato-controlled-demo-v0.3.yaml),
with its like-for-like backbone comparison in
[`evaluation/TOMATO_TFHUB_BENCHMARK_2026_09_09.md`](evaluation/TOMATO_TFHUB_BENCHMARK_2026_09_09.md).
It is versioned for auditability, explicitly not a field-release manifest.

## Codex desktop research bundle

The original Electron/Codex app can use the available downloaded checkpoints
through [`model_registry.json`](model_registry.json). The registry is lazy and
framework-neutral: it supports legacy Keras, current Keras, Transformers
PyTorch, and ONNX Runtime entries without importing every runtime at startup.

Install the local runtime files from the checked-in research sources:

```powershell
.\backend\scripts\install_crop_model_bundle.ps1
```

Then run either `npm run demo:desktop` (automatic when the bundle is present)
or `npm run demo:codex-models` for a backend-only model smoke run. The Codex
`diagnose_crop` tool continues to require farmer crop confirmation and returns
ranked candidates plus per-model evidence. Every result remains
`needs_expert_review`; these source checkpoints do not have Indian field/OOD
evaluation or agronomist approval and are not production diagnostics.

To add a future crop or model, place its runtime artifacts under the ignored
`ml/private-artifacts/crop-disease/models/` directory, add one metadata entry
to the registry, and select an adapter already supported by the registry (or
add a new lazy adapter). Keep source revision, license, preprocessing, labels,
and reproducible hashes in the model's provenance manifest.
