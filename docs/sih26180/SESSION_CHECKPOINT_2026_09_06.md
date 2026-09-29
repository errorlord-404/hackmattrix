# Session checkpoint — 6 September 2026

## Completed in this checkpoint

- Reviewed the supplied soil-health-monitor circuit image and the supplied Wokwi project URL as design references.
- Checked the current repository rather than assuming it was empty. The app/API/agent work already provides a useful starting point:
  - React screens include fields, map, soil health, dashboard and AI views.
  - `backend/app/farm_state/` has field, soil-test, sensor-device and manual sensor-reading persistence.
  - `agent/src/kisansathi_agent/` provides a human-confirmed `record_sensor_reading` MCP write tool.
  - `desktop/codex-harness.cjs` starts a local `codex app-server` session with the KisanSathi MCP plugin.
- Confirmed there is currently no firmware project, Wokwi export, device authentication, device ingestion protocol, calibration history, device-health contract, actual ML inference artifact or safe actuator protocol in this repository.
- Created [TEAM_IMPLEMENTATION_PLAN.md](TEAM_IMPLEMENTATION_PLAN.md), which assigns Varuna, Anwaar, Prachi, Harshwardhan, Aman and Pranav concrete non-overlapping deliverables; defines an interface contract; sequences six delivery weeks; and documents safety gates.
- Updated the documentation index and continuation prompt to require reading this team/hardware plan.
- Added Aman’s non-ML integration slice: source-attributed marketplace discovery for machinery, seeds, fertilizer, logistics, buyers and exporters; its React route; and matching read-only MCP tools.
- Added an explicit-quote comparison API and MCP helpers for generic marketplace, machinery, and logistics decisions. It totals only disclosed base, delivery, loading, unloading and additional costs; it does not infer missing costs.
- Added MSP-versus-mandi comparison and compatibility tools matching the backend PRD names (`get_market_price`, `get_nearby_mandi_prices`, `find_machinery`, `get_scheme_details`, `calculate_logistics_cost`).
- Added marketplace setup-status API/tool/UI handling so the empty directory state tells the farmer whether approved sources still need configuration.
- Identified APEDA's public exporter directory and the Agriculture Ministry's FARMS/custom-hiring ecosystem as candidate sources; both require a source-specific approved adapter rather than unsupported generic parsing.
- Implemented and live-validated the bounded APEDA first-page exporter adapter: on 6 September 2026 it returned 12 public exporter records without contacting protected workflows.
- Added `AMAN_FUNCTION_MATRIX.md`, mapping each existing non-ML farmer function to its FastAPI route, frontend access, MCP tool and data-source status.
- Completed Harshwardhan’s device-onboarding/demo frontend: local placement/calibration capture, field assignment, current reading/data-age state, bounded moisture history, and tested empty/offline paths.
- Completed Pranav’s current Codex CLI integration scope: added portable Agent Plugin v1 manifests, made the plugin launcher portable across repository/installed-package use, added a real MCP stdio discovery test, and verified an installed Codex app-server starts a session with the KisanSathi launcher. See `PRANAV_CODEX_INTEGRATION_STATUS.md`.
- Completed the limited-prototype readiness audit. The farmer-state path is live-proven end to end through FastAPI and MCP; Mongo/reference data was unavailable during this local audit. The resulting “limited software prototype yes / field-deployable D1 no” decision is recorded in `INITIAL_PROTOTYPE_READINESS.md`.
- Completed Pranav's ML/DL discovery and decision groundwork in `ml/`: inspected the image journey, backend and MCP tool, then recorded the current truth that it is upload/storage only, not a model. Added a model-result contract, baseline model-card placeholder, evaluation protocol, release-manifest template and evidence-backed model/API decision record. The selected direction is a narrow, Android-local MobileNetV3-Large versus EfficientNet-Lite0 comparison with INT8 export, explicit unknown handling and an optional server-side crop.health secondary opinion. Training remains correctly blocked until the team names one crop, pilot region, target phone/SoC, limited label set, local data/consent and agronomy reviewer.
- Added an executable vendor-neutral CNN scaffold under `ml/training/` and crop-to-specialist routing policy under `ml/orchestration/`. It can train an ImageFolder-based MobileNetV3/EfficientNet crop router and separate specialist using private approved data, and has tests proving that ambiguous routing asks the farmer while unsupported crops do not fall through to a wrong specialist. No training data, weights or false diagnosis results were added.
- Added the corresponding farmer-confirmation UI in `src/pages/FieldTools.jsx`: the pest/disease flow now visibly requires a crop confirmation (including a valid “I do not know” response) before upload. The frontend routing helper remains local and deliberately does not claim that a released specialist or backend inference exists yet.
- Researched the requested Google-image-search idea. The legitimate implementation route is Google Cloud Vision **Web Detection**, which supplies web entities/matching pages/similar-image references after explicit image-sharing consent. It is research evidence only, never another disease vote. A sparse public PlantVillage checkout was attempted for a demo router artifact but stalled before any image blob arrived; no training data or model weight was silently substituted or committed.
- Recovered from the public checkout issue with a bounded raw-image downloader and trained a local controlled-image crop-router smoke-test artifact (four crops, MobileNetV3-Small, 80 images, 13/16 held-out correct). Its SHA-256 and strict non-release limitations are recorded in `ml/demo_artifacts/README.md`; the weight is intentionally ignored by Git. A matching bounded tomato-specialist downloader was added, but its mirror responded too slowly and was stopped before any specialist model was trained.
- Added `ml/orchestration/hierarchical_inference.py` and tests, proving the final intended chain fails closed: router checkpoint → farmer confirmation if ambiguous → existing crop-specific checkpoint only. A live bell-pepper router smoke test returned `unsupported_crop` because no specialist exists, rather than fabricating a disease label.
- Downloaded a reliable public Kaggle PlantVillage mirror outside the repository, extracted only four tomato labels, and fine-tuned the first MobileNetV3-Large tomato specialist. It completed a true router → confirmed tomato → specialist inference path. Evaluation correctly rejected it for release: 0.725 validation accuracy / 0.656356 macro-F1 and early-blight recall 0.10 on 80 controlled images. The ignored artifact hash, exact data/split/training metadata and limitations are in `ml/demo_artifacts/README.md`.

