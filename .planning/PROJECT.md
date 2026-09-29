# KisanSathi AI Harness

## What This Is

KisanSathi is a farmer-facing web application backed by FastAPI and a local
farmer-state data layer, with market, schemes, crop, weather, and other shared
reference services. This milestone turns the existing merged application and
KisanSathi MCP adapter into a working AI harness inside the forked Codex CLI:
Codex should discover farmer-scoped tools, call the same backend used by the
frontend, request approval for writes, and preserve source, freshness, and
uncertainty in its answers.

## Core Value

A farmer can ask Codex for grounded, actionable farm help and trust that every
fact comes from the correct farmer's backend state or an explicitly identified
provider, while every state change remains confirmed and auditable.

## Requirements

### Validated

- ✓ React application routes exist for dashboard, fields, map, soil, weather,
  crop guide, irrigation, pest, market, schemes, finance, machinery, AI,
  voice, reports, and settings — existing merged frontend baseline.
- ✓ FastAPI exposes the current farm-state, weather, assistant, reference,
  ingestion, and machinery routes — existing merged backend baseline.
- ✓ The standalone `agent/` package exposes 28 farmer-scoped MCP tools with
  bounded result envelopes, launcher-owned farmer identity, idempotent writes,
  and explicit degraded/provider-unavailable results.
- ✓ Prachi voice and backend-fastapi merge commits are already reachable from
  the local `pranav` branch.

### Active

- [ ] Complete the local branch reconciliation, including an evidence-based
  decision and merge of required `aman` changes without losing current WIP.
- [ ] Make the frontend's visible business data use the backend contracts and
  show loading, empty, stale, unavailable, and provider-error states truthfully.
- [ ] Close backend contract gaps for every supported frontend feature,
  including map, crop guidance, schemes eligibility, machinery, advisor,
  diagnosis, and finance calculator boundaries.
- [ ] Package the existing KisanSathi MCP server as a Codex-discoverable local
  plugin under the fork, using the fork's existing MCP connection manager and
  plugin loader.
- [ ] Expose a complete, task-oriented MCP tool matrix for backend-backed
  frontend capabilities, with no farmer ID or credentials in model arguments.
- [ ] Require explicit approval/confirmation for state-changing operations and
  keep physical control, purchases, payments, and unapproved submissions out of
  the tool surface.
- [ ] Preserve provenance, freshness, assumptions, confidence, output bounds,
  and explicit unavailable/inconclusive results through backend → MCP → Codex.
- [ ] Add automated backend, frontend, MCP, plugin-loader, and cross-farmer
  integration verification with reproducible local commands.
- [ ] Run a GSD UAT/audit pass, classify findings, fix all safe findings, and
  leave any design-dependent items explicitly documented.

### Out of Scope

- Autonomous pump, valve, tractor, or machinery control — the current backend
  does not provide a safe authorization and emergency-stop contract.
- Purchasing, payments, loans, produce sales, subsidy submissions, or other
  financial/legal commitments — these require separate authorization and audit
  design.
- Persisting the browser-local finance ledger in the backend — first provide a
  stateless calculator; persistence requires consent, retention, and security
  decisions.
- Image diagnosis and audio voice tools until Codex/MCP attachment transport,
  size limits, provider configuration, and end-to-end tests are proven.
- Reimplementing FastAPI domain logic as native Rust handlers in `codex-core` —
  the Python MCP adapter remains the domain-to-tool boundary.
- Production authentication — `X-Farmer-ID` is a temporary local development
  identity boundary and must be replaced by authenticated session claims before
  deployment.

## Context

- The root Git worktree is on `pranav`; the working tree is intentionally dirty
  with existing user changes and untracked backend, frontend, and `agent/`
  files. Work must preserve all of them.
- `codex/` is a source directory inside this worktree, not a separate Git
  repository. Its Rust MCP code lives under `codex/codex-rs/codex-mcp`, and its
  plugin loader lives under `codex/codex-rs/core-plugins`.
- Existing planning notes are `FRONTEND_BACKEND_MERGE_PLAN.md`,
  `MCP_AGENT_IMPLEMENTATION_PLAN.md`, and
  `CODEX_AI_HARNESS_MERGE_PLAN.md`. Existing codebase maps are in
  `.planning/codebase/`.
- The current frontend has live API adapters and contexts in the worktree, but
  older codebase maps describe the pre-integration fixture-only state. Live
  source and tests are authoritative when they differ.
- The FastAPI service keeps farmer-owned state behind the temporary
  `X-Farmer-ID` boundary and shared reference data in its reference store.
- Codex's local contribution rules require MCP mutations to use the existing
  connection manager, favor integration tests, avoid unnecessary additions to
  `codex-core`, and run the repository's `just` wrappers for Rust formatting and
  tests.

## Constraints

- **Safety**: Reads can be automatic; writes need Codex approval and explicit
  farmer confirmation; no tool may claim a physical action occurred without a
  backend contract and result.
- **Data integrity**: The backend is the source of truth. MCP must not read
  SQLite/Mongo files directly or invent missing values.
- **Identity**: Farmer identity is launcher/session-owned, never model-selected,
  and every farmer-state request must carry it consistently.
- **Compatibility**: The Codex fork must keep existing MCP/plugin behavior and
  platform path rules on Windows, macOS, and Linux.
- **Traceability**: Every requirement must map to one GSD phase and a concrete
  test or acceptance scenario.
- **Change safety**: Existing dirty files, local branches, and backup stashes
  are user-owned. No destructive Git operation is permitted.
- **Provider uncertainty**: Weather, diagnosis, advisor, voice, and external
  reference feeds must expose freshness and provider failure states honestly.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use the existing Python MCP adapter as the Codex plugin's server | Prevents 28 duplicated Rust/API implementations and keeps backend rules centralized | — Pending integration verification |
| Make the Codex integration plugin-owned | The fork already discovers plugin-owned MCP servers and has a dedicated MCP connection manager | — Pending packaging verification |
| Keep finance persistence deferred and expose only a stateless calculator first | Browser-local finance data has no approved backend/privacy contract | — Pending feature decision |
| Gate image and audio capabilities on transport/provider tests | A tool schema alone would falsely claim support | — Pending transport verification |
| Use local-only branch reconciliation | User explicitly requested local merging and the worktree is dirty | ✓ Good if checkpoints and tests remain recoverable |

---
*Last updated: 2026-08-19 after starting the Codex AI harness implementation milestone*
