# Session checkpoint 2026 09 05

## Purpose

This checkpoint preserves the deep-research and repository-audit work completed for KisanSathi, the proposed SIH26180 Smart Farming Assistant. It is designed for a new AI session to resume without reconstructing the research or rereading the entire repository.

Read files in this order:

1. [README](README.md)
2. [Research report](RESEARCH.md)
3. [Product requirements](PRD.md)
4. [Implementation plan](IMPLEMENTATION_PLAN.md)
5. [Source ledger](SOURCE_LEDGER.md)
6. [Deep Research source record](report-source.md)
7. [Continuation prompt](CONTINUATION_PROMPT.md)

The user asked for a field-deployable farmer assistant covering crop planning, inputs, crop health, irrigation, weather/disaster resilience, harvest/sale/logistics, government support, farm economics, voice and a farm digital twin. The immediate competition target is provisionally SIH26180, “AI-powered Smart Farming Assistant,” attributed to Qualcomm. The exact official SIH statement was unavailable from the official site during this session; community reproductions match the supplied text but should not be treated as authoritative for deadlines/category/judging.

## Artifacts created in this session

- RESEARCH.md: evidence-backed feasibility and architecture report with citations.
- PRD.md: product scope, user journeys, requirements, acceptance evidence, D0-D3 delivery boundaries and quality targets.
- IMPLEMENTATION_PLAN.md: concrete architecture, canonical contracts, IoT/control plan, model deployment, service boundaries, test matrix and phases.
- SOURCE_LEDGER.md: source-to-claim provenance for consequential research conclusions.
- report-source.md: canonical Deep Research synthesis, assumptions, limitations and search record.
- This checkpoint and CONTINUATION_PROMPT.md.

These documents were committed as a docs-only checkpoint. The canonical Deep Research source record was added in a follow-up documentation commit. Do not overwrite the existing August audit report or .planning documents without comparing their assumptions. They are pre-existing uncommitted work.

## Main recommendation

Build a focused, field-validated demonstrator first:

- one crop and one pilot area;
- Android local camera inference for a bounded disease/pest taxonomy;
- calibrated physical sensing;
- crop-stage/root-zone water balance;
- a controller with local manual override, hard bounds and flow feedback;
- weather and authoritative alert context when online;
- farmer-facing local-language actions, history and offline capture.

The broad full lifecycle remains the product roadmap. It should not absorb the time needed to prove the local hardware/AI loop.

## Facts verified from the current repository

Workspace: C:\Users\prana\Desktop\sih mvp
HEAD at inspection: 3e5dfbc (20 Aug 2026)
Working tree: already materially dirty with many modified/untracked files owned by the user. Preserve those files. This session has only added the documentation in docs/sih26180/.

Architecture:
- React/Vite application in src/.
- Electron desktop companion in desktop/.
- FastAPI backend in backend/.
- Python MCP service in agent/src/kisansathi_agent/.
- Existing desktop harness starts installed codex app-server, injects the KisanSathi plugin and routes through the Python MCP service. It does not prove the repository’s Codex fork binary is running.
- Farm state is server-side, per-farmer SQLite under backend/app/farm_state/. Shared reference data uses Mongo/Beanie.
- Current UI has 17 routes.
- MCP server registers 47 tools.
- FastAPI OpenAPI generation showed 61 paths.

Capabilities found:
- fields, boundaries, crop cycles/stages, soil tests, sensor readings, weather snapshots, alerts, reminders, diagnosis upload records, reports and manual interface;
- market data ingestion from data.gov.in/AGMARKNET scaffold;
- machinery, seed/fertilizer/scheme catalog interfaces;
- Sarvam STT/TTS/translation configuration;
- Electron-to-Codex/MCP conversation path;
- browser localStorage finance records.

Material gaps:
- no application-owned .onnx/.tflite/.pt artifact or model registry;
- diagnosis endpoint stores images but returns provider-unavailable/inconclusive;
- no firmware, device enrollment protocol, BLE/MQTT implementation, pump control, flow feedback or hardware tests;
- existing irrigation uses fixed 35/40% moisture values and 60% rain probability; it is not a validated water balance and must not control equipment;
- latest-weather query in irrigation plan is not field/coordinate scoped;
- soil screening uses unqualified threshold values and can imply no issue with missing measurements;
- market comparison uses all matching historical observations rather than selecting latest comparable mandi/variety/grade data, and transport defaults are not route quotes;
- scheme eligibility service does not implement substantive criteria;
- X-Farmer-ID is explicitly temporary identity, not authentication; CORS is wide open;
- browser finance and server farm state are different stores; server local SQLite is not phone offline storage;
- write idempotency is hash(path,payload), which can conflate distinct but identical intended actions; store operations commit per statement rather than atomic action+outbox transactions;
- no packaged Android runtime, no sync protocol and no demonstrated signed-in end-to-end Codex-to-MCP production session;
- no deployed marketplace/vendor quote integration, crop plan optimizer, yield model, price forecast, storage optimizer, satellite analytics or export workflow.

## Verification run in this session

