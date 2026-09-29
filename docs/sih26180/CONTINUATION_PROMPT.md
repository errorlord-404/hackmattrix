# Continuation prompt for a future AI

Copy the block below into a new task in this repository.

```text
Continue the KisanSathi SIH26180 project from the documented checkpoint. Do not restart discovery from scratch.

First read, in order:
1. docs/sih26180/README.md
2. docs/sih26180/FLOWCHART_SESSION_CHECKPOINT_2026_09_09.md
3. docs/sih26180/flowcharts/README.md
4. docs/sih26180/flowcharts/FLOWCHART_RESEARCH_BRIEF.md
5. docs/sih26180/SESSION_CHECKPOINT_2026_09_06.md
6. docs/sih26180/SESSION_CHECKPOINT_2026_09_05.md
7. docs/sih26180/RESEARCH.md
8. docs/sih26180/PRD.md
9. docs/sih26180/IMPLEMENTATION_PLAN.md
10. docs/sih26180/SOURCE_LEDGER.md
11. docs/sih26180/report-source.md
12. docs/sih26180/TEAM_IMPLEMENTATION_PLAN.md
13. docs/sih26180/AMAN_FUNCTION_MATRIX.md
14. docs/sih26180/PRANAV_CODEX_INTEGRATION_STATUS.md
15. docs/sih26180/INITIAL_PROTOTYPE_READINESS.md
16. ml/MODEL_DECISION_RECORD.md
17. ml/evaluation/README.md
18. git status --short
19. relevant AGENTS.md files before editing their scope.

The repository is intentionally dirty. Treat existing modified/untracked paths as user-owned. Do not reset, clean, checkout, rebase or stage unrelated changes. Work only on paths needed for the requested task.

Current planning recommendation:
- Deliver a focused field-deployable SIH demonstrator for one crop and one pilot region.
- Core: Android local crop-health inference, calibrated sensors, stage-aware FAO56-style root-zone water balance, bounded local irrigation controller with manual override and flow feedback, offline history/tasks and source-aware weather/alert context.
- Keep full lifecycle features as a staged roadmap.
- Do not make unverified claims about field accuracy, NPK probe accuracy, yield/profit, exact hyperlocal forecasts, MSP eligibility or winning SIH.

Before implementation, verify the official SIH statement and choose/confirm target crop, pilot location, Qualcomm target device/board, field partner, agronomy reviewer and hardware constraints. If those inputs are still unavailable, implement only reusable D0/Phase 1 corrections and clearly record assumptions.

Known current defects to address before expanding features:
1. Irrigation weather query is not scoped to requested field/coordinates.
2. Irrigation relies on fixed moisture thresholds and probability-only rain deferral; it must not actuate equipment.
3. Soil screening does not distinguish missing/unknown from healthy and does not enforce measurement unit/method context.
4. Market comparison needs latest comparable mandi/variety/grade selection and dated cost/route assumptions.
5. Scheme eligibility is discovery, not implemented eligibility.
6. X-Farmer-ID is not authentication; CORS and public mutators need hardening before network deployment.
7. Idempotency needs intent-specific keys and atomic persistence/outbox handling.
8. Crop health has an opt-in TF Hub MobileNetV3 tomato-specialist TFLite integration. Its larger controlled PlantVillage benchmark is 0.955 dynamic-TFLite validation accuracy, but it is rejected for field release. The optional crop-router interface can only suggest ranked crops and always requires farmer confirmation; the only locally trained TF Hub router scored 0.4375 on a 64/16 controlled split and is rejected/not configured. Read the 7 September checkpoint sections before changing it.
9. No firmware, controller protocol, Android runtime or phone offline sync exists.

Hardware and team plan (6 September 2026):
- Treat the supplied Wokwi link/circuit image as a reference, not as a field-verified design. The Wokwi sources are not in the repository; export them first.
- Resolve the P0 issue before powering hardware: a genuine MAX3485 is a 3.3 V transceiver, while the supplied drawing appears to share a 5 V rail with it. Identify the actual module and protect ESP32 logic levels.
- Varuna owns electronics/power/calibration; Anwaar owns ESP32/RS485/Wokwi firmware; Prachi owns sensor-status UI; Harshwardhan owns device onboarding/history/demo UX; Aman owns device ingestion/authentication/validation; Pranav owns Codex/MCP integration and the ML/DL baseline.
- Preserve the separation: dedicated device ingestion is not the existing `record_sensor_reading` MCP tool, and neither the agent nor MVP controls a pump.
- The Codex/MCP integration is complete for the current non-hardware/non-ML scope. Keep it as a Python MCP adapter behind FastAPI; do not duplicate farm-domain tools in the Codex Rust core. Its portable plugin manifests and test evidence are in `PRANAV_CODEX_INTEGRATION_STATUS.md`.
- ML/DL research and release scaffolding now live in `ml/`. The FastAPI diagnosis endpoint accepts `confirmed_crop` and can run `local_tflite_demo` with the ignored TF Hub MobileNetV3 tomato-specialist dynamic TFLite artifact, persisting candidates, model metadata and limitations in local SQLite. `unknown`/“I do not know” routes to an optional suggestion-only crop router when one is configured; it cannot select a specialist. The default remains disabled. Complete the Android baseline only after the team locks a crop, region, target phone/SoC, label list, field-data permissions and agronomist review. A hosted crop.health call is an optional server-side secondary opinion, never proof of offline on-device inference.
- To run the deliberate controlled TFLite proof without modifying `.env`, use `powershell -ExecutionPolicy Bypass -File backend/scripts/run_local_tflite_demo.ps1 -Port 8001`. Use `-CheckOnly` first. It is tested against the included ignored artifact but must never be described as field-deployed.
- For the paired frontend/backend demonstration use `npm run demo:tflite:check` followed by `npm run demo:tflite`; Vite prints its actual URL if 5173 is occupied. The runner is tested and stops cleanly with Ctrl+C.
- The Digital Twin now includes a farmer-confirmed task loop. Use `/v1/tasks` and the MCP `list_field_tasks`, `create_field_task`, and `update_field_task_status` tools for actions; they are persisted SQLite records, not transaction or physical-control authorization. The next UI task is to surface this contract on the Field Detail/Crop Guide views.
- The `/tasks` Field Actions page now surfaces that contract with backend data and manual farmer-confirmed creation/completion. The next action-engine step is a reviewed rule that proposes (but never auto-creates) a task from a specific recommendation, then gives the farmer a clear acceptance control.
- Farm Finance now uses the farmer-scoped backend SQLite ledger: `/v1/ledger/entries` and `/v1/ledger/summary`, mirrored by MCP ledger tools. It is INR-only record keeping, and entries are voided rather than deleted. It is not yet an offline mobile-sync or accounting/tax/credit system.
- A dedicated device telemetry path now exists: `POST /v1/device-ingestion/observations` validates an environment-provisioned bearer credential scoped to its farmer/field, retains Modbus/CRC packet evidence, and copies only CRC-valid canonical samples into sensor history. `GET /v1/device-ingestion/devices` and MCP `list_device_health` are read-only. Provisioning is config-based for now; do not give a device token to the agent, and do not confuse these tests with real hardware/firmware evidence.
- Latest verification after finance/device work: backend `34 passed`; agent `12 passed`; UI `10 files / 15 tests`, lint, and production build passed. The frontend production bundle warning remains.
- Crop-stage action proposals are now available at `GET /v1/fields/{field_id}/action-proposals`, MCP `get_crop_stage_action_proposals`, and the Field Actions UI. They are generic, read-only prompts that omit already-open task titles; the farmer must explicitly accept one to create a task. Latest verification: backend `35 passed`; agent `12 passed`; UI `10 files / 15 tests`, lint and build passed.
- `ml/training/train_tfhub_classifier.py` now defaults to inverse-frequency class weights derived from the training folders and records them with the artifact. It also adds brightness augmentation. This is an approved robustness aid for a future licensed/consented field dataset, not new field-performance evidence for the current controlled tomato artifact. Latest ML verification: `9 passed`.
- Important vision correction: a real non-crop project image was confidently classified by the controlled tomato specialist. `local_tflite_demo` now exposes ranked candidates under `needs_expert_review` unless `CROP_HEALTH_TFLITE_RELEASE_MANIFEST_PATH` binds the exact model/labels to an `approved_for_field_release` manifest with passed independent field-held-out, unknown/OOD, and agronomist-review gates. Do not create or mount such a manifest without those actual evidence reports.
- `ml/training/train_tfhub_classifier.py` provides the executable TensorFlow Hub MobileNetV3/ EfficientNet-Lite0 transfer-learning scaffold. MobileNetV3 now warms up the head, then fine-tunes its ImageNet backbone at a lower learning rate; EfficientNet-Lite0 stays head-only because the configured TF Hub handle is TF1-based. `export_tfhub_tflite.py` produces FP32, dynamic-range, and calibrated INT8 candidates. `ml/orchestration/crop_router.py` still prevents ambiguous or unsupported routes in the legacy PyTorch path. Do not replace the configured specialist or enable a router without a versioned manifest and field-held-out evaluation.
- The TF Hub registry additionally exposes `mobilenet_v3_large`: use it as the
  accuracy-oriented, fine-tunable 224px specialist benchmark alongside
  `mobilenet_v3_small` and frozen `efficientnet_lite0`. It is not yet trained
  or selected; compare all candidates on the same field-held-out/OOD set and
  target Android device before changing any release configuration.
- `ml/training/evaluate_tflite_classifier.py` now reports field-held-out
  macro-F1, per-class precision/recall/confusion, supported-input coverage, and
  optional unknown/OOD true rejection at configured score/margin gates. Run it
  for each candidate before a manifest review; its JSON report is evidence only.
- The irrigation plan now prevents a high rain probability from deferring a
  critically dry reading and requests reassessment after an irrigation logged
  within 12 hours. It remains a generic read-only moisture screen; implement
  a true root-zone water balance only with recorded field capacity, root depth,
  crop coefficient, flow and calibration evidence.
- The Irrigation screen can now record a farmer-confirmed irrigation event;
  this feeds the 12-hour reassessment state but never controls equipment.
- `GET /v1/irrigation-events`, MCP `list_irrigation_events`, and the Irrigation
  history panel expose the same farmer/field-scoped recorded events. They are
  not flow telemetry and must not infer missing volume/duration.
- The controlled demo launcher now invokes `ml/training/validate_release_manifest.py`.
  It verifies artifact/label checksum, size, ordered scope labels, and gate
  shape; it still reports the current controlled artifact as rejected. Run
  `npm run demo:tflite:check` before a demo and never treat its success as field
  release approval.
- A protected live demo was last verified at frontend `http://127.0.0.1:5173/`
  and backend `http://127.0.0.1:8001/health`; expect health `degraded` if the
  optional Mongo reference database is unavailable, but require
  `diagnosis: local_tflite_demo` and farmer SQLite `available`.
