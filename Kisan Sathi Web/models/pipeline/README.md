# Crop model lifecycle

This directory provides a framework-neutral registry and optional training,
export, quantization and candidate-packaging adapters. It does not contain an
approved diagnostic model and it cannot grant approval.

## Inspect the registry

From `Kisan Sathi Web/`:

```powershell
$env:PYTHONPATH = "models/pipeline"
python -m model_pipeline registry-validate
python -m model_pipeline recipe-validate
python -m model_pipeline doctor
```

After packaging a candidate, create a deterministic evidence report without
granting approval:

```powershell
python -m model_pipeline evaluate-release `
  --candidate models/candidates/<candidate-id>/manifest.json `
  --output models/candidates/<candidate-id>/evidence/eval-report.json
```

The report records artifact hashes and automated/human gate state. It never
edits `docs/APPROVED_RELEASES.json` and remains `release_ready: false` until
the separately governed human approval process is complete.

The same CLI exposes the repeatable candidate operations:

```powershell
python -m model_pipeline package-candidate --source-root build/model --destination build/candidate-id --metadata candidate.json --artifacts artifacts.json
python -m model_pipeline register-candidate --manifest build/candidate-id/manifest.json --models-root models
python -m model_pipeline quantize-onnx --source build/model-fp32.onnx --destination build/model-int8.onnx --mode static-int8
```

Static INT8 requires a representative calibration reader and therefore should
normally be invoked through `model_pipeline.quantization.quantize_onnx` with
`ArrayCalibrationReader`; the CLI refuses to imply calibration when none is
provided.

The checked-in recipe catalog contains one `15 crops + unknown` router and 15
crop specialists. Every specialist includes `healthy`, its draft disease
taxonomy, and `unknown`. The taxonomy still requires agronomist review.

## Optional environments

Install only the backend required by a training job, preferably in separate
virtual environments:

```powershell
python -m pip install -r models/pipeline/requirements-core.txt
python -m pip install -r models/pipeline/requirements-pytorch.txt
python -m pip install -r models/pipeline/requirements-tensorflow.txt
python -m pip install -r models/pipeline/requirements-onnx.txt
```

Versions in optional requirement groups are training-tool candidates until the
dependency approval record explicitly approves them. Installing a framework or
creating an artifact never changes release status.

## Lifecycle

```text
dataset manifest
  -> recipe + backbone
  -> framework adapter training
  -> native weights-only checkpoint
  -> ONNX export
  -> representative static INT8 quantization
  -> field/OOD/calibration/quantization evaluation
  -> disabled candidate bundle
  -> agronomist + rights + release review
  -> APPROVED_RELEASES.json
  -> activation and rollback tests
```

Use ONNX for deployment. PyTorch state dictionaries, Keras files and SavedModel
directories are training artifacts. Pickle is not a deployment format.

See `docs/MODEL_TRAINING_AND_REGISTRATION.md` for the verification and
registration checklist.