## Hardware research outcomes

| Item | Outcome | Required action |
|---|---|---|
| MAX3485-labelled RS485 board | Official MAX3485 documentation specifies a 3.3 V device, while the supplied diagram appears to share a 5 V rail with it | Verify the actual module before power-up; use an appropriate 3.3 V device or prove level/power compatibility |
| SEN0604 | Officially documents RS485/Modbus, default 9600 8N1 and soil moisture/temperature/pH/EC capabilities | Verify function labels and set/test address in isolation |
| SEN0605 | Officially documents RS485/Modbus N/P/K reference values and says data are not professional-grade accurate | Use as a screening/trend input, compare with lab/Soil Health Card data |
| Wokwi project | Browser access to `https://wokwi.com/projects/473687727046494209` was unavailable; source is not in this checkout | Anwaar exports `diagram.json`, firmware source and `wokwi.toml` into `firmware/soil-node/` |

## Explicit decisions

1. The SIH MVP starts with **advice**, not autonomous pump switching.
2. IoT upload uses a new device-authenticated ingestion route, not `POST /v1/sensor-readings` or the MCP tool.
3. Raw Modbus/CRC, timestamp, sequence, data quality, device/probe identity and calibration context travel with observations.
4. Stale or failed readings render as **unknown**, not healthy/no-irrigation.
5. Codex/MCP can explain backend decisions in local language; it cannot directly authorize physical actuation.

## Verification performed

- `git diff --check -- docs/sih26180` — no whitespace errors.
- Inspected current repository paths and symbol references for farm-state API, MCP tool, Electron harness and frontend sensor/soil consumers.
- Consulted manufacturer and platform documentation linked in `TEAM_IMPLEMENTATION_PLAN.md`.
- `python -m pytest backend/tests -q` — 18 passed.
- `PYTHONPATH=src python -m pytest tests -q` from `agent/` — 10 passed.
- `npm run test:ui`, `npm run lint`, `npm run build` — passed; Vite reports only its existing large-bundle warning.

## Working-tree safety

The repository contains many unrelated modified and untracked files that predate this checkpoint. They were not staged, changed or reverted. This checkpoint should commit only the three documentation files listed in the next section.

## Files changed by this checkpoint

- `docs/sih26180/TEAM_IMPLEMENTATION_PLAN.md` (new)
- `docs/sih26180/README.md`
- `docs/sih26180/CONTINUATION_PROMPT.md`
- `docs/sih26180/SESSION_CHECKPOINT_2026_09_06.md` (this file)
- `docs/sih26180/AMAN_FUNCTION_MATRIX.md` (new)
- `backend/app/models/marketplace_listing.py`, `backend/app/schemas/marketplace_listing.py`, `backend/app/routers/marketplace.py`, `backend/app/scraping/marketplace.py`, `backend/app/services/quote_comparison.py`, and associated tests
- `src/pages/Marketplace.jsx`, route/navigation/API client integration and UI test
- `agent/src/kisansathi_agent/tools.py`, `agent/src/kisansathi_agent/server.py`, and MCP tests
- `codex/plugins/kisansathi/plugin.json`, `codex/plugins/kisansathi/mcp.json`, `codex/plugins/kisansathi/run_server.py`, `agent/tests/test_stdio_server.py`, and `docs/sih26180/PRANAV_CODEX_INTEGRATION_STATUS.md`
- `docs/sih26180/INITIAL_PROTOTYPE_READINESS.md`
- `ml/README.md`, `ml/MODEL_DECISION_RECORD.md`, `ml/contracts/crop-health-result.schema.json`, `ml/model_cards/crop_health_baseline_v0_1.md`, `ml/evaluation/README.md`, and `ml/releases/crop-health-v0.1.manifest.example.yaml`
- `ml/training/**`, `ml/orchestration/crop_router.py`, and `ml/tests/test_crop_router.py`
- `src/features/cropRouting.js`, `src/features/cropRouting.test.js`, and `src/pages/FieldTools.jsx`

## Exact next task

## 7 September 2026 — local ML integration update

- Completed the prototype integration for the already fine-tuned local artifacts: `backend/app/services/crop_health.py` loads the existing two-stage router/specialist contract only when explicitly configured.
- `POST /v1/diagnoses` now accepts a `confirmed_crop`, persists model/candidate/limitation metadata in the farmer SQLite database, and returns transparent safe states: `needs_crop_confirmation`, `unsupported_crop`, `provider_unavailable`, or `needs_expert_review` rather than fabricating a diagnosis.
- The web photo flow and MCP `diagnose_crop` tool now forward the farmer-confirmed crop. This creates one consistent path: UI or voice agent → FastAPI → local model → persisted evidence → agent explanation.
- The local demo remains **not release-ready**. Its controlled-image tomato specialist has insufficient early-blight recall and must be retrained/evaluated on region- and field-held-out data before field claims, automation, or treatment recommendations.

