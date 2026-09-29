# Roadmap: KisanSathi AI Harness

## Overview

This brownfield milestone turns the existing React/FastAPI application and
Python KisanSathi MCP adapter into a locally runnable Codex harness. Delivery
starts by protecting the dirty worktree and reconciling local history, then
proves the existing 28-tool plugin boundary, hardens backend identity and
contract semantics, closes truthful frontend workflows, expands the safe MCP
surface, and finishes with end-to-end Codex approval, provider-degradation,
cross-farmer, and audit gates. FastAPI remains the only domain/data authority;
the MCP adapter remains the domain-to-tool boundary.

**Roadmap basis:** six dependency-ordered phases recommended by the brownfield
research. **Granularity:** standard. **Phase numbering:** sequential.

**Requirement-count note:** the requirements file defines 47 explicit v1 IDs
and five v2 IDs. This roadmap maps all 47 v1 IDs exactly once.

## Boundaries carried through every phase

- `X-Farmer-ID` is a trusted local launcher/session selector for this MVP, not
  production authentication. Model arguments never select identity, headers,
  tokens, SQL, or filesystem paths. Production authenticated claims remain
  v2 (`AUTH-01`).

- Reads may be automatic only after farmer scope is established. Persistent
  writes require Codex approval, explicit farmer confirmation, backend
  idempotency, and the authoritative resulting record.

- No pump, valve, tractor, or machinery control; no booking/payment/purchase,
  loan, produce sale, subsidy submission, or other financial/legal commitment.

- Finance remains browser-local and the AI/MCP addition is stateless
  calculation only. Image diagnosis and audio/voice capabilities stay
  provider/transport-gated and must return safe degraded results until proven.

- FastAPI owns domain data and provider workflows. MCP must not read SQLite or
  Mongo directly, and farming business logic must not be reimplemented in
  `codex-core`.

## Phases

- [ ] **Phase 1: Workspace Reconciliation** - Protect WIP and establish a recoverable, evidence-based integration history.
- [ ] **Phase 2: Plugin Boundary & Existing Harness** - Package and prove the existing 28-tool MCP server through Codex's native loader path.
- [ ] **Phase 3: Backend Contracts, Identity & State Safety** - Make backend behavior stable, bounded, idempotent, and honestly farmer-scoped.
- [ ] **Phase 4: Frontend-Backed Farm Workflows** - Close backend parity and render truthful loading, freshness, empty, unavailable, and error states.
- [ ] **Phase 5: Safe MCP Capability Expansion** - Add task-oriented tools for the remaining supported farm workflows without widening unsafe boundaries.
- [ ] **Phase 6: Full Harness Acceptance & Release Gates** - Prove stdio, approval, degraded media/provider behavior, UAT, Rust gates, and traceability.

## Phase Details

### Phase 1: Workspace Reconciliation

**Goal**: The integration work can proceed without losing user-owned changes, duplicating branch history, or losing a rollback path.
**Depends on**: Nothing (first phase)
**Requirements**: INT-01, INT-02, VER-06
**Success Criteria** (what must be TRUE):

  1. A recoverable checkpoint contains the tracked and untracked WIP, and the operator can identify the starting branch, commit, status, and diff without using a destructive Git command.
  2. The operator has evidence showing whether `aman` contains required work; required changes are merged exactly once or the no-merge decision is recorded with its rationale.
  3. The existing Prachi and backend-fastapi merge commits remain reachable, and the integration history records conflicts, resolutions, validation, and rollback instructions.
  4. Later feature work can be reverted by atomic integration commits or by switching back to the protected checkpoint without overwriting unrelated user work.

**Verification Gates**:

  - Capture `git status --short`, `git diff --stat`, `git rev-parse HEAD`, and the checkpoint reference before reconciliation.
  - Verify `f731f78` and `84d727a` are ancestors of the integration base; inspect `aman` with `git merge-base`, `git log --left-right --cherry-pick`, and `git diff --name-status`.
  - Review the integration log and prove that no `git reset --hard`, `git clean`, or `git checkout --` was used.
  - Run the existing backend, agent, frontend lint, and frontend build baseline after conflict-heavy reconciliation.

**Plans**: TBD

### Phase 2: Plugin Boundary & Existing Harness

