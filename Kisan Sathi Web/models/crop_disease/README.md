# Crop-disease model subsystem

This offline-first, registry-driven service supports the canonical 26-crop Indian taxonomy. Model selection stays in `registry.json`, not application code.

`VERIFIED_DOWNLOADABLE` means an upstream artifact and license are known. It does **not** mean Indian field validation, agronomist approval, or release approval. The router always returns this limitation with a prediction.

## Operator flow

From `Kisan Sathi Web`, explicitly download and checksum an artifact:

```powershell
python -m pip install -r models/crop_disease/requirements.optional.txt
python -m models.crop_disease.downloader --model mesabo_resnet50
python -m models.crop_disease.downloader --model mesabo_resnet50 --verify
```

To reproduce the complete allowlisted research setup on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_research_models.ps1 -InstallDependencies
powershell -ExecutionPolicy Bypass -File scripts/setup_research_models.ps1 -VerifyOnly
```

The registry pins each downloaded source to an immutable upstream commit. The
script downloads only entries marked `VERIFIED_DOWNLOADABLE`, writes a
per-model `download-manifest.json`, and verifies every file hash. It never
copies assets into `models/releases`, changes the model catalog, or edits
`docs/APPROVED_RELEASES.json`.

Server-side ONNX candidates use the same preprocessing/labels contract as the
browser path. `OnnxImageClassifier` loads only local files through
`onnxruntime`; it never downloads during inference and prefers an explicitly
named `model.onnx`, INT8, or FP32 artifact.

Keras sources remain blocked unless the upstream artifact includes an authoritative ordered class-label file. The downloader writes it as `labels.json`; it never guesses output indexes.

Artifacts live in `models/crop_disease/downloaded/` (or `CROP_MODEL_DIR`) and have per-model SHA-256 manifests. Mount that directory as persistent storage and do not commit models.

The authenticated API accepts raw `image/*` content:

```text
POST /v1/crop-disease/predict?crop=tomato&top_k=3
Content-Type: image/jpeg
```

Use `/v1/crop-disease/models`, `/models/{id}`, `/crops`, and `/coverage` to inspect availability.

## Prototype mode

For the current web prototype, verify the locally downloaded research
checkpoints and generate the machine-readable profile:

```powershell
python scripts/setup_research_models.ps1 -VerifyOnly
python scripts/validate_prototype_models.py --write-profile docs/PROTOTYPE_CV_PROFILE.json
```

Prototype inference is available through `POST /v1/crop-disease/predict?crop=...`
for the crops returned by `GET /v1/crop-disease/prototype`. This path uses only
manifest-verified downloads and remains explicitly non-diagnostic. It does not
change `docs/APPROVED_RELEASES.json` or the production browser-release gate.

## Adding a model

1. Train/fine-tune in `models/pipeline`, then export the target runtime artifact.
2. Add exact crop coverage, license, revision, preprocessing, and label source to the registry.
3. Add a local-only adapter if a new framework is required.
4. Generate manifests, parity fixtures, OOD/field evidence, and agronomist sign-off before promotion to `docs/APPROVED_RELEASES.json`.

Rice and unsupported crops intentionally return a structured unavailable result until a qualified specialist exists; no placeholder prediction is fabricated.