### To enable only for a local SIH demonstration

Install `backend/requirements-ml.txt`, then set the following environment values (use absolute paths):

```text
DIAGNOSIS_PROVIDER=local_hierarchical_demo
CROP_HEALTH_ROUTER_MODEL_PATH=C:\\...\\ml\\demo_artifacts\\plantvillage-crop-router-demo-v0.1.pt
CROP_HEALTH_SPECIALIST_MODELS_JSON={"tomato":"C:\\...\\ml\\demo_artifacts\\plantvillage-tomato-specialist-demo-v0.1.pt"}
```

These untracked local checkpoints must never be committed or promoted as a field release.

### Verification for the 7 September integration

- `python -m pytest tests -q` from `backend/` — **23 passed**.
- `PYTHONPATH=src python -m pytest tests -q` from `agent/` — **12 passed**.
- `npm run test:ui -- --run`, `npm run lint`, `npm run build` — passed (Vite retains an existing large-chunk warning).
- A live local inference invocation with the configured ignored checkpoints and a held-out controlled tomato image returned `completed → healthy` at 0.9999977. This only validates plumbing on an in-domain controlled image; it is not performance evidence.

### Exact continuation task

Do not further tune the current tiny artifacts. Choose one crop/pilot region with an agronomy reviewer, collect consented real-phone/field images (including healthy, common pests, nutrient deficiency, multiple severities and unknowns), then fine-tune with field-held-out evaluation, calibration, OOD/unknown tests, device latency/battery tests and a signed release manifest. Export the approved model to INT8 TFLite/ONNX for the chosen Qualcomm target. Keep the server demo as a secondary, explicitly marked evidence path until that release gate passes.

## 7 September 2026 — TensorFlow Hub / TFLite track

- Added a dedicated TensorFlow Hub pipeline at `ml/training/train_tfhub_classifier.py` using the pinned ImageNet-pretrained MobileNetV3-Small and EfficientNet-Lite0 feature-vector models.
- Added calibrated INT8 export at `ml/training/export_tfhub_tflite.py`, model definitions and no-TensorFlow unit checks.
- `ml/training/requirements-tfhub.txt` keeps the large TensorFlow/TensorFlow Hub dependencies out of the regular FastAPI environment.
- Both model URLs resolve through TensorFlow Hub (currently redirected to their maintained Kaggle model pages). The local workstation did not finish the 350 MB TensorFlow wheel download during bounded tool runs; no unverified artifact or score was claimed.

### Next concrete command on a training machine

```powershell
python -m pip install -r ml/training/requirements-tfhub.txt
python ml/training/train_tfhub_classifier.py --dataset <approved-field-split> --output ml/private-artifacts/tomato-efficientnet-lite0 --backbone efficientnet_lite0 --epochs 8
python ml/training/export_tfhub_tflite.py --saved-model ml/private-artifacts/tomato-efficientnet-lite0 --representative-data <approved-field-split>\train --output-dir ml/private-artifacts/tomato-efficientnet-lite0-tflite
```

### Actual local TF Hub benchmark evidence

- Installed TensorFlow 2.21.0, TensorFlow Hub 0.16.1 and compatible `tf-keras`; loaded the EfficientNet-Lite0 Hub feature vector successfully (output shape `1×1280`).
- EfficientNet-Lite0 is currently served through a TF1 Hub handle, so `hub.KerasLayer` cannot unfreeze it. A frozen-head 4-epoch benchmark reached only **0.675** validation accuracy on the 80-image controlled tomato split; it is rejected.
- Full TF Hub MobileNetV3-Small fine-tuning (8 epochs, ImageNet initialization, same 320/80 controlled split, seed 42) reached **0.7625** Keras validation accuracy, above the old PyTorch smoke-test accuracy of 0.725. This is a small controlled split, not statistically reliable field evidence, and remains rejected for release.
- Export produced `model-fp32.tflite` (6,149,072 bytes), dynamic-range `model-dynamic.tflite` (1,756,896 bytes), and calibrated `model-int8.tflite` (1,877,528 bytes). TFLite evaluation on the same 80 images was **0.7500 FP32**, **0.7625 dynamic-range**, and **0.6625 INT8**. Dynamic range is the compact CPU demo candidate; the 8.75-point full-INT8 quantization loss fails the project’s ≤2-point gate, so **do not deploy the INT8 artifact**.

### ML decision after this benchmark

Keep the TF Hub MobileNetV3 FP32 model only as a demo/development artifact. Before Android selection, improve post-training quantization (larger field-like representative calibration set, quantization-aware training or a compatible LiteRT path), then repeat all field-held-out and unknown/OOD tests. Neither the controlled accuracy nor any TFLite output authorizes automatic agronomy action.

## 7 September 2026 — larger controlled TF Hub benchmark and provider wiring

