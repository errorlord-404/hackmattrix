# Requirements: KisanSathi AI Harness

**Defined:** 2026-08-19  
**Core Value:** A farmer can ask Codex for grounded farm help and trust the
answer and every confirmed change.

## v1 Requirements

### Integration and identity

- [ ] **INT-01**: The local integration branch contains the required `aman`
  changes exactly once, preserves the existing backend-fastapi and Prachi merge
  commits, and records the merge rationale.

- [ ] **INT-02**: The existing dirty worktree is protected by a recoverable
  checkpoint before branch reconciliation; no destructive Git command is used.

- [ ] **INT-03**: Every farmer-state backend request is scoped to the launcher
  identity and a model cannot provide or override `farmer_id`, headers, tokens,
  SQL, or arbitrary filesystem paths.

- [ ] **INT-04**: Two configured farmer identities cannot read or mutate one
  another's fields, alerts, reminders, reports, soil records, or crop cycles.

### Frontend-backed farm workflows

- [ ] **FRM-01**: Dashboard loads profile, fields, observations, soil,
  irrigation, weather, market, and alerts from backend contracts and renders
  independent loading, empty, stale, unavailable, and error states.

- [ ] **FRM-02**: A farmer can list, create, inspect, update where supported,
  and select their fields; field links and selectors use backend IDs rather than
  fixture IDs.

- [ ] **FRM-03**: Farm Map renders backend GeoJSON boundaries/centroids with a
  usable list fallback and correct field status/alert information.

- [ ] **FRM-04**: Crop Guide displays a selected field's recorded crop cycle,
  stages, and backend-backed guidance without inventing agronomy values.

- [ ] **FRM-05**: Soil Health displays sourced soil tests and latest
  observations with measurement time, provenance, and missing-data handling.

- [ ] **FRM-06**: Weather resolves location from stored field/profile data and
  displays provider timestamps, alerts, and explicit unavailable/offline states.

- [ ] **FRM-07**: Irrigation displays explainable read-only advice and records
  confirmed irrigation events/reminders without controlling equipment.

- [ ] **FRM-08**: Pest and Disease accepts a real user input, submits a supported
  diagnosis request, and displays a sourced result or explicit inconclusive /
  provider-unavailable response; it never shows a fabricated label.

- [ ] **FRM-09**: Market displays live summary/history/trend/MSP data and mandi
  comparison assumptions, source, units, and freshness; reference failure is
  isolated from farmer-state screens.

- [ ] **FRM-10**: Government Schemes supports bounded state search and eligibility
  checks using explicit farmer inputs and does not claim approval or submission.

- [ ] **FRM-11**: Machinery Rentals lists backend-backed providers with the UI's
  supported filters and does not imply booking/contact success without a backend
  workflow.

- [ ] **FRM-12**: AI Advisor creates/continues backend sessions, preserves
  provider response and citations/uncertainty, and never appends a canned local
  answer.

- [ ] **FRM-13**: Voice Assistant captures a supported browser input or reports a
  truthful unsupported/provider-unavailable result; it never inserts a canned
  transcript or answer.

- [ ] **FRM-14**: Reports can be created, listed, loaded, and refreshed from
  backend records with persisted result/status.

- [ ] **FRM-15**: Settings, preferred language, notification preferences, and
  alert acknowledgment use the shared profile/alert contracts while keeping
  translation/navigation presentation behavior local.

- [ ] **FRM-16**: Finance provides a clearly labeled stateless calculation using
  explicit inputs; browser-local ledger state is not silently persisted or
  represented as backend truth.

### Backend contracts

- [ ] **API-01**: Every frontend API adapter path has a matching OpenAPI route,
  response contract, and a focused test for success and validation failure.

- [ ] **API-02**: Farm-map, crop guidance/catalog, seed recommendation, and
  fertilizer recommendation routes are task-oriented and bounded for agent use.

- [ ] **API-03**: Machinery rental list/filter behavior and scheme eligibility
  behavior are stable, validated, and exposed with the same semantics used by
  the frontend.

- [ ] **API-04**: Read-only irrigation advice does not create or mutate a plan
  record on every GET; persistence is explicit and separately tested.

- [ ] **API-05**: Advisor, diagnosis, voice, sensor, and supported mutation
  routes return stable error codes, request IDs, retryability, and explicit
  provider-unavailable/inconclusive states.

- [ ] **API-06**: Supported writes enforce idempotency server-side, not only in
  the MCP client, and duplicate requests do not create duplicate records.

- [ ] **API-07**: List endpoints used by frontend and MCP are bounded or
  cursor/pagination-safe and cannot inject unbounded content into model context.

- [ ] **API-08**: Backend tests prove farmer isolation, provider failure behavior,
  request validation, route side-effect rules, and response provenance.

### MCP tool surface

- [ ] **MCP-01**: The existing 28 proven tools continue to list and execute over
  stdio with read/write annotations and bounded common result envelopes.

- [ ] **MCP-02**: Add explicit tools for farm map, crop catalog/guidance, seed
  recommendation, fertilizer recommendation, and field update where backend
  support exists.