All checks are baseline checks of the existing project, not validation of proposed features:

- npm run test:ui: 1 test passed.
- npm run test:desktop: 6 tests passed.
- backend python -m pytest -q: 14 tests passed; deprecation warnings.
- agent python -m pytest -q: 10 tests passed; settings forward-reference/deprecation warnings.
- npm run lint: passed.
- npm run build: passed; emitted 639.50 kB uncompressed primary JS bundle and size warning.
- FastAPI OpenAPI: 61 paths.

No Rust build, live Mongo/provider integration, field trial, sensor calibration, NPU benchmark, physical control test, paid API integration or official SIH verification was performed.

## Research conclusions to preserve

- Do not claim exact farm-level seasonal weather forecasts. IMD products have documented horizons; a coordinate response does not create field-scale forecast skill.
- Forecast-aware irrigation is correct only when projected root-zone depletion remains below the stress threshold before expected rain. Four-day rain does not fix stress tomorrow.
- Use FAO56 water balance as the transparent baseline; only add learned corrections after local measured data shows benefit.
- Low-cost NPK probes cannot be assumed to replace lab tests. A 2025 CGIAR evaluation found poor precision and moisture dependence in tested devices. Soil Health Card/lab reports should anchor nutrient decisions.
- Disease models trained on clean leaves face severe field-domain shift. Original PlantVillage results fell from 99.35% controlled test accuracy to 31.4% on differently sourced images. Use guided multi-view capture, local field labels, unknown outcomes, grouped data splits and a fixed held-out local test set.
- MobileNetV3-Small is a sensible first local classifier comparison; use a small detector for visible pests. Quantized, fixed-shape, supported-op execution must be profiled on the actual Qualcomm target; QNN HTP requirements include quantized models.
- Photo-only nutrient deficiency classification should remain screening; symptoms overlap with water/disease/age/root problems.
- Mandi prices are observed daily wholesale indicators, not buyer commitments. Forecast using backtests against naive baselines and show uncertainty/cost sensitivity.
- Organic/export conditions begin at crop planning and require records/certification/residue/packhouse workflow; a harvest-time buyer directory is inadequate.
- A seed certificate addresses identity/purity/germination, not yield guarantee. No universal yield guarantee was verified.
- MSP requires crop/state/season/procurement/registration/quality checks.
- SACHET CAP/RSS is an official alert feed. Preserve warning source, area, issue/expiry and cancellation/update state.
- Commercial competitor feature overlap exists (Plantix, Fasal, Cropin). Novelty comes from demonstrated offline, sensor-aware, stage-aware, uncertainty-aware decisions and real measurement, not from a broad feature list.

## Important citations and sources

The full links and limitations are in RESEARCH.md. Highest-impact sources include:

- FAO56 root-zone balance: https://www.fao.org/4/X0490E/x0490e0e.htm
- CGIAR low-cost soil sensor evaluation: https://cgspace.cgiar.org/items/66e9e012-8409-46dc-918e-af0883333d74
- IMD API reference: https://api.imd.gov.in/public/api_reference.html
- SACHET alerts: https://sachet.ndma.gov.in/
- PlantVillage domain shift study: https://arxiv.org/abs/1604.03169
- ONNX Runtime QNN: https://onnxruntime.ai/docs/execution-providers/QNN-ExecutionProvider.html
- Government mandi data: https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi
- FARMS machinery service: https://agrimachinery.nic.in/Index/farmsapp
- APEDA NPOP: https://npop.apeda.gov.in/
- Copernicus Sentinel-2: https://documentation.dataspace.copernicus.eu/Data/SentinelMissions/Sentinel2.html

## Current status and next recommended task

Deep research, PRD and implementation planning are complete enough to begin Phase 0. The next task should not blindly implement every plan item. It should first:

1. retrieve and verify the official SIH statement;
2. select exact pilot crop, state/district, farm partner and target Qualcomm device/board;
3. identify local agronomy reviewer and actual sensor/control hardware;
4. formalize Phase 0 contracts and create the D0 implementation plan;
5. if implementation is authorized, fix the current field-scoping, units/missing-data and action-idempotency defects before adding ML/hardware.

The next AI should inspect the actual current status and diff first, because other agents/users may modify source files after this checkpoint.

## Commit status

This checkpoint is versioned in the Git commit named `docs: add SIH smart farming research checkpoint`. That commit contains only `docs/sih26180/`; pre-existing user changes remain outside it.

Before using this checkpoint in a future session, run:

```text
git log -1 --stat --oneline -- docs/sih26180
git status --short
```

If a later session updates any document in this directory, it should add a new dated checkpoint or update this one with the new commit hash, tests, decisions and next task.

## Follow-up completion on 6 September 2026

The Deep Research skill's canonical `report-source.md` record was added after a final targeted official-SIH search. No official SIH26180 page was returned by searches limited to SIH, Smart India and MIC domains. The result does not disprove the supplied brief; it means the brief remains provisional until an organizer-owned page or document is available.

Documentation structural QA confirmed that all local Markdown links in `docs/sih26180/` resolve and `git diff --check` passed for the documentation update.