- Created a deterministic larger PlantVillage split: 400 training and 100 validation images per label (`early_blight`, `healthy`, `late_blight`, `leaf_mold`), 1,600/400 total.
- Full TF Hub MobileNetV3-Small fine-tuning reached **0.9575** Keras validation accuracy. Exported dynamic TFLite achieved **0.9550** on the same 400 images, with recall 0.93 early blight, 1.00 healthy, 0.90 late blight, 0.99 leaf mold. This is a controlled-data benchmark only, not field evidence.
- Full INT8 TFLite achieved 0.9075 with late-blight recall 0.76: still rejected for the project full-INT8 release gate. Dynamic-range TFLite remains the compact CPU **demo** candidate.
- Added `DIAGNOSIS_PROVIDER=local_tflite_demo` to the backend. It runs only a farmer-confirmed configured crop specialist, persists candidate/model/limitation evidence in the existing SQLite diagnosis envelope, and fails closed for unsupported/missing/low-confidence input.
- A live service invocation with the ignored dynamic TFLite artifact and a held-out healthy tomato photo returned `completed → healthy` with model metadata. `python -m pytest tests -q` from `backend/` remains **23 passed**.
- The `/pest` UI now displays the returned label, model confidence, ranked alternatives, provider/model/version/location and safety limitations. It also has a dedicated upload-to-result UI test. Frontend validation is **8 files / 13 tests passed**, lint passes, and the production build passes; ML orchestration tests are **6 passed**.
- Dynamic TFLite SHA-256 for this larger controlled benchmark: `b16a6c0966cd0c2c0c61a7ba85ac77b7e736ded451fe9f2c391c77150cfdd69b`.
- Final API proof: multipart `POST /v1/diagnoses` with a real held-out image and `confirmed_crop=tomato` returned HTTP 201, `completed`, `healthy`, `tfhub-mobilenetv3-small-tomato-specialist`, and three persisted candidates. This is the exact API contract consumed by the web UI and Codex tool.
- Added an explicit top-one/top-two disease margin gate (`CROP_HEALTH_MIN_DISEASE_MARGIN=0.15`) in addition to the confidence gate. The held-out healthy proof image cleared it with a 0.9976 margin; ambiguous model calls now return `needs_expert_review`.
- Added deterministic backend tests for low-confidence and near-tie rejection; backend suite is now **24 passed**.
- Added the version-controlled controlled-demo manifest `ml/releases/crop-health-tfhub-tomato-controlled-demo-v0.2.yaml`, including artifact SHA-256, labels, preprocessing, thresholds, all benchmark metrics, explicit release blockers and distribution prohibition. YAML validation passed.

## 7 September 2026 — TF Hub crop-router evidence and confirmation contract

- Fine-tuned the same ImageNet-pretrained TF Hub MobileNetV3-Small backbone as a four-crop router (`bell_pepper`, `maize`, `potato`, `tomato`) using the only locally available 64/16 PlantVillage controlled split. It reached **0.4375 validation accuracy**. The saved artifact is ignored under `ml/private-artifacts/plantvillage-crop-router-tfhub-demo`; it is rejected and is **not configured** in the application.
- This result confirms that the old tiny crop-router split is insufficient; it must not be presented as a successful accuracy improvement. TensorFlow Datasets documents PlantVillage as 54,303 controlled leaf images across 38 categories, but even a full controlled corpus cannot substitute target-region farmer-phone field data for release.
- Added an opt-in, generic TFLite crop-router contract. With router artifacts configured, an unknown crop returns ranked `crop_candidates` and `needs_crop_confirmation`; it never selects a disease specialist. The farmer must confirm/correct the crop in a subsequent request.
- The API now persists crop candidates separately from disease candidates, and the `/pest` result view displays them in an amber “Suggested crop — please confirm” card. A router is disabled by default because there is no acceptable artifact.
- Verification: backend suite **26 passed**; frontend UI suite **8 files / 13 tests passed**; lint and production build passed. The production build still reports the pre-existing >500 kB JavaScript chunk warning.
- Attempted to obtain the official TensorFlow Datasets `plant_village` corpus (documented as 54,303 controlled images) to replace the tiny router split. The current TFDS builder failed before downloading images because its pinned Mendeley URL returned **HTTP 403**. Its public publisher page is accessible but describes a different 61,486-image augmented dataset. Do not silently substitute it for the documented TFDS corpus; source an approved, versioned dataset bundle or resolve the publisher download route before retraining.
- Added `backend/scripts/run_local_tflite_demo.ps1`. It verifies the known dynamic TFLite artifact, injects `local_tflite_demo` settings into only the launched process, accepts a configurable port, and does not alter `.env`. `-CheckOnly` succeeds locally.
- Live proof: launched the explicit TFLite backend alongside the pre-existing unconfigured service on port 8001, verified `/health` reports `diagnosis: local_tflite_demo`, and posted a held-out healthy tomato photo. The API returned HTTP 201, `completed`, `healthy`, 0.998403 confidence, three candidates, `tfhub-mobilenetv3-small-tomato-specialist`, `controlled-demo-v0.2`, and the persisted no-action limitations. The temporary port-8001 process was stopped; the existing process on port 8000 was not touched.
- Added root `npm run demo:tflite:check` and `npm run demo:tflite`. The latter runs the explicit backend on 8001 and Vite with matching `VITE_FARM_STATE_API_URL`/`VITE_REFERENCE_API_URL`, without editing `.env`. Live combined proof returned backend health `diagnosis: local_tflite_demo` and Vite HTTP 200. During proof an existing process owned 5173, so Vite safely selected 5174; the runner prints the actual URL. Both temporary processes were stopped without touching the existing 8000/5173 processes.

## 7 September 2026 — irrigation forecast safety correction

- Fixed the irrigation plan's cross-field weather defect. It now selects only the newest cached weather snapshot within the requested field's coordinate tolerance—the same lookup policy used by the field-weather endpoint—rather than the newest snapshot anywhere in the farmer store.
- Plans explicitly state either the location-matched forecast fetch time or that no matching forecast was used, so a rain deferral is inspectable. The endpoint remains read-only and cannot actuate a pump/valve.
- Added a regression with two geographically separated fields: a 95% forecast on the far field does not defer irrigation on the requested field, while a matching 95% forecast correctly produces `defer_for_rain`. Backend verification is now **27 passed**.