- [ ] **MCP-03**: Add explicit tools for diagnosis, advisor sessions/messages,
  schemes eligibility, machinery rental search, and stateless finance
  calculation with truthful capability gating.

- [ ] **MCP-04**: Image and audio tools are enabled only after transport,
  provider, type/size-limit, redaction, timeout, and end-to-end tests pass;
  otherwise they return a safe degraded result rather than pretending support.

- [ ] **MCP-05**: MCP writes require Codex approval plus tool-level confirmation
  semantics, use backend-enforced idempotency, and return the authoritative
  resulting record.

- [ ] **MCP-06**: MCP results preserve source, observed/freshness time,
  assumptions, confidence, warnings, and next actions where available.

- [ ] **MCP-07**: Prompt-injection text in market, scheme, weather, or provider
  data is treated as untrusted data and cannot alter tool policy or identity.

- [ ] **MCP-08**: MCP client tests cover tool schemas, HTTP method/path/payload,
  identity headers, output bounds, annotations, retries, and error mapping.

### Codex CLI harness

- [ ] **CODEX-01**: KisanSathi is packaged inside `codex/` as a valid plugin
  with portable manifest, Codex overlay, local MCP declaration, skill
  instructions, and reproducible server dependency setup.

- [ ] **CODEX-02**: The plugin uses the fork's existing plugin loader and MCP
  connection manager; no duplicated farming business logic is added to
  `codex-core`.

- [ ] **CODEX-03**: Plugin launch paths are portable and contained, work on
  Windows/macOS/Linux, inherit backend/farmer configuration without committed
  secrets, and keep protocol output on stdout only.

- [ ] **CODEX-04**: A Codex integration test proves plugin load, MCP server
  start, `tools/list`, representative read, approved write, rejection/cancel,
  and surfaced backend failure.

- [ ] **CODEX-05**: The KisanSathi skill instructs Codex to gather context,
  preserve provenance, ask for missing fields, distinguish facts from guidance,
  use preferred language, and never invent unavailable data.

### Verification and operations

- [ ] **VER-01**: Frontend lint and production build pass after integration.
- [ ] **VER-02**: Backend and MCP unit/contract tests pass with reproducible
  commands and no hidden external-service dependency for core scenarios.

- [ ] **VER-03**: Codex Rust formatter and targeted MCP/plugin/core integration
  tests pass, or a platform prerequisite is documented with the exact blocked
  command and a runnable CI alternative.

- [ ] **VER-04**: Browser/UAT scenarios cover daily briefing, map, soil/weather,
  irrigation confirmation, market/schemes, machinery, advisor/diagnosis/voice
  degraded paths, reports, finance boundary, and cross-farmer isolation.

- [ ] **VER-05**: GSD verification and audit artifacts map every requirement to
  implementation evidence, tests, and any manual-only follow-up.

- [ ] **VER-06**: Changes are committed atomically with no accidental overwrite
  of unrelated user work and a recoverable local rollback path.

## v2 Requirements

- **AUTH-01**: Replace temporary `X-Farmer-ID` with authenticated session claims,
  authorization middleware, and audit logging.

- **PHYS-01**: Add safely authorized machinery/pump/device actions with explicit
  scopes, confirmations, limits, and emergency-stop semantics.

- **FIN-01**: Add a consented, authenticated, retained finance ledger and
  audit-ready financial actions.

- **MEDIA-01**: Add production-grade speech-to-text/text-to-speech and image
  diagnosis providers with evaluated model quality and privacy controls.

- **DATA-01**: Add device-authenticated sensor ingestion and scheduled reference
  feed operations outside conversational tool calls.

## Standalone Web Migration Requirements (Phase 7)

### Standalone packaging and deployment

- [x] **WEB-01**: `Kisan Sathi Web/` contains all runtime frontend, backend,
  harness, API, configuration, migrations, model manifests, and deployment files
  needed to build and run without importing source from the parent application.

- [ ] **WEB-02**: The standalone service has reproducible local and production
  startup paths, health/readiness checks, environment validation, container
  definitions, persistent-volume contracts, and secret-injection documentation.

- [ ] **WEB-03**: Browser clients use authenticated user/session claims; they do
  not control farmer identity through `X-Farmer-ID`, URL parameters, model tool
  arguments, or browser-stored provider secrets.

### Provider-neutral web harness

- [ ] **WEB-04**: The harness exposes a provider-neutral streaming conversation
  interface with explicit capability flags for text, vision, tools, structured
  output, streaming, and cancellation.

- [ ] **WEB-05**: OpenAI, Anthropic, Gemini, OpenAI-compatible, and local/self-hosted
  models can be added through isolated adapters without changing farm tools,
  workflow policy, persistence, or the browser protocol.

- [ ] **WEB-06**: Provider credentials are accepted and stored only through a
  server-side secret boundary; credentials are redacted from logs, responses,
  tool arguments, browser storage, and persisted conversation content.

- [ ] **WEB-07**: Conversation sessions, streaming events, reconnect/resume,
  interruption, tool progress, clarification, and approval requests work over
  web transports without Electron IPC or a locally spawned Codex process.

### Tool orchestration and parity

