# Model card — `crop-health-baseline-v0.1` (not trained)

**Status:** design placeholder — it must not be enabled in the app.

| Field | Release requirement |
|---|---|
| Intended use | Guided screening of a declared crop and a declared, limited class set on the chosen Android phone. |
| Model family | MobileNetV3-Large or EfficientNet-Lite0 classifier, with an INT8 candidate after accuracy comparison. |
| Target output | Supported class, `unknown`, `unsupported_crop`, or `needs_expert_review`; never a treatment dose. |
| Input | Guided RGB crop photo; capture-quality gate; field/crop/stage metadata where available. |
| Non-use | Universal disease detection, diagnosis of nutrient deficiency from a photo alone, pesticide recommendation, legal/insurance evidence, or autonomous irrigation. |
| Data | PlantVillage may be used only as warm-start data. Training requires target-crop, target-region, in-field images. The independent final test set must contain farmer-phone images never seen during development. |
| Evaluation gate | Per-actionable-class recall and macro-F1, unknown rejection, confusion with healthy/deficiency/water stress, float-vs-INT8 delta, latency, size, thermal and offline measurements. |
| Release blockers | Crop, region, phone/SoC, class list, image/data consent, agronomist labels, test split, calibration, artifact hash, license and reviewed action content. |
| Rollback | Android retains prior verified model/content package; manifest includes version, SHA-256, compatibility, expiry and rollback target. |

See `MODEL_DECISION_RECORD.md` for the validation protocol and selection rationale.