## 7 September 2026 — sensor unit safety correction

- Added canonical-unit validation for sensor ingestion: moisture/humidity `%`, temperature `°C`, pH `pH`, EC `mS/cm`, and N/P/K `mg/kg`. Common aliases normalize; unsupported units are rejected at the API boundary.
- The irrigation planner now refuses a legacy moisture record whose stored unit is not `%`; it returns `insufficient_data` with an explicit assumption instead of comparing an arbitrary raw value against a percent threshold.
- Regression coverage proves normalization (`percent` → `%`), invalid `raw_adc` rejection, and legacy fail-closed irrigation behavior. Backend verification is now **29 passed**.

## 7 September 2026 — canonical crop-stage engine

- Implemented canonical write-time lifecycle stages: `land_preparation`, `seed_treatment`, `sowing`, `germination`, `vegetative`, `flowering`, `fruiting`, `grain_filling`, `maturity`, and `harvest`. Common user wording normalizes (for example, “Grain Filling” → `grain_filling`, “Harvesting” → `harvest`); unsupported values fail validation rather than silently escaping stage-aware rules.
- Updated irrigation critical-stage recognition for the canonical `grain_filling` key. Existing historical arbitrary stage rows remain readable; crop-specific stages require an explicit future mapping instead of a guessed normalization.
- Backend verification is now **30 passed**.

## 7 September 2026 — task/action engine baseline

- Activated the previously orphaned `field_tasks` SQLite state with farmer-scoped APIs: create a task, list tasks (field/status filters), and mark a task `completed` or `cancelled`. Writes are idempotent and retain a source label.
- Added Codex/MCP tools: `list_field_tasks`, `create_field_task`, and `update_field_task_status`. They retain the confirmation boundary and describe task creation as an audited record—not a purchase, booking, chemical application, or hardware command.
- Verification: backend **31 passed** and MCP agent **12 passed**.
- Added the navigable `/tasks` **Field Actions** screen. It loads only persisted open tasks for a selected field, shows provenance/due time, lets the farmer create a confirmed action, and records completion through the same backend contract. It contains no generated placeholder tasks and makes no booking/purchase/device-control claim.
- UI verification is now **9 files / 14 tests passed**; lint and production build pass. The known production bundle-size warning remains.

## 7 September 2026 — staged pretrained-model fine-tuning

- The TensorFlow Hub classifier trainer now implements staged transfer learning for `mobilenet_v3_small`: it warms up the new crop-health head while the ImageNet backbone is frozen, then fine-tunes the pretrained backbone with a separately configured lower learning rate (default `3e-5`). The training metadata records both phases and rates.
- `efficientnet_lite0` remains head-only in this specific TF Hub implementation because its published feature-vector handle is TF1-based and is not safely unfrozen through `hub.KerasLayer`.
- This improves the reproducible training procedure, not the status of any model: the existing controlled PlantVillage artifact remains demo-only and rejected for field release until the documented field-data and evaluation gates pass.

## 7 September 2026 — farmer-scoped finance ledger

- Replaced the Finance page's browser-only transaction source with the existing farmer-scoped SQLite Farm State API. The ledger supports confirmed INR income/expense records, optional field/crop context, active-only summary totals, and audit-preserving void/reinstate status updates.
- Added matching Codex/MCP tools (`list_ledger_entries`, `get_ledger_summary`, `record_ledger_entry`, and `update_ledger_entry_status`) so the agent and UI see the same farmer data.
- The ledger is deliberately bookkeeping only: it cannot move money, create credit, execute a purchase, calculate tax, or make a financial forecast. Browser-only `financeStore.js` is no longer used by the screen and can be removed after migration/retention review.

## 7 September 2026 — device-authenticated telemetry boundary

- Added the planned dedicated `POST /v1/device-ingestion/observations` route. It accepts only provisioned bearer-authenticated device packets and scopes each device to a configured farmer and optional field list; it never accepts farmer identity from the ESP32 payload.
- Every packet stores device, boot ID, sequence, observed/received time, firmware version, transport metadata, probe ID, Modbus address, CRC state, calibration revision, and rejection reason in the farmer SQLite store. `(device_id, boot_id, sequence)` replay is idempotent.
- CRC-valid samples pass through the same canonical-unit contract and become normal sourced sensor readings. CRC-failed samples are retained as evidence but cannot influence soil/irrigation rules. `GET /v1/device-ingestion/devices` and the read-only MCP `list_device_health` tool expose fresh/stale/rejected health without revealing credentials.
- The Device Onboarding screen now consumes that health route alongside readings/history and visibly reports the gateway state, last packet time, firmware version, and rejection reason. It keeps stale/rejected data distinct from a missing reading and does not show device credentials.
- This is a protocol/software contract, not physical hardware evidence. The Wokwi export, firmware, actual transceiver-voltage verification, Modbus bench log, calibration comparison, offline queue, and field test are still outstanding.

### Verification for the finance and device increments

- `python -m pytest backend/tests -q` — **34 passed**.
- `PYTHONPATH=src python -m pytest tests -q` from `agent/` — **12 passed**.
- `npm run test:ui -- --run` — **10 files / 15 tests passed**; `npm run lint` passed.
- `npm run build` passed; the existing bundle-size warning remains (about 683 kB JavaScript before gzip).

## 8 September 2026 — crop-stage proposal-to-action loop