- The Windows universal-data bootstrap has now installed a workspace-local
  MongoDB runtime and completed one official ingestion run. The restarted
  port-8001 demo reports `reference_database: available`; do not mistake the
  tiny current source sample (one market/crop record, 23 MSP records) for full
  market coverage. Check whether the optional n8n setup has completed before
  claiming scheduler activation.
- The n8n portion currently failed only because Windows lacks Visual Studio's
  **Desktop development with C++** workload required by `node-gyp` for
  `isolated-vm`. Do not call the scheduler active; manual CLI ingestion and
  Mongo/FastAPI remain live. Install that workload and rerun the existing setup
  script when scheduler automation is required.
- The existing `/pest` React flow now asks the farmer to confirm the crop before the photo is uploaded. Its client-side helper deliberately treats “I do not know” as a valid non-routing answer. Preserve this behavior when wiring a trained artifact: an unknown crop must not silently select a disease specialist.
- Current addition: `GET /v1/fields/{field_id}/crop-options` and MCP
  `get_crop_options` are transparent, farmer-scoped evidence screens. They
  combine SQLite field ownership with central Mongo crop metadata, report
  season/rotation/soil checks plus missing evidence/conflicts, and never claim
  “best crop,” profit, yield, fertilizer requirements, or purchase action.
  Backend tests were **44 passed** when this slice was added; live port-8001
  proof returned the sourced Kharif `Paddy(Common)` catalogue item with missing
  rotation/soil evidence. Build a validated crop recommendation model only
  after collecting local soil/yield/weather/price ground truth.
