# Local controlled-image demo artifact

`plantvillage-crop-router-demo-v0.1.pt` is intentionally excluded from Git. It
is a local **demo** artifact, created on 7 September 2026 to prove the crop
routing code path; it is not a released model and must not be enabled in the
backend or shown as field-validated AI.

| Field | Value |
|---|---|
| Architecture | ImageNet-initialized MobileNetV3-Small |
| Labels | `bell_pepper`, `maize`, `potato`, `tomato` |
| Data | 80 PlantVillage controlled leaf images, 20 per crop; deterministic 16/4 train/validation per crop |
| Training | 3 epochs, batch size 8, seed 42, learning rate 0.0003 |
| Best validation accuracy | 0.8125 (13/16 images) |
| SHA-256 | `2e4f5dc0bc1a1774901a273ef146d9beddeed39968759344dee51542cf73e84b` |
| Release status | **Blocked**: tiny controlled split, no farmer-phone field test, no unknown class, no calibration, no target Android benchmark, no agronomy approval |

Run a local check:

```powershell
python ml/training/predict_classifier.py `
  --checkpoint ml/demo_artifacts/plantvillage-crop-router-demo-v0.1.pt `
  --image C:\path\to\crop-photo.jpg
```

The UI must still ask the farmer to confirm the crop. This artifact is an
engineering smoke test, not crop-identification evidence.

The matching tomato-specialist downloader exists under
`ml/training/download_plantvillage_tomato_specialist_demo.py`, but its public
mirror download was deliberately stopped after slow responses on 7 September
2026. No partial specialist artifact exists. Run it with a reliable approved
dataset mirror before training the specialist checkpoint.

## Tomato specialist demo — now trained from a Kaggle PlantVillage mirror

`plantvillage-tomato-specialist-demo-v0.1.pt` is also ignored by Git and was
fine-tuned from ImageNet-initialized MobileNetV3-Large on 7 September 2026.

| Field | Value |
|---|---|
| Labels | `healthy`, `early_blight`, `late_blight`, `leaf_mold` |
| Dataset | Public `emmarex/plantdisease` Kaggle PlantVillage mirror; selected four tomato folders only |
| Split | 100 images/label, deterministic 80/20 train/validation, seed 42 |
| Training | 4 epochs, batch size 16, learning rate 0.0003, CUDA |
| Artifact SHA-256 | `235ea9691283c1bb10c3223d2c623cb4f839476e0fb4ccad64fbbcc7dc2a731f` |
| Validation accuracy / macro-F1 | 0.725 / 0.656356 on 80 controlled images |
| Per-class recall | early blight 0.10; healthy 1.00; late blight 0.80; leaf mold 1.00 |
| Release status | **Rejected for field release.** Early-blight recall and macro-F1 are below the project release targets; data is controlled-image only and lacks unknown/OOD testing. |

The model is valuable as an end-to-end orchestration proof: a farmer-confirmed
tomato sample reaches the specialist and returns transparent candidates. It must
continue to return `needs_expert_review` outside this controlled demo until it
is retrained with more local field data, an explicit unknown class, calibrated
thresholds and an independent field-held-out evaluation.

## TensorFlow Hub MobileNetV3 / TFLite controlled benchmark

The local ignored directory `ml/private-artifacts/` now also contains a
TensorFlow Hub MobileNetV3-Small tomato specialist. It was ImageNet-initialized
and full-fine-tuned for 8 epochs on the same 320/80 four-label controlled split
as the model above. This is a benchmark, not an approved artifact.

| Candidate | Size | Controlled validation accuracy | Decision |
|---|---:|---:|---|
| Keras SavedModel | n/a | 0.7625 | Better than the earlier 0.725 smoke test; still field-unvalidated |
| FP32 TFLite | 6,149,072 bytes | 0.7500 | Development reference only |
| Dynamic-range TFLite | 1,756,896 bytes | 0.7625 | Compact CPU **demo candidate only** |
| Fully INT8 TFLite | 1,877,528 bytes | 0.6625 | Rejected: quantization loss is too large |

Dynamic TFLite SHA-256:
`c5493e3b774a9d0cfd8f589891ee1e5ed53fff5c45ac76179979440f58c0670b`.
The TensorFlow Hub handle is
`https://tfhub.dev/google/imagenet/mobilenet_v3_small_100_224/feature_vector/5`.
No candidate has an unknown/OOD class, field-held-out result, per-class release
recall, agronomist approval or phone latency measurement. Do not enable this
artifact in the backend as a production provider.

## Superseding larger controlled TFLite demo (v0.2)

The integrated `local_tflite_demo` uses the ignored dynamic-range artifact at
`ml/private-artifacts/tomato-mobilenetv3-tfhub-large-demo-tflite/model-dynamic.tflite`,
not the smaller benchmark above. It was fine-tuned with the same TF Hub
MobileNetV3-Small backbone using 1,600 training and 400 held-out validation
PlantVillage images (400/100 per label).

| Metric | Result |
|---|---:|
| Keras validation accuracy | 0.9575 |
| Dynamic-range TFLite accuracy | 0.9550 |
| Early blight recall | 0.93 |
| Healthy recall | 1.00 |
| Late blight recall | 0.90 |
| Leaf mold recall | 0.99 |
| Dynamic TFLite SHA-256 | `b16a6c0966cd0c2c0c61a7ba85ac77b7e736ded451fe9f2c391c77150cfdd69b` |

This result is only a larger **controlled-image** benchmark. The full INT8
candidate scored 0.9075, with late-blight recall 0.76, and remains rejected.
The version-controlled release boundary is
`ml/releases/crop-health-tfhub-tomato-controlled-demo-v0.2.yaml`. Neither
artifact is a field release or authorised treatment engine.