- Added stage-aware task proposals for the active canonical crop stage. The rules cover generic, non-prescriptive lifecycle records such as emergence inspection, flowering health/moisture check, harvest planning, and harvest quality/quantity capture.
- The proposal endpoint is read-only, suppresses titles already tracked as open tasks, and returns a clear `requires_farmer_confirmation` field. It never creates a task by itself.
- Added MCP `get_crop_stage_action_proposals` and a Field Actions UI review card. The UI presents the stage/crop/rationale and creates a task only after the farmer presses “Accept as field action.”
- Verification: backend **35 passed**, agent **12 passed**, frontend **10 files / 15 tests**, lint and production build pass. Build retains its large-bundle warning.

## 8 September 2026 — TF Hub field-data fine-tuning safeguards

- The TensorFlow Hub classifier trainer now uses inverse-frequency class weights by default, computed only from the training folders. This prevents a majority healthy label from dominating the optimization when the approved field set is imbalanced. The model metadata records raw class counts, weighting mode, and resolved weights.
- Added random brightness augmentation alongside the existing rotation, contrast, zoom, and flip transforms to better represent benign lighting variation from farmer-phone capture. It does not synthesize disease labels or replace target-region field data.
- The staged ImageNet transfer-learning procedure remains: warm up the disease head, then lower-rate fine tune MobileNetV3-Small. EfficientNet-Lite0 remains head-only for the configured TF1 Hub handle.
- Verification: ML **9 passed**; backend **35 passed**; agent **12 passed**; frontend **10 files / 15 tests**, lint, and production build pass. The controlled PlantVillage model remains demo-only/rejected for field release.

## 8 September 2026 — controlled-demo OOD safety correction

- A real project non-crop image (`public/farmer.jpg`) was posted to the explicit TFLite demo with `confirmed_crop=tomato`. The constrained specialist returned a high-confidence `late_blight` candidate (0.8464), proving that score and top-two margin alone cannot reject out-of-distribution input.
- Changed the default TFLite demo contract: even a confident candidate returns `needs_expert_review`, retains ranked candidates/model metadata, and explains that the controlled artifact lacks unknown/OOD and farmer-phone field evidence.
- Replaced the mutable completion flag with a release-manifest gate. A completed result now needs an approved manifest that matches the exact model/label checksums and explicitly passes independent field-held-out, unknown/OOD, and agronomist-review gates. The checked-in demo has none, so it remains review-only.

### Current artifact boundary

The ignored artifacts under `ml/private-artifacts/tomato-mobilenetv3-tfhub-large-demo*` may support a controlled SIH demonstration only. They have no farmer-phone/Indian field dataset, unknown/OOD class, independent field split, calibration study, agronomist sign-off, device latency/battery result, or approved treatment content. Do not mark them as field deployed.

The four-label PlantVillage tomato specialist controlled-demo checkpoint is already integrated behind the explicit `local_tflite_demo` provider and `CropHealthResult v1` envelope. The next ML step is **not** another controlled-data tuning cycle: collect or license consented target-region farmer-phone/field images (healthy, diseases, pests, nutrient deficiency, multiple severities and unknowns), obtain agronomist-reviewed labels and treatment boundaries, and replace the demo only after field-held-out, calibration, OOD and target-device evaluation pass.

## 8 September 2026 — TensorFlow Hub pretrained-backbone review

- Re-checked the pinned TensorFlow Hub model handles against their current
  Google-published pages. MobileNetV3 Small and Large resolve as TensorFlow 2
  feature-vector models; the configured EfficientNet-Lite0 handle resolves as
  TensorFlow 1.
- Added `mobilenet_v3_large` to the executable training registry. It is a
  224-pixel, ImageNet-pretrained, fine-tunable specialist benchmark candidate;
  MobileNetV3 Small remains the lower-cost router candidate and
  EfficientNet-Lite0 remains a frozen-feature baseline in this implementation.
- This is a candidate expansion only. There was no new training run, no model
  replacement and no field-accuracy claim. Benchmark all three only after the
  consented field/OOD dataset and Android target are available.

## 8 September 2026 — artifact-bound TFLite release gate

- Removed `CROP_HEALTH_TFLITE_ALLOW_DEMO_COMPLETED`. The runtime now requires
  `CROP_HEALTH_TFLITE_RELEASE_MANIFEST_PATH` to point to a reviewed manifest
  with approved status, matching model and label SHA-256 values, crop scope,
  and three passed gates: independent field evaluation, unknown/OOD evaluation,
  and agronomist review.
- Expanded the versioned manifest template with the label checksum and release
  gates. The existing controlled demo manifest explicitly records all gates as
  missing, so its high-scoring candidates cannot become diagnoses.
- Added backend regressions for missing-manifest review-only output, approved
  matching manifest completion, and artifact-checksum mismatch rejection.

## 8 September 2026 — comparable TF Hub/TFLite evaluation reports

- Upgraded `ml/training/evaluate_tflite_classifier.py` from raw accuracy only
  to a fixed-threshold field-test report containing coverage, accepted accuracy,
  macro-F1, per-class precision/recall, a confusion matrix, and separate
  unknown/OOD true-rejection when an approved challenge directory is supplied.
- A supported-class photo rejected by score/margin now counts as a false
  negative for class recall/F1 while coverage is reported separately; this
  prevents a high rejection rate from inflating model quality.
- The evaluator rejects malformed/non-probability output rather than producing
  a fake confidence metric. It writes an optional JSON evidence report but
  cannot approve a model or modify the runtime manifest.

## 8 September 2026 — safer irrigation-screening states