- The `/crop-guide` React screen now consumes that contract. It deliberately
  requires an explicit “Check crop options” action and presents source,
  evidence matches, conflicts and absent evidence—not an automatic choice.
  The previous crop pre-populates from the selected field but stays editable.
  UI verification after this wiring: **10 files / 16 tests**, lint and build
  passed; the existing roughly 693 kB uncompressed bundle warning remains.
- Current TensorFlow Hub shortlist: `mobilenet_v3_small` (fast router),
  `mobilenet_v3_large` (fine-tunable specialist), `efficientnet_v2_b0`
  (fine-tunable accuracy-versus-latency comparison), and frozen
  `efficientnet_lite0`. EfficientNetV2-B0 was added after checking TensorFlow's
  official retraining guide; it is not trained or selected. ML suite was
  **15 passed** after registry coverage. Compare all candidates on identical
  field-held-out/OOD and target-phone latency/battery tests before any runtime
  change.
- `ml/training/compare_tflite_candidates.py` now enforces like-for-like TF Hub
  comparison before it prints a candidate metric table: equal supported sample
  count, ordered labels, score/margin policy and OOD scope are mandatory. It
  is evidence only and cannot choose a model or edit a release manifest. ML
  tests are now **17 passed**.
- Crop-health feedback now has a complete farmer-facing contract:
  `POST /v1/diagnoses/{diagnosis_id}/feedback` persists an append-only,
  farmer-scoped confirmation/correction/unknown record with optional explicit
  sharing consent. The `/pest` UI exposes it only after a result. Every
  response says `requires_expert_review_and_separate_export`; do not add a
  shortcut that exports photos, relabels diagnoses, or retrains a model from
  farmer feedback. Latest checks: backend **45 passed**, UI **10 files / 17
  tests**, ML **17 passed**, lint and build passed.
