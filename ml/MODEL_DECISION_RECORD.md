# Pranav ML/DL decision record — crop-health baseline

**Version:** 1.0
**Date:** 7 September 2026
**Owner:** Pranav (ML/DL and Codex integration)
**Decision status:** implementation-ready once crop, pilot locality and Android target are selected

## 1. What the codebase actually provides today

| Area | Evidence in this repository | Current state |
|---|---|---|
| Crop photo journey | `src/pages/FieldTools.jsx` accepts JPEG/PNG/WebP and calls `farmStateApi.createDiagnosis`. | Present, but only uploads a photo. |
| Backend | `backend/app/routers/assistants.py` validates file signature, stores the image and writes `inconclusive`; `DIAGNOSIS_PROVIDER` defaults to `unconfigured`. | Safe failure, **not inference**. |
| Agent / Codex | `diagnose_crop` in `agent/src/kisansathi_agent/tools.py` forwards the image to `/v1/diagnoses` and preserves unavailable/inconclusive responses. | Correct adapter, no model behind it. |
| Desktop harness | `desktop/` supplies local images to Codex when possible and otherwise uses the diagnosis service. | Optional richer interface, not a field inference runtime. |
| ML assets | No `ml/`, model artifact, registry, model card, dataset manifest, calibration or evaluation set existed before this record. | Missing. |
| Required D1 behavior | `docs/sih26180/PRD.md`, HEALTH-01..04 and OPS-01. | One crop/region/device, local versioned inference, explicit unknowns, pest evidence and rollback are required. |

**Consequence:** calling an LLM/vision API the "CNN model" would not satisfy D1. It can accelerate the web demo, but it cannot prove local/offline or validated field behavior.

## 2. Scope decision: narrow the first release

Before training, the team must sign this single line:

> `Supported crop = ____ ; pilot district/state = ____ ; phone/SoC = ____ ; actionable health classes = ____ ; supported pest classes = ____.`

If the team has no decision yet, use **tomato in one pilot locality** as a *working proposal*, not a claim: it is well represented in public disease datasets and makes guided leaf/fruit capture practical. A rice or cotton choice is equally possible but needs crop-specific field data and different pest classes. Do not combine tomato, rice, wheat, cotton and every horticulture crop in v0.1.

### v0.1 output policy

1. The app verifies photo quality (focus, exposure, crop/leaf sufficiently visible) and known crop/field where possible.
2. A local classifier considers only the release label list.
3. It returns a class only when calibrated acceptance and top-1/top-2 margin gates pass; otherwise it returns `unknown` or `needs_expert_review`.
4. A detected pest must be shown with a box/count only when a separate detector was trained and evaluated for that declared pest set.
5. Yellowing/necrosis becomes **possible stress**, with water/stage/lab-context alternatives; it must not issue a nutrient dose from pixels or low-cost NPK probe values.
6. The agent explains the versioned result and fetches only reviewed crop-pack content. It never upgrades an unknown visual result into a confident disease label.

## 3. Curated pretrained-model and repository map

This is a decision-oriented catalogue, not an impossible claim to enumerate every checkpoint on Hugging Face/Kaggle/GitHub. Every candidate below has a clear role, deployment fit and limitation.