- [x] **WEB-08**: The existing farm tool contracts remain available through one
  canonical registry, with workflow-specific allowlists so only relevant tools
  are sent to a model on each turn.

- [ ] **WEB-09**: Read/write annotations, explicit farmer confirmation,
  server-enforced authorization, idempotency, audit evidence, bounded outputs,
  provenance, freshness, unavailable states, and physical/financial safety
  boundaries are preserved independently of the selected LLM provider.

- [ ] **WEB-10**: The web frontend replaces `window.kisanHarness` with a typed
  HTTP/SSE or WebSocket client while preserving text, images, voice,
  localization, tool events, approvals, cancellation, and degraded fallbacks.

### Browser and server computer vision

- [ ] **CVWEB-01**: An approved, versioned classifier can run in a Web Worker
  through ONNX Runtime Web using WASM universally and WebGPU opportunistically,
  with identical preprocessing, labels, score/margin gates, checksums, quality
  checks, and limitations to the server release contract.

- [ ] **CVWEB-02**: Unsupported devices, model-load failures, low-confidence/OOD
  results, and authoritative persistence fall back to the backend inference and
  expert-review path without presenting a browser candidate as a diagnosis.

### Migration and verification

- [ ] **MIG-01**: The initial standalone copy has a documented source manifest
  mapping every copied/adapted module to its original, exclusions are explicit,
  and generated/runtime/vendor data is not copied.

- [ ] **MIG-02**: Existing source remains untouched during migration execution;
  all implementation writes stay under `Kisan Sathi Web/` except explicit
  planning evidence and no runtime import points back to the parent tree.

- [ ] **WEBVER-01**: Contract/parity tests prove all required farm workflows and
  tool safety semantics behave equivalently across the Electron baseline and
  standalone web harness before cutover.

- [ ] **WEBVER-02**: Browser, backend, harness, provider-adapter, CV fallback,
  authentication, tenant-isolation, deployment, load, failure-injection, and
  rollback tests pass with reproducible evidence.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Native Rust reimplementation of all farming business logic | Duplicates the tested MCP/backend boundary and increases drift risk |
| Autonomous physical control or financial commitment | No approved authorization, emergency-stop, or audit contract |
| Silent finance-ledger migration | Existing data is browser-local and has no consent/retention contract |
| Claiming image/audio success without transport/provider verification | Would create unsafe false capability |
| Production auth in this milestone | Requires deployment/session infrastructure beyond the current local MVP |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INT-01 | Phase 1 | Pending |
| INT-02 | Phase 1 | Pending |
| INT-03 | Phase 3 | Pending |
| INT-04 | Phase 3 | Pending |
| FRM-01 | Phase 4 | Pending |
| FRM-02 | Phase 4 | Pending |
| FRM-03 | Phase 4 | Pending |
| FRM-04 | Phase 4 | Pending |
| FRM-05 | Phase 4 | Pending |
| FRM-06 | Phase 4 | Pending |
| FRM-07 | Phase 4 | Pending |
| FRM-08 | Phase 4 | Pending |
| FRM-09 | Phase 4 | Pending |
| FRM-10 | Phase 4 | Pending |
| FRM-11 | Phase 4 | Pending |
| FRM-12 | Phase 4 | Pending |
| FRM-13 | Phase 4 | Pending |
| FRM-14 | Phase 4 | Pending |
| FRM-15 | Phase 4 | Pending |
| FRM-16 | Phase 4 | Pending |
| API-01 | Phase 3 | Pending |
| API-02 | Phase 4 | Pending |
| API-03 | Phase 4 | Pending |
| API-04 | Phase 3 | Pending |
| API-05 | Phase 3 | Pending |
| API-06 | Phase 3 | Pending |
| API-07 | Phase 3 | Pending |
| API-08 | Phase 3 | Pending |
| MCP-01 | Phase 2 | Pending |
| MCP-02 | Phase 5 | Pending |
| MCP-03 | Phase 5 | Pending |
| MCP-04 | Phase 6 | Pending |
| MCP-05 | Phase 6 | Pending |
| MCP-06 | Phase 2 | Pending |
| MCP-07 | Phase 5 | Pending |
| MCP-08 | Phase 5 | Pending |
| CODEX-01 | Phase 2 | Pending |
| CODEX-02 | Phase 2 | Pending |
| CODEX-03 | Phase 2 | Pending |
| CODEX-04 | Phase 6 | Pending |
| CODEX-05 | Phase 2 | Pending |
| VER-01 | Phase 4 | Pending |
| VER-02 | Phase 2 | Pending |
| VER-03 | Phase 6 | Pending |
| VER-04 | Phase 6 | Pending |
| VER-05 | Phase 6 | Pending |
| VER-06 | Phase 1 | Pending |

**Coverage:**

- Explicit v1 requirements: 47 total
- Mapped to phases: 47
- Unmapped explicit IDs: 0
- The v1 count is authoritative at 47 explicit IDs; no undefined requirements
  are being fabricated or assigned silently.

---
*Requirements defined: 2026-08-19*
*Last updated: 2026-08-19 after brownfield research kickoff*
