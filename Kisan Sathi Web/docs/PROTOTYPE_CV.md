# Crop-disease prototype

The web prototype uses only the downloaded, manifest-verified research checkpoints in
`models/crop_disease/downloaded/`. Run:

```powershell
python scripts/validate_prototype_models.py --write-profile docs/PROTOTYPE_CV_PROFILE.json
```

The current bundle contains three usable checkpoints:

- `mesabo_resnet50` — ResNet50 / Transformers PyTorch
- `harimitra` — Keras CNN
- `plantvillage_efficientnet` — Keras EfficientNet

Together they provide prototype screening coverage for maize, potato, tomato, citrus,
grape, soybean, and chilli. The API surface is:

- `GET /v1/crop-disease/prototype` — verified installed-model status and crop coverage
- `POST /v1/crop-disease/predict?crop=tomato` — server-side prototype inference

The web screening card calls the second endpoint for the selected prototype crop. The
same registry and router are used by the API, so adding a future model is a registry and
manifest operation rather than a code-path fork.

This is intentionally not a production CV release. `docs/APPROVED_RELEASES.json` remains
fail-closed: browser activation, diagnostic use, Indian field claims, treatment advice,
and production approval are all disabled until the separate field/OOD, agronomist,
redistribution, golden-parity, and rollback evidence exists.