**Goal**: Codex can load the contained KisanSathi plugin and use the existing 28 farmer-scoped MCP tools with bounded, provenance-preserving results.
**Depends on**: Phase 1
**Requirements**: MCP-01, MCP-06, CODEX-01, CODEX-02, CODEX-03, CODEX-05, VER-02
**Success Criteria** (what must be TRUE):

  1. A local Codex session discovers the KisanSathi server through the fork's existing plugin loader and MCP connection manager, lists the 28 proven tools, and completes a representative read and approved write.
  2. The plugin has valid contained manifests, MCP transport configuration, a plugin-local launcher/dependency setup, and skill instructions; no committed secret, absolute developer path, or model-supplied farmer identity is required.
  3. MCP results are bounded and retain source, observed/freshness time, assumptions, confidence, warnings, request IDs, and explicit unavailable/degraded status where supplied by the backend.
  4. The packaged process keeps diagnostics on stderr and protocol traffic on stdout, and the KisanSathi skill tells Codex to gather context, ask for missing fields, distinguish facts from guidance, preserve provenance, respect language preference, and never invent data or physical actions.

**Verification Gates**:

  - From the project root, run `python -m pytest backend/tests -q` and `python -m pytest agent/tests -q`; preserve the exact commands and results.
  - Install/run the existing adapter with a temporary local identity and verify native `codex mcp list`/`codex mcp get kisansathi`, `tools/list`, and representative `tools/call` behavior.
  - Validate the portable `plugin.json`, `.codex-plugin/plugin.json`, root `mcp.json`, contained `cwd`/command, skill path, and dependency setup using the fork's plugin validator/loader tests.
  - Confirm no KisanSathi-specific connection-manager or farming business logic is added to `codex-core`; if a Rust fixture is needed, keep it in the existing MCP/plugin test seams.

**Plans**: TBD

### Phase 3: Backend Contracts, Identity & State Safety

**Goal**: FastAPI is a stable, bounded source of truth whose local farmer-state boundary, provider failures, and mutation semantics are safe for both the frontend and MCP.
**Depends on**: Phase 2
**Requirements**: INT-03, INT-04, API-01, API-04, API-05, API-06, API-07, API-08
**Success Criteria** (what must be TRUE):

  1. Every frontend adapter path used in scope has a matching OpenAPI route/response contract and focused success and validation-failure coverage.
  2. Irrigation advice reads do not create durable records; explicit persistence, where retained, is a separately tested idempotent operation, and supported write retries return one authoritative record rather than duplicates.
  3. Backend responses expose stable error codes, request IDs, retryability, provenance, and explicit provider-unavailable/inconclusive states; bounded or cursor/pagination-safe lists cannot flood model context.
  4. Two configured farmer identities cannot read or mutate each other's fields, alerts, reminders, reports, soil records, or crop cycles, and model-provided arguments cannot override launcher identity or transport credentials.
  5. Shared reference-data mutation, physical control, financial persistence, and production-auth claims remain outside the local farmer-facing contract.

**Verification Gates**:

  - Run the backend suite from `backend/` with `python -m pytest`; include route success/validation, OpenAPI inventory, provider failure, bounded-list, and request-ID assertions.
  - Add and pass focused tests for irrigation GET side effects, server-side idempotency/replay/conflict, advisor/diagnosis/voice mutation semantics, resource substitution, missing/forged identity, and reference-data authorization boundaries.
  - Use temporary per-farmer SQLite directories and prove farmer A/B isolation for reads and writes; do not use the demo database for mutation tests.
  - Treat any missing true-auth requirement as a documented local-MVP limitation, not as evidence of production multi-tenant security.

**Plans**: TBD

### Phase 4: Frontend-Backed Farm Workflows

**Goal**: A farmer can use every supported frontend workflow against backend contracts and can distinguish healthy, loading, empty, stale, unavailable, provider-error, and validation states without fabricated values.
**Depends on**: Phase 3
**Requirements**: FRM-01, FRM-02, FRM-03, FRM-04, FRM-05, FRM-06, FRM-07, FRM-08, FRM-09, FRM-10, FRM-11, FRM-12, FRM-13, FRM-14, FRM-15, FRM-16, API-02, API-03, VER-01
**Success Criteria** (what must be TRUE):

  1. Dashboard, fields, map, crop guide, soil, weather, and irrigation screens use backend IDs and values, preserve field/profile scope, and show independent per-source loading, empty, stale, unavailable, validation, and error states.
  2. Market, schemes, eligibility, and machinery workflows show source, units, assumptions, freshness, and bounded filters; scheme results never imply approval/submission and machinery never implies booking/contact success.
  3. Pest/diagnosis, advisor, and voice screens show only sourced provider results or unmistakable inconclusive/provider-unavailable/unsupported states; no canned label, transcript, answer, or agronomy value is presented.
  4. Reports, settings, preferred language, notification preferences, and alert acknowledgement use their shared contracts and survive refresh where persistence is part of the contract; finance remains explicitly stateless/browser-local and is never represented as backend truth.
  5. The frontend's lint and production build gates pass after integration, with any bundle-size warning recorded rather than mistaken for a functional failure.