- `ml/training/build_diagnosis_review_queue.py` converts only explicitly
  consented, label-bearing feedback from explicitly named farmer SQLite files
  into a local review manifest. It does not copy/upload images and hides local
  paths unless an authorised operator passes `--include-local-paths`. Its output
  is still marked `requires_agronomist_label_review_and_dataset_split`; do not
  connect it directly to a training folder or released model. ML tests are now
  **19 passed**.
- `train_tfhub_classifier.py` now defaults to fine-tunable
  `mobilenet_v3_large`; the old default was frozen TF1 EfficientNet-Lite0 and
  could reject a bare training command. Use `--backbone efficientnet_lite0
  --freeze-backbone` only for the frozen baseline. The review queue includes
  anonymized field-group and recorded capture-time metadata for later
  field/date-disjoint splitting. ML tests are now **20 passed**.
- `ml/training/build_reviewed_field_split.py` converts only explicit
  `crop-health-expert-review-v1` approvals into a metadata-only
  train/validation/field-test manifest. It refuses fewer than three field
  groups and refuses any assignment that leaves a label absent from a
  partition. It never copies images or starts training. A separate unknown/OOD
  challenge set remains mandatory. ML tests are now **23 passed**.
- `ml/training/materialize_reviewed_split.py` is the guarded final data-steward
  step: it only copies checksum-matching images from an expert-reviewed split,
  requires `--confirm-authorised-data-steward`, creates safe label folders, and
  rejects non-empty destinations. It neither uploads, trains nor approves a
  model. ML tests are now **25 passed**.
- Runtime smoke evidence: the exact EfficientNetV2-B0 TF Hub feature-vector
  handle loaded under TensorFlow **2.21.0** / TensorFlow Hub **0.16.1** and
  returned a `(1, 1280)` float32 feature tensor for one 224px RGB input. This
  proves only dependency/handle compatibility. It is not a field-accuracy,
  export or target-device result.
- Do **not** run a new EfficientNetV2-B0 benchmark from the remaining temporary
  PlantVillage folders: they were checked on 8 September 2026 and now contain
  only a few `healthy` images, not the former balanced four-class split. No
  benchmark was launched. Restore an approved balanced split for a controlled
  demo comparison, or use the field-data pipeline after real consented expert
  review.
- The deliberate demo stack is currently live at frontend
  `http://127.0.0.1:5173/` and backend `http://127.0.0.1:8001/health` with
  `reference_database: available` and `diagnosis: local_tflite_demo`. The
  launcher now passes Uvicorn reload exclusions as literal
  `--reload-exclude=<glob>` option values because PowerShell expands bare
  globs. Do not stop unrelated port-8000/Mongo processes. The TFLite manifest
  still makes all image results review-only.

