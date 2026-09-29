# PlantDoc crop-router experiment — 9 September 2026

## Decision

**Rejected for runtime integration.** The crop router continues to require the
farmer to confirm the crop. The backend must not receive this artifact through
`CROP_HEALTH_TFLITE_ROUTER_MODEL_PATH` or use it to select a disease
specialist.

## Reproducible experiment

- Source: [PlantDoc Dataset](https://github.com/pratikkayal/PlantDoc-Dataset),
  revision `5467f6012d78d1c446145d5f582da6096f852ae8`, CC BY 4.0 according to
  its repository README.
- Materializer: `training/materialize_plantdoc_crop_router.py`.
- Labels: `bell_pepper`, `maize` (PlantDoc `Corn`), `potato`, `tomato`.
- Split: bounded source folders `train/` (100 images per label; 400 total) and
  `test/` (16 images per label; 64 total). The source manifest remains only in
  the ignored local data directory.
- Model: ImageNet-pretrained TensorFlow Hub MobileNetV3-Small feature vector,
  staged head warm-up then fine-tuning; seed 42.
- Export evaluated: dynamic-range TFLite, 1,756,896 bytes, SHA-256
  `4a5fe1ec14be15f1ee44862e1b3e7f601cf2bbc624f15315b6cd273a7189c2d3`.

## Results

| Acceptance policy | Coverage | Accepted accuracy | Macro-F1 | Tomato recall |
|---|---:|---:|---:|---:|
| Raw (0.00 score / 0.00 margin) | 100% (64/64) | 64.06% | 0.6018 | 12.50% (2/16) |
| Router gate (0.80 score / 0.15 margin) | 17.19% (11/64) | 100% | 0.2217 | 0% (0/16) |

The apparent 100% accepted accuracy at the router gate is not evidence of a
useful router: it simply rejects 53 of 64 supported images, including every
tomato image. Raw predictions also confuse tomato with potato or bell pepper.
This sample is small and web-sourced, so it cannot support either a positive
performance claim or threshold tuning. It is sufficient to reject this training
run as a demo router.

## Consequence

The product keeps its safer flow: ask the farmer to name or confirm the crop;
then run only the corresponding specialist as screening evidence. A future
router needs consented target-region farmer-phone images, a true
`other_or_unknown` class, field/date/device-disjoint evaluation, calibration
and target-device benchmark evidence before it is even considered for optional
crop suggestion. Crop identification must never autonomously authorize disease
treatment or pump control.