**Verification Gates**:

  - Run `npm run lint` and `npm run build` from the project root.
  - Exercise browser/manual smoke flows for profile → field → map/detail, soil/weather/irrigation, market/schemes/machinery, reports/settings, provider-degraded diagnosis/advisor/voice, and finance-local behavior.
  - Break individual subrequests and verify the affected card/panel explains the condition while healthy data remains visible; verify missing coordinates and stale/provider metadata.
  - Verify crop guidance, seed/fertilizer recommendation, map, and scheme eligibility use bounded backend semantics shared with the eventual MCP tools.

**Plans**: TBD
**UI hint**: yes

### Phase 5: Safe MCP Capability Expansion

**Goal**: Codex exposes the remaining supported farm capabilities as task-oriented, bounded, identity-safe tools that mirror the hardened backend and frontend semantics.
**Depends on**: Phase 4
**Requirements**: MCP-02, MCP-03, MCP-07, MCP-08
**Success Criteria** (what must be TRUE):

  1. Codex can call explicit farm-map, field-update, crop catalog/guidance, seed recommendation, and fertilizer recommendation tools when backend support exists.
  2. Codex can call bounded schemes-eligibility, machinery-search, advisor-session/message, text diagnosis, and stateless finance-calculation tools; unsupported provider capabilities return safe degraded results and no finance ledger is persisted.
  3. Every new tool omits farmer ID, credentials, arbitrary paths, and policy controls from model arguments, carries correct read/write/provider annotations, enforces output bounds, and preserves backend provenance/freshness/assumptions.
  4. Market, scheme, weather, and provider text is handled as untrusted data: instruction-like content cannot change identity, approval policy, tool selection constraints, or write behavior.
  5. MCP client tests prove exact HTTP method/path/payload/header shaping, bounds, annotations, retry/error mapping, and authoritative results for the expanded surface.

**Verification Gates**:

  - Run `python -m pytest agent/tests -q` with schema uniqueness, no-identity-argument, HTTP shaping, output bound, annotation, retry, and error-envelope assertions for every added tool.
  - Run backend contract tests for every route introduced or changed by the expanded tools, using mocked reference/provider responses and no live external dependency for core scenarios.
  - Seed market/scheme/provider fixtures with prompt-injection text and prove it is returned as data without changing tool policy or farmer scope.
  - Verify central catalog CRUD, booking, physical control, payments, and finance persistence are not registered in the farmer-facing tool list.

**Plans**: TBD

### Phase 6: Full Harness Acceptance & Release Gates

**Goal**: A new Codex session can safely run the complete local harness with real MCP framing, explicit approvals, honest provider/media degradation, cross-farmer isolation, reproducible verification, and traceable release evidence.
**Depends on**: Phase 5
**Requirements**: MCP-04, MCP-05, CODEX-04, VER-03, VER-04, VER-05
**Success Criteria** (what must be TRUE):

  1. A real stdio subprocess and Codex integration test prove plugin load, server start, `tools/list`, representative read, approved write, rejection/cancel, and surfaced backend failure.
  2. Every persistent MCP write requires Codex approval plus tool-level farmer confirmation; denial/cancellation leaves state unchanged, timeout/retry creates one record, and the authoritative resulting record is returned.
  3. Image/audio capabilities are enabled only after transport, provider, type/size, redaction, timeout, and end-to-end tests pass; otherwise Codex and the UI return safe unsupported/provider-unavailable/inconclusive results.
  4. Browser/UAT scenarios cover daily briefing, map, soil/weather, irrigation confirmation, market/schemes, machinery, advisor/diagnosis/voice degraded paths, reports, finance boundaries, prompt-injection handling, and cross-farmer isolation.
  5. GSD verification/audit artifacts map every explicit v1 requirement to implementation evidence, automated/manual tests, and any design-dependent follow-up; Rust verification either passes through the repository `just` wrappers or records the exact platform blocker and runnable CI alternative.