Marketplace/Aman slice (6 September 2026):
- `/marketplace/listings` searches only source-attributed JSON-LD records ingested from operator-configured HTTPS public sources. It intentionally starts empty until `MARKETPLACE_DIRECTORY_SOURCES_JSON` is configured and ingestion is run.
- The React `/marketplace` route and MCP `search_marketplace_listings`, `find_seed_suppliers`, `find_fertilizer_suppliers`, `find_logistics_providers`, `find_crop_buyers`, and `find_exporters` call that same API. They are discovery-only and must not claim booking, purchase, sale, eligibility, stock, or guaranteed price.
- `/marketplace/compare-quotes` and its generic/machinery/logistics MCP helpers rank only explicit quote components. Do not add estimated freight, tax, insurance, exchange rates, or hidden costs without a trusted source and an explicit product requirement.
- `compare_msp_with_market` compares the newest official MSP source record with the newest sourced price per mandi. It is explicitly not procurement, grade, centre-availability, or eligibility confirmation.

Use shared contracts and tests. Keep domain logic out of the Codex Rust fork; preserve the existing FastAPI + Python MCP adapter boundary. Do not give the language agent direct physical control; domain services and the local controller own calculations, authorization and actuation.

Run relevant tests, read back the diff, update the existing backend change-memory documents when changing backend scope, and commit only your own deliberate files. At the end, update docs/sih26180/SESSION_CHECKPOINT_2026_09_05.md or create a new dated checkpoint with:
- what changed;
- tests/commands and result;
- decision changes;
- remaining risks/blockers;
- exact next recommended task;
- commit hashes.
```

Start by reporting the verified official SIH statement status and a compact Phase 0 execution plan. Then proceed with the most valuable authorized implementation work.

## 9 September 2026 MVP-readiness planning checkpoint

Before fixing the four current demo-screen defects, read
`docs/sih26180/MVP_INITIAL_DEMO_READINESS_PLAN_2026_09_09.md` completely. It is
the authoritative implementation plan for this slice.

Verified findings:

1. The demo profile contains `Pune, Maharashtra (local demo)` while Mongo
   records use `Pune` / `Maharashtra`. `MachineryRentals.jsx` and
   `Marketplace.jsx` parse the display string and send exact filters, so valid
   seeded rows are filtered out.
2. Field creation already uses Leaflet/OpenStreetMap in `LocationPicker.jsx`,
   but Farm Map uses a decorative SVG in `FieldTools.jsx`; all field labels use
   the same fixed coordinates.
3. The schemes screenshot is consistent with renderer/backend port drift: the
   client fallback is 8000 while the deliberate demo stack uses 8001.
4. Implement in this order: non-destructive baseline; one-command launcher and
   component diagnostics; structured location/geospatial APIs; real Leaflet
   farm map; field-centered marketplace/machinery map; scheme truthfulness;
   Codex parity; resilience and UAT.
5. Do not train another model or enable physical actuation in this slice.

The repository is dirty and existing changes are user-owned. Use `apply_patch`,
stage only deliberate files, update backend memory files for backend changes,
and commit each accepted wave atomically.

## Latest implementation handoff — 9 September 2026

The initial-demo readiness slice is implemented and verified. Read these files
before making further changes:

- `MVP_INITIAL_DEMO_READINESS_PLAN_2026_09_09.md`
- `MVP_IMPLEMENTATION_CHECKPOINT_2026_09_09.md`
- `MVP_BASELINE_2026_09_09.md`
- `DEMO_FAILURE_DRILLS.md`

Latest implementation commits are `ca31110`, `350cd08`, `052308d`, and
`ad6d652` after the earlier map/Codex commits. Verified gates: backend 51,
agent 12, UI 18, desktop 6, lint/build, `npm run demo:check`, and
`npm run demo:contracts` (53 adapter path shapes matched OpenAPI).

The canonical presentation command is `npm run demo:desktop`; use the explicit
PowerShell `-ResetDemo` switch for a clean demo identity. The launcher starts
FastAPI before seeding, attaches only to a compatible existing health service,
and refuses incompatible occupied backend ports. Native Electron screenshot
capture was unavailable through the current desktop automation surface; do not
claim native visual UAT without rechecking that environment.

Continue only with remaining pilot scope: real provider ingestion and freshness
operations, production identity/authentication, offline sync beyond bounded
reference caching, calibrated hardware/actuation, and field-evaluated crop
health. Keep all ML and hardware actions review-only until their release gates
are satisfied.