- Updated the advisory irrigation rule so a critical low moisture reading is
  not deferred merely because rain is probable; rain deferral is now limited to
  a small below-target deficit.
- If a farmer-recorded irrigation is less than 12 hours old and moisture is not
  critical, the endpoint returns `reassess_after_recent_irrigation` and asks
  for a fresh reading before another application. This remains generic,
  read-only screening—not a calibrated volume/root-zone balance or pump control.
- Added the matching farmer UI action: “I irrigated — record it” posts an
  explicit time-stamped `farmer_confirmed` irrigation event, then refreshes the
  plan. It cannot start/stop a pump, estimate volume, or claim actuation.
- UI verification: **10 files / 15 tests passed**; lint and production build
  passed. The existing roughly 686 kB pre-gzip bundle warning remains.

## 8 September 2026 — connected irrigation history

- Added farmer-scoped, field-filterable `GET /v1/irrigation-events`, plus the
  matching `list_irrigation_events` MCP tool and Irrigation-page history panel.
  The UI and voice agent now consume the same recorded events that drive the
  post-irrigation reassessment state.
- The endpoint intentionally preserves only confirmed entries; it does not
  estimate volumes from duration, moisture, or assumed pump flow.
- Verification: backend **42 passed**, agent **12 passed**, UI **10 files / 15
  tests**, lint, and production build passed. The bundle warning remains.

## 8 September 2026 — TF Hub artifact-integrity preflight

- Added `ml/training/validate_release_manifest.py`, which validates a local
  manifest against the exact model SHA-256, byte size, labels SHA-256/order,
  declared scope, and release-gate shape. It reports integrity and never
  upgrades a release.
- The controlled demo launcher now runs that preflight before starting. Live
  verification matched the dynamic TFLite artifact (`b16a…d69b`, 1,756,896
  bytes) and the four declared labels, while retaining its rejected status and
  missing field/OOD/agronomist gates.
- ML verification: **15 passed** and `npm run demo:tflite:check` passed.

## 8 September 2026 — live protected-demo runtime proof

- Started the paired `npm run demo:tflite` stack after the integrity preflight.
  The Vite frontend responded at `http://127.0.0.1:5173/` and backend
  `/health` at `http://127.0.0.1:8001/` reported
  `diagnosis: local_tflite_demo`.
- Health is `degraded` only because the optional central Mongo reference
  database is unavailable; farmer SQLite state is available. The release
  preflight still reports the model as rejected/review-only, as intended.

## 8 September 2026 — shared reference runtime activated

- Ran the repository's Windows universal-data bootstrap. The first run exposed
  a path-with-spaces bug in the MongoDB launcher; it was fixed by explicitly
  quoting `--dbpath`/`--logpath`, and the retry started workspace-local MongoDB
  on port 27017.
- The official-source ingestion completed with one current AGMARKNET mandi
  record, 23 PIB MSP records, and one derived crop record. Source URLs and the
  completed ingestion run are preserved in MongoDB.
- Restarted only the demo stack started in this session. Its port-8001 health
  now reports both `reference_database: available` and
  `diagnosis: local_tflite_demo`; `GET /crops` returned the sourced record.
  The controlled model remains review-only. The optional n8n install/activation
  was still running when last checked.

### Scheduler activation blocker (environment, not prototype)

- n8n v1.123.72 installation stopped at `isolated-vm` because `node-gyp` could
  not find a Visual Studio C++ build workload. The host has Visual Studio but
  lacks the required Desktop development with C++ components.
- This does not affect MongoDB, FastAPI, the completed manually triggered
  ingestion, or the live port-8001 demo. It blocks only automated daily n8n
  scheduling until the workload is installed and the setup script is rerun.

## 8 September 2026 — crop-option evidence screen and durable demo launch

- Added `GET /v1/fields/{field_id}/crop-options` and MCP
  `get_crop_options`. The endpoint verifies farmer field ownership in SQLite,
  reads the central crop catalogue, and returns visible season/rotation/soil
  checks, conflicts and missing evidence. It intentionally does **not** call a
  crop “best,” calculate profit/yield/fertilizer, or purchase anything.
- Live proof on the shared reference runtime: a Kharif field query returned
  sourced `Paddy(Common)` at ₹2,379/quintal and correctly marked rotation and
  soil evidence missing. This tiny catalogue is a proof of plumbing, not a
  recommendation dataset.
- Fixed the demo launcher again: PowerShell expanded bare Uvicorn
  `--reload-exclude` globs into hundreds of `.runtime` file arguments. The
  launcher now passes literal `--reload-exclude=<glob>` options. The paired
  stack is live at `http://127.0.0.1:5173/` and
  `http://127.0.0.1:8001/health`, with both reference storage and the guarded
  local TFLite provider available.

## 8 September 2026 — TensorFlow Hub accuracy benchmark expansion

- Kept MobileNetV3-Small as the fast crop-router candidate and
  MobileNetV3-Large as the first fine-tunable specialist baseline.
- Added official TensorFlow Hub `efficientnet_v2_b0` (224px TF2 feature-vector
  handle) to the executable staged fine-tuning registry as an
  accuracy-versus-latency comparison. It is neither trained nor configured in
  runtime.
- Verified ML tests: **15 passed**. The selection rule remains unchanged: pick
  only the candidate that wins the same farmer-field-held-out disease/OOD tests
  and target-phone latency/battery benchmark. The current controlled tomato
  artifact remains demo-only/rejected; no model can trigger advice or hardware.

## 8 September 2026 — crop selection reaches the farmer UI