**Verification Gates**:

  - Run the real MCP stdio harness against a temporary FastAPI stack and assert stdout is protocol-only, startup/shutdown are clean, and backend request IDs/identity/idempotency are observable.
  - From `codex/`, run `just fmt-check` and the targeted `just test -p codex-mcp` / `just test -p codex-core-plugins` commands; if Windows lacks `link.exe`, preserve the exact blocked command and CI host alternative required by VER-03.
  - Execute the eight acceptance scenarios from `CODEX_AI_HARNESS_MERGE_PLAN.md`, including approval denial, retry idempotency, degraded providers, and a second farmer context.
  - Complete the GSD UAT/audit pass and attach evidence for all 47 explicit v1 IDs.

**Plans**: TBD
**UI hint**: yes

## Requirement Coverage and Traceability

Every explicit v1 requirement in `.planning/REQUIREMENTS.md` is assigned to one
and only one phase:

| Requirement | Phase | Status |
|---|---|---|
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

**Coverage:** 47/47 explicit v1 requirements mapped exactly once.

## Progress

**Execution Order:** Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|---|---:|---|---|
| 1. Workspace Reconciliation | 0/TBD | Not started | - |
| 2. Plugin Boundary & Existing Harness | 0/TBD | Not started | - |
| 3. Backend Contracts, Identity & State Safety | 0/TBD | Not started | - |
| 4. Frontend-Backed Farm Workflows | 0/TBD | Not started | - |
| 5. Safe MCP Capability Expansion | 0/TBD | Not started | - |
| 6. Full Harness Acceptance & Release Gates | 0/TBD | Not started | - |

## Next Action

Run `$gsd-plan-phase 1` to convert the first phase's reconciliation gates into
executable plans. Do not modify application source while only approving or
planning this roadmap.

### Phase 7: Standalone Kisan Sathi Web migration

**Goal:** Build `Kisan Sathi Web/` as an independently installable and deployable web service containing its own frontend, backend, API contracts, provider-neutral LLM harness, farm-tool orchestration, authentication boundary, and hybrid browser/server computer-vision path without changing the existing application's behavior.
**Requirements**: WEB-01, WEB-02, WEB-03, WEB-04, WEB-05, WEB-06, WEB-07, WEB-08, WEB-09, WEB-10, CVWEB-01, CVWEB-02, MIG-01, MIG-02, WEBVER-01, WEBVER-02
**Depends on:** Phase 6
**Plans:** 3/16 plans executed

Plans:

- [x] 07-01-PLAN.md — Freeze migration manifest, selective-copy tooling, and baseline contracts.
- [ ] 07-02-PLAN.md — Complete the blocking package-legitimacy checkpoint.
- [x] 07-03-PLAN.md — Migrate standalone FastAPI domain/data behavior and data rehearsal tooling.
- [ ] 07-04-PLAN.md — Enforce authenticated claims and cross-tenant object isolation.
- [x] 07-05-PLAN.md — Build the canonical 78-tool registry and workflow safety policy.
- [ ] 07-06-PLAN.md — Prove the authenticated resumable read/write walking slice.
- [ ] 07-07-PLAN.md — Implement normalized provider adapters and server-only secrets.
- [ ] 07-08-PLAN.md — Migrate React to typed HTTP/SSE browser transport.
- [ ] 07-09-PLAN.md — Preserve voice and image upload parity with truthful fallbacks.
- [ ] 07-10-PLAN.md — Add release-gated browser ONNX screening and server fallback.
- [ ] 07-14-PLAN.md — Migrate core farm workflows with browser parity tests.
- [ ] 07-15-PLAN.md — Migrate reference, reporting, settings, and finance-boundary workflows.
- [ ] 07-11-PLAN.md — Compose, deploy, health-check, and observe the standalone stack.
- [ ] 07-12-PLAN.md — Run contract, security, and complete three-engine browser parity gates.
- [ ] 07-16-PLAN.md — Run load/failure gates and generate checksummed release evidence.
- [ ] 07-13-PLAN.md — Gate cutover and rehearse rollback with final release evidence.