| Candidate / source | Useful role | Edge fit | Use in KisanSathi? | Important boundary |
|---|---|---|---|---|
| [MobileNetV3](https://arxiv.org/abs/1905.02244) pretrained on ImageNet | Compact image-classifier backbone for a crop-specific leaf/fruit classifier. | Strong; export INT8 to TFLite/ONNX. | **Small = router baseline; Large = fine-tunable specialist benchmark.** | It is not plant-disease-trained; fine-tune with target field images. |
| [EfficientNet-Lite / TensorFlow Lite](https://blog.tensorflow.org/2020/04/whats-new-in-tensorflow-lite-from-devsummit-2020.html) | Compact classifier alternative. | Strong; TensorFlow documents conversion to TFLite for on-device inference. | **Benchmark against MobileNetV3.** | Select by measured local accuracy/latency, not paper reputation. |
| [PlantVillage](https://github.com/spMohanty/PlantVillage-Dataset) | Public warm-start classification data: 54,306 leaf images, 14 crops/26 diseases. | Dataset, not an acceptable deployed model. | Use only for initial training/augmentation. | Mostly controlled leaf imagery; it cannot be the independent field test set. |
| [PlantDoc](https://github.com/pratikkayal/PlantDoc-Dataset) | Smaller in-the-wild-ish crop disease set with classification and detection variants. | Training/evaluation aid. | Use for auxiliary/domain-shift evaluation after license review. | Too small and heterogeneous to establish local-crop performance alone. |
| [PlantSeg](https://github.com/tqwei05/PlantSeg) | Lesion segmentation data (11,400+ images/115 diseases) and baselines. | Server/GPU research first. | Optional Phase 2: lesion area/evidence overlay. | Its own baseline scores show this is not a plug-in diagnostic model; do not put it on the MVP critical path. |
| [YOLO11 / YOLO26](https://docs.ultralytics.com/models/) | Fine-tunable object detector for **declared pests** or a visible lesion/fruit defect. | Nano variant can be edge feasible after export/profiling. | Use only for one defined pest detector if boxes/counts are a demo requirement. | COCO weights do not detect crop pests. Ultralytics documents AGPL-3.0 or enterprise licensing; resolve licensing before product distribution. |
| [DINOv2](https://github.com/facebookresearch/dinov2) | Robust visual embeddings for label review, nearest-example retrieval, active learning or OOD experiments. | Generally heavier than classifier baseline. | Offline training/review tool, optional server fallback. | Embeddings are not a disease diagnosis or calibrated unknown detector by themselves. |
| [SAM 2](https://github.com/facebookresearch/segment-anything-2) | Human-guided crop/leaf/lesion segmentation, optionally for annotation. | Too heavy/complex for first-phone baseline. | Annotation and research only. | Segmentation does not identify a disease; do not confuse a mask with a diagnosis. |
| [crop.health API](https://crop.kindwise.com/demo/) | Hosted secondary opinion; vendor says it covers ~300 health issues across 23 crops. | Requires internet, key, cost and consent. | **Fast web-demo fallback only**, behind server-side provider adapter. | Must preserve candidate output/provenance and still return inconclusive on outage; vendor result is not local validation. |
| [plant.health API](https://www.kindwise.com/plant-health) | Broad visual triage API with multilingual details. | Hosted. | Not preferred for food-crop MVP; optional comparison provider. | Vendor explicitly distinguishes it from crop.health and notes ambiguity/look-alikes. |
| [OpenAI Responses image inputs](https://developers.openai.com/api/reference/cli/resources/responses/methods/create) | Structured image-quality checklist, farmer-language explanation or expert-review summary. | Hosted; no local runtime. | Optional assistant layer only. | Do not use as a disease classifier or treatment authority. Apply explicit consent and retention controls; image inputs are accepted by the API but data controls must be reviewed. |
| [Roboflow Hosted / self-hosted Inference](https://docs.roboflow.com/deploy/serverless-hosted-api-v2) | Train/host a team-owned classifier or detector and receive structured boxes/classifications through HTTP; can also be self-hosted. | Hosted by default; self-hosting is possible but is not an Android replacement. | Good short-term training/annotation and connected detector demo option. | It hosts **our** trained model; it is not a general agriculture diagnosis API. Keep keys server-side and evaluate the exact deployed version. |
| [Gemini image understanding](https://ai.google.dev/gemini-api/docs/image-understanding) / Google Vision labels | General multimodal/image-label second opinion or capture-quality assistance. | Hosted. | Optional comparison/explanation only. | Neither documentation claims a crop-disease diagnostic model; no use as a released disease authority. |
| [Google Cloud Vision Web Detection](https://docs.cloud.google.com/vision/docs/detecting-web) | Finds web entities, matching pages and visually similar images from a submitted photo. | Hosted; requires a Google Cloud project/credentials and sends the image externally. | Optional consented research-evidence lookup after a local/hosted candidate exists. | It finds web references, not a verified diagnosis. Never vote its results into a disease score; show source URLs and freshness to the farmer/expert. |

### Runtime choice

Use **TensorFlow Lite/LiteRT first** for the classifier because the selected small backbones export directly and Android has a maintained image-classifier task API. Use **ONNX Runtime Mobile** only if the selected training/export stack needs it; it supports Android CPU/XNNPACK/NNAPI and has a Qualcomm QNN path, but performance is model/device-specific and must be benchmarked on the actual phone. See [ONNX Runtime mobile deployment](https://onnxruntime.ai/docs/tutorials/mobile/) and [Android/QNN build guidance](https://onnxruntime.ai/docs/build/android.html).

No Qualcomm target board/phone is recorded in the repository, so do **not** promise QNN acceleration yet.

## 4. Recommended implementation architecture

```text
Guided Android camera
  -> local quality gate (blur/exposure/framing)
  -> local supported-crop classifier (TFLite INT8 candidate)
  -> acceptance + margin + unknown/OOD gate
  -> versioned CropHealthResult v1
  -> reviewed crop-content pack / expert escalation
  -> durable local SQLite observation and sync outbox

Optional connected path only:
  server provider adapter -> crop.health or other approved API -> same result contract
  optional evidence lookup -> Google Cloud Vision Web Detection -> source-attributed links only
  Codex/MCP -> explains the persisted versioned result, never replaces it
```

The existing `/v1/diagnoses` contract is too small for this. It lacks model ID/version, evidence quality, label alternatives, artifact hash, inference location, accepted-vs-rejected reason and reviewed-content provenance. **Aman and affected consumers must approve that schema change**; Pranav should not silently modify their API ownership.

## 5. Exact work remaining for Pranav

### P0 — decision and data (must happen before model training)

- [ ] Obtain crop, district/state, variety/stage list, target phone/SoC and agronomist reviewer; create `ml/releases/crop-health-v0.1/manifest.yaml`.
- [ ] Define 4–8 actionable labels plus `healthy`, `unknown/other`, poor-input and non-target crop challenge sets. Keep disease, pest and nutrient-stress labels separate.
- [ ] Create `ml/data/DATASHEET.md`: consent, image source, license, image IDs, annotation protocol, labels, capture device, season, plot/field and split rule.
- [ ] Collect target-region farmer-phone images across light/background/stage/severity. Split **by field/date**, not random image, to prevent leakage.
- [ ] Ask the agronomist to review labels and approved follow-up content. Preserve dissent/uncertain labels.

### P1 — classifier baseline (the smallest fieldable ML deliverable)

- [ ] Train MobileNetV3-Large and EfficientNet-Lite0 from ImageNet weights; PlantVillage may warm-start but not determine the test result.
- [ ] Apply field-like augmentation (lighting, scale, clutter, blur) without synthesizing labels that change disease morphology.
- [ ] Tune threshold and top-1/top-2 margin on validation only. Add a deliberately collected `unknown` test set (other crops, soil, hands, insects, blurry images, unlisted diseases).
- [ ] Export float and INT8 TFLite candidates. Record SHA-256, labels, preprocessing, runtime, license, model size and reproducible training commit.
- [ ] Evaluate independent in-field test images: macro-F1; class recall; confusion matrix; unknown rejection; calibration; float-vs-INT8 delta; p50/p95 local latency; memory/thermal/battery. The PRD initial gate is macro-F1 and per-released-class recall >=0.85, unknown rejection >=0.90, and <=2 points macro-F1 quantization loss—report actual results rather than asserting them.
- [ ] Complete the model card in `ml/model_cards/` and add a test that validates the release manifest/result schema.

### P2 — pest evidence, then nutrient stress

- [ ] If a declared pest is in scope, annotate boxes on local images and fine-tune a nano detector. Report mAP/recall and count error on a separate field test. Otherwise show "pest not supported" rather than fake boxes.
- [ ] Implement nutrient-stress as a fusion *screening* workflow: photo + crop/stage + recent irrigation/weather + confirmed soil/lab context. Test contradictory contexts. No photo-only N/P/K dose recommendation.

### P3 — wiring and demonstration

- [ ] Mobile owner adds Android local camera/runtime/SQLite. Pranav provides the artifact, label parser, acceptance configuration and golden test photos.
- [ ] Aman adds a provider-neutral backend result contract and optional hosted provider configuration, with API key only server-side.
- [ ] Keep `diagnose_crop` tool compatible with the final result; add a read-only `get_crop_health_result` once the canonical endpoint is published.
- [ ] Desktop/Codex shows model version, evidence limits and `unknown` faithfully. It must not expose a raw image or fabricate treatment.

### Implemented local orchestration proof (7 September 2026)

`ml/orchestration/hierarchical_inference.py` now executes the intended chain.
It runs a router checkpoint, applies the farmer-confirmation policy, and runs a
specialist only if a named approved checkpoint exists. A live smoke test with the
local controlled-image router returned bell pepper as its top candidate (0.872)
and then returned `unsupported_crop` because no bell-pepper specialist is
released. This is the required safe behavior; it is not a disease claim.

The first tomato specialist smoke-test artifact is now fine-tuned from an
ImageNet-initialized MobileNetV3-Large. Its 80-image controlled validation set
produced 0.725 accuracy and 0.656356 macro-F1, including only 0.10 recall for
early blight. It is therefore **rejected for release** and documented solely as
an end-to-end integration artifact in `ml/demo_artifacts/README.md`.

### TensorFlow Hub deployment implementation (7 September 2026)

The project now includes a second, deployable training track under
`ml/training/`:

- `tfhub_models.py` pins the approved feature-vector handles for
  MobileNetV3-Small (router), MobileNetV3-Large (fine-tunable specialist
  benchmark), and EfficientNet-Lite0 (frozen specialist baseline).
- `train_tfhub_classifier.py` uses those ImageNet-pretrained TF Hub features,
  target-label data and field-like augmentation to create a SavedModel with
  preprocessing/label metadata.
- `export_tfhub_tflite.py` creates both FP32 and representative-data-calibrated
  INT8 TFLite candidates plus labels, ready for Android benchmark work.

This implements the repeatable fine-tuning/export route, not a claim that the
new model is more accurate. The TensorFlow packages and model handles must be
installed/downloaded in a dedicated training environment and benchmarked using
the same field-held-out data before replacing the rejected PyTorch demo.

### TensorFlow Hub backbone selection update (8 September 2026)

TensorFlow Hub currently resolves the pinned MobileNetV3 Small and Large
feature-vector handles to Google-published TensorFlow 2 model pages, while the
EfficientNet-Lite0 handle resolves to a TensorFlow 1 feature-vector page.
Accordingly, the project now exposes `mobilenet_v3_large` as the accuracy-first
specialist *benchmark* choice: it supports the existing frozen-head then
lower-rate fine-tuning procedure. `efficientnet_lite0` remains a valid
edge-oriented frozen-feature comparison, but this code must not claim it has
been fully fine-tuned through `hub.KerasLayer`. No model selection changes until
the three candidates are evaluated on the same target-region field-held-out and
unknown/OOD test sets and target phone.

### EfficientNetV2-B0 comparison candidate (8 September 2026)

TensorFlow Hub's official image-retraining guide lists the TensorFlow 2
EfficientNetV2-B0 feature-vector handle at 224px alongside MobileNetV3. It is
therefore registered in the same staged transfer-learning pipeline as an
accuracy-versus-latency comparison. It is not configured in runtime and has no
performance claim: it must beat MobileNetV3-Large on the identical
field-held-out/OOD evaluation and target-device latency/battery benchmark.

**Runtime smoke evidence (8 September 2026):** With TensorFlow 2.21.0 and
TensorFlow Hub 0.16.1 installed on the project workstation, the exact handle
loaded through `hub.KerasLayer` and returned a `(1, 1280)` float32 feature
tensor from a zeroed `(1, 224, 224, 3)` RGB input. This proves dependency and
handle compatibility only—not crop-disease accuracy, TFLite export quality or
device performance.

### Candidate evidence cannot be compared across different test scopes (8 September 2026)

`compare_tflite_candidates.py` accepts only reports with the same supported
sample count, ordered labels, score/margin acceptance policy and unknown/OOD
sample scope. It emits a metrics table only after those checks. This prevents a
candidate from appearing better because it used an easier split or less strict
rejection gate. The output still cannot choose or approve a release because
device and agronomy evidence remain separate mandatory gates.

### TFLite release-evaluation implementation (8 September 2026)

`evaluate_tflite_classifier.py` now makes a directly comparable report for each
TF Hub export: accepted-input coverage, accepted accuracy, macro-F1,
per-class precision/recall, confusion matrix, and—when supplied—a separate
unknown/OOD true-rejection rate at the exact model score/margin gates. It
rejects non-probability outputs instead of silently treating logits as a
confidence score. This closes an evaluation-tooling gap; it does not supply the
required farmer-phone field or unknown data, and it cannot approve a manifest.

### Artifact-integrity preflight (8 September 2026)

`validate_release_manifest.py` validates the manifest's declared artifact
checksum, byte size, exact label ordering, scope and gate shape before a local
demo starts. It permits the explicitly rejected controlled-demo manifest only
to prove that its files have not changed; `approved_for_field_release` adds the
label checksum and all passed-evidence gate requirements. It cannot create an
approval or replace deployment-controlled manifest review.

**Controlled benchmark update:** MobileNetV3-Small was then full-fine-tuned on
the existing 320/80 controlled tomato split. Its Keras validation accuracy was
0.7625 (old PyTorch smoke test: 0.725). The exported FP32 TFLite model scored
0.7500, the 1.76 MB dynamic-range model scored 0.7625, and the full-INT8 model
scored 0.6625 on that same split. The dynamic model is the compact CPU demo
candidate. The full-INT8 loss is far beyond the release limit; all artifacts
remain demo-only/rejected. The
result is useful for selecting the next quantization experiment, not for a
field-accuracy claim.

## 6. How APIs fit without weakening the prototype

| Situation | Allowed behavior | Not allowed |
|---|---|---|
| SIH offline demo | Local v0.1 model produces an explicit versioned result or `unknown`. | Claiming API result as on-device AI. |
| Connected web demo before local model is ready | Backend calls an approved provider such as crop.health using an environment-held key; saves vendor/model timestamp and candidates. | Client-side API key, automatic pesticide/fertilizer dose, treating vendor output as verified field accuracy. |
| Team wants fast custom pest boxes | Train the declared classes with Roboflow or local YOLO workflow and call the deployed version through a server-held credential. | Using a random public Roboflow model or assuming COCO weights know crop pests. |
| Team wants a second visual opinion | Send the image plus the local candidate list to OpenAI/Gemini only with consent; require structured uncertainty and retain the local result as authoritative for the workflow. | Majority-voting generic models into a fabricated confidence score. |
| Farmer/agent needs related public material | With separate consent, call Google Cloud Vision Web Detection after model triage, then let the agent summarize only reputable returned pages with visible citations. | Scraping Google Images/Lens, treating similar images as proof, or uploading the image without consent. |
| Image + Codex conversation | The agent converts the persisted result to farmer language, asks for additional photos/context, and can open an expert-review task. | Asking a general LLM to infer disease and then overwrite the provider/local result. |
| Provider outage | Return `provider_unavailable`/`inconclusive`; keep local history. | "Healthy" default or an invented answer. |

## 7. Acceptance evidence checklist

- A local Android device runs the exact signed model in airplane mode and emits a schema-valid v1 result.
- Screenshot/video shows supported input, unknown input and poor/blurred image paths.
- Independent test-set report identifies crop/region/classes/sample counts, split by field/date, metrics, confidence intervals where feasible, and failures.
- Model card, dataset datasheet, artifact checksum, license and rollback manifest are committed.
- API/MCP/UI contract tests preserve `unknown`, provider outage and model-version data.
- A human-reviewed content pack—not model prose—supplies any suggested next action.

## 8. Risks that must stay visible

1. **PlantVillage accuracy is not field accuracy.** Its controlled imagery is valuable for pretraining but prone to background/domain shortcuts; field-held-out evidence is mandatory.
2. **Disease, pest, nutrient deficiency and water stress overlap visually.** Treat the model as screening plus context, not an autonomous agronomist.
3. **A crop health API improves demo breadth but reduces offline reliability and introduces cost, privacy and vendor-dependence.** Keep it optional.
4. **Model selection without the exact Android phone is speculative.** Benchmark the exported candidate on the actual device before a latency claim.
5. **No released model should trigger the pump.** The agent remains an explanation/orchestration layer and cannot expand a physical-control authorization.

## Controlled backbone selection checkpoint (9 September 2026)

The balanced 1,600/400 PlantVillage tomato split was restored with seed 42 and
used without change for all candidates. Dynamic-range TFLite results were:

- MobileNetV3-Small (previous runtime): 95.50% accuracy, 0.9546 macro-F1.
- MobileNetV3-Large: 96.50% accuracy, 0.9650 macro-F1.
- EfficientNetV2-B0: 97.75% accuracy, 0.9775 macro-F1.

EfficientNetV2-B0 also produced the most balanced recalls (97% early blight,
100% healthy, 95% late blight, 99% leaf mold), so it replaces the earlier
artifact in the explicit controlled-demo launcher. Its full-INT8 export scored
96.50%, but dynamic remains selected until the actual target device establishes
the latency, thermal, memory and battery trade-off. See
`evaluation/TOMATO_TFHUB_BENCHMARK_2026_09_09.md` and controlled-demo manifest
v0.3 for the complete evidence and integrity hashes.

This selection changes only controlled demonstration quality. It does not pass
the independent field, unknown/OOD, agronomist or deployment-device gates, and
therefore cannot authorize diagnosis, treatment, irrigation or pump actions.

### External-domain warning (9 September 2026)

A bounded 24-image PlantDoc external tomato check at revision
`5467f6012d78d1c446145d5f582da6096f852ae8` returned only 45.83% raw accuracy
for the selected dynamic TFLite artifact (0.3906 macro-F1), compared with
97.75% on the controlled PlantVillage split. At the current 0.70/0.15 gate it
accepted 13/24 known images and rejected 15/18 non-tomato PlantDoc images.
This tiny web-image sample is insufficient to tune or certify a threshold, but
it is sufficient to show the domain-transfer risk. No runtime threshold,
release status, treatment content or actuation authority was changed. See
`evaluation/PLANTDOC_EXTERNAL_CHECK_2026_09_09.md`.

### Crop-router experiment rejection (9 September 2026)

A fresh MobileNetV3-Small crop router was fine-tuned from ImageNet features on
a balanced, bounded four-crop PlantDoc subset (400 source-train and 64 source-
test images; 16 test images per label). Dynamic TFLite raw held-out accuracy
was 64.06% (macro-F1 0.6018) and tomato recall was only 12.5%. Under the
configured 0.80 confidence / 0.15 margin gate it accepted 11/64 images and
rejected all tomato images. The artifact is rejected for runtime integration;
the application must keep asking the farmer to confirm the crop before calling
a crop-specific specialist. Full provenance and metrics are in
`evaluation/PLANTDOC_CROP_ROUTER_CHECK_2026_09_09.md`.

### PlantDoc tomato adaptation experiment rejection (9 September 2026)

An ImageNet-pretrained TF Hub EfficientNetV2-B0 specialist was trained on 180
PlantDoc source-`train` tomato images (45 per supported label), tuned on 40
disjoint source-`train` validation images, and checked on 24 reserved
source-`test` images. It achieved 55.00% development validation accuracy but
only 29.17% raw external-test accuracy (macro-F1 0.2530); at the normal
0.70/0.15 confidence gate, it accepted no image. This artifact is rejected and
is not a runtime candidate. The source-test subset is public web imagery, not
a farmer-phone field test. See
`evaluation/PLANTDOC_TOMATO_ADAPTATION_CHECK_2026_09_09.md`.

## Source ledger

- [PlantVillage Dataset repository](https://github.com/spMohanty/PlantVillage-Dataset) — dataset size/scope and original paper.
- [PlantDoc Dataset repository](https://github.com/pratikkayal/PlantDoc-Dataset) — in-field visual dataset scope and CC BY 4.0 license statement.
- [PlantSeg repository](https://github.com/tqwei05/PlantSeg) — in-the-wild lesion segmentation data and published baselines.
- [Ultralytics model documentation](https://docs.ultralytics.com/models/) and [YOLO11 license note](https://docs.ultralytics.com/models/yolo11/) — task capabilities and license boundary.
- [DINOv2 official repository](https://github.com/facebookresearch/dinov2) and [SAM 2 official repository](https://github.com/facebookresearch/segment-anything-2) — foundation-model roles.
- [TensorFlow Lite blog](https://blog.tensorflow.org/2020/04/whats-new-in-tensorflow-lite-from-devsummit-2020.html), [TFLite conversion tutorial](https://www.tensorflow.org/tutorials/images/classification), [ONNX Runtime Mobile](https://onnxruntime.ai/docs/tutorials/mobile/) — on-device export/runtime choices.
- [Kindwise crop.health demo](https://crop.kindwise.com/demo/), [Kindwise handbook](https://www.kindwise.com/handbook), [OpenAI Responses API](https://developers.openai.com/api/reference/cli/resources/responses/methods/create) — optional hosted/API capabilities; usage/retention/licensing must be reconfirmed before deployment.