- Connected the new farm-state crop-option contract to the `/crop-guide` React
  screen. A farmer can choose the next season, correct the recorded previous
  crop, enter a soil type, and explicitly request a source-backed evidence
  comparison.
- The interface clearly separates matching evidence, conflicts and missing
  data; it exposes the attributable price source and labels every result as
  farmer review required. It does not auto-select a crop, estimate profits or
  inputs, or turn reference prices into an income claim.
- UI verification: **10 files / 16 tests passed**, ESLint passed, and the
  production build passed. The existing 500 kB code-splitting warning remains.

## 8 September 2026 — comparable TF Hub candidate evaluation

- Added `ml/training/compare_tflite_candidates.py`. It accepts reports emitted
  by the existing TFLite evaluator and refuses a comparison unless supported
  sample count, ordered labels, score/margin policy and unknown/OOD evaluation
  scope are identical.
- When the evidence is comparable, it produces a transparent macro-F1,
  coverage, accepted accuracy and OOD-rejection table. It cannot select a
  model, update the release manifest or replace target-device/agronomist gates.
- Added regression coverage; ML verification is now **17 passed**.

## 8 September 2026 — consented crop-health feedback loop

- Added farmer-scoped, append-only `diagnosis_feedback` records and
  `POST /v1/diagnoses/{diagnosis_id}/feedback`. It records a farmer’s
  confirmation/correction/unknown response, optional crop/label, note and
  explicit sharing consent with idempotency and cross-farmer isolation.
- The API deliberately returns
  `requires_expert_review_and_separate_export`: feedback is not ground truth,
  does not export an image, alter a diagnosis, train a model, or authorize
  treatment.
- The Pest & Disease screen now lets the farmer provide that feedback after a
  result and clearly explains the consent boundary.
- Current verification: UI **10 files / 17 tests**, backend **45 passed**, ML
  **17 passed**, lint and production build passed. The existing code-splitting
  warning remains.

## 8 September 2026 — local agronomist-review queue builder

- Added `ml/training/build_diagnosis_review_queue.py`. An authorised operator
  must name each farmer SQLite file explicitly; the tool reads consented,
  label-bearing feedback and produces a local JSON review queue.
- It never copies or uploads images, and omits local image paths by default.
  Every item remains marked `requires_agronomist_label_review_and_dataset_split`.
  Review still needs an approved agronomist and a field/date-disjoint split
  process before TF Hub fine-tuning.
- ML verification: **19 passed**.

## 8 September 2026 — executable TF Hub default corrected

- Corrected `train_tfhub_classifier.py` to default to fine-tunable
  MobileNetV3-Large. Previously the default was TF1 EfficientNet-Lite0 while
  the same command rejected non-frozen TF1 training; a plain training command
  could therefore stop before fitting.
- EfficientNet-Lite0 is still available as a comparison baseline but now
  requires explicit `--freeze-backbone`; its README command was corrected.
- The review queue now includes anonymized field groups and recorded capture
  timestamps so future splits can be separated by field/date. ML verification:
  **20 passed**.

## 8 September 2026 — expert-reviewed field-split manifest

- Added `ml/training/build_reviewed_field_split.py`. It consumes a local review
  queue plus explicit `crop-health-expert-review-v1` approvals, and emits a
  metadata-only train/validation/field-test split manifest.
- It fails closed when there are fewer than three distinct field groups or an
  approved disease label would be absent from a partition. Each field group is
  assigned to only one partition; no images are copied or training invoked.
- ML verification: **23 passed**. A separate unknown/OOD challenge set, actual
  field data, target-phone benchmarking, and release review are still required.

## 8 September 2026 — guarded reviewed-data materialization

- Added `ml/training/materialize_reviewed_split.py`, the only command that
  creates training-folder image copies. It requires an explicit
  `--confirm-authorised-data-steward` acknowledgement, verifies every source
  SHA-256, normalizes safe label-folder names and refuses non-empty output
  directories.
- It consumes only the expert-reviewed field-split manifest and still does not
  upload data, train a model, tune on `field_test`, or approve release.
- ML verification: **25 passed**.

## 8 September 2026 — EfficientNetV2-B0 runtime compatibility verified

- Loaded the exact official TF Hub EfficientNetV2-B0 feature-vector handle with
  the installed TensorFlow 2.21.0 / TensorFlow Hub 0.16.1 environment and ran a
  224px RGB inference. It produced a `(1, 1280)` float32 feature tensor.
- This verifies the new registry entry is executable on this workstation. It
  is not evidence of crop-health accuracy, TFLite export quality, target-phone
  latency or field release.

### Controlled-data availability check

- Before launching an EfficientNetV2-B0 benchmark, checked the retained
  temporary PlantVillage directories. The original balanced four-class split is
  no longer available: the remaining tiny/source directories contain only a
  handful of `healthy` images. Training on it would make an invalid comparison,
  so no run was started and no accuracy claim changed.
- Resume only after an approved, balanced four-class controlled split is
  restored for a demo benchmark, or preferably after the consented,
  agronomist-reviewed field dataset pipeline above has real data.

In parallel, configure one approved HTTPS public directory source in `MARKETPLACE_DIRECTORY_SOURCES_JSON`, run marketplace ingestion, and verify that a source-attributed listing appears in the directory and MCP result. Run the P0 hardware verification with Varuna and Anwaar: identify the exact transceiver board, resolve the 3.3 V/5 V wiring, export the Wokwi project, and produce a single-sensor Modbus bench read log. Device ingestion must remain a separate authenticated contract—not an uncontrolled hardware connection.
