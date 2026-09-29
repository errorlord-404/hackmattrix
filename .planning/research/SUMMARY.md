# KisanSathi AI Harness Research Summary

**Project:** KisanSathi AI Harness
**Milestone:** Brownfield Codex integration and frontend/backend contract completion
**Researched:** 2026-08-19
**Confidence:** MEDIUM-HIGH

## Executive Summary

KisanSathi is an existing farmer-facing React application backed by FastAPI, with local farmer-owned state and shared reference/provider data. The confirmed architecture keeps FastAPI as the only domain and data authority: the frontend calls REST contracts, the Python `agent/` package adapts those contracts into 28 bounded farmer-scoped MCP tools, and the forked Codex CLI launches that adapter through its existing stdio MCP connection manager and Agent Plugin loader. Farming business logic should not be reimplemented in Rust or accessed directly from SQLite/Mongo. Farmer identity remains launcher/session-owned and must never be a model argument.

The recommended delivery strategy is a thin vertical proof followed by contract hardening and controlled capability expansion. First protect the dirty worktree and reconcile local branch history, then prove the existing adapter over native Codex MCP configuration and package it as a contained plugin without adding new domain tools. Next make backend semantics safe and testable—especially irrigation read purity, idempotent writes, stable errors/request IDs, bounded lists, and the local identity boundary—while the frontend closes truthful loading/empty/stale/unavailable states. Only then expand MCP coverage for map, crop guidance, schemes eligibility, machinery, advisor, diagnosis, voice, and stateless finance where the underlying contracts are real.

The main risks are security and false capability claims rather than basic connectivity. `X-Farmer-ID` is validated but spoofable, shared reference-data writes are unauthenticated, Codex write annotations are not an approval state machine, and the provider-assisted routes currently return safe degraded responses rather than useful provider results. The roadmap must make those limitations explicit, test cross-farmer isolation and approval/retry behavior end to end, and keep image/audio, financial persistence, physical control, and production authentication behind their stated gates.

## Confirmed Architecture and Stack

### System boundaries

```text
Farmer/operator
      |
Forked Codex CLI -- existing MCP connection manager/plugin loader
      |
KisanSathi plugin -- stdio --> Python FastMCP adapter (`agent/`)
                                  |
                            X-Farmer-ID from launcher config
                                  |
                              FastAPI backend
                         /                       \
              farmer SQLite state          Mongo/reference/providers
      React frontend --------------------------^ 
```

- **Frontend:** React/Vite pages, contexts, and API clients. `FarmDataProvider` owns profile/fields/map/alerts; `AIConversationProvider` owns advisor, voice, and diagnosis actions. The frontend remains a REST client and must not depend on MCP or direct databases.
- **Backend:** FastAPI exposes approximately 58 OpenAPI paths. Farmer state is stored in a per-validated-ID SQLite store; shared catalogs and market/scheme/machinery data use Mongo/Beanie routers; provider routes return structured degraded states when not configured.
- **MCP adapter:** Python 3.11+ package using FastMCP, `httpx`, and Pydantic. It owns backend calls, headers, request IDs, idempotency keys, result bounds, tool schemas, and safety annotations. Current tests cover the 28-tool baseline.
- **Codex integration:** Native `[mcp_servers.kisansathi]` configuration is the shortest proof path. The distributable target is a plugin-root `plugin.json` plus root `mcp.json`, `skills/kisansathi/SKILL.md`, and a plugin-contained launcher/source. Existing `codex-mcp` and `core-plugins` boundaries should be reused without a KisanSathi-specific connection-manager or Rust business-tool branch.

### Technology decisions confirmed by evidence

- Keep the existing Python adapter as the single source of truth; do not duplicate it under `codex-core` or `codex-mcp`.
- Use stdio MCP with stderr diagnostics and protocol-only stdout. Use native config for the first local proof, then a contained portable plugin for distribution.
- Keep `KISANSATHI_FARMER_ID` and backend configuration outside model schemas and published secrets. It is a controlled local identity boundary, not production authentication.
- Preserve bounded result envelopes carrying source, freshness/observed time, assumptions, confidence, warnings, request IDs, and explicit unavailable/inconclusive status.
- Treat reads as automatic only after farmer scope is established. Persistent writes require Codex approval plus explicit farmer confirmation, backend idempotency, and an authoritative resulting record.
- Keep finance ledger state browser-local for this milestone; the only safe initial AI capability is a stateless calculator with explicit inputs.

## Key Findings

### Codex MCP integration (`CODEX_MCP.md`)

The adapter is already shaped for Codex: one long-lived stdio process, mandatory validated launcher farmer ID, bounded output, timeouts, generated request IDs, idempotent writes, and no farmer ID in tool schemas. The example native configuration uses `cwd`, `required`, startup/tool timeouts, and `default_tools_approval_mode = "writes"`; it is suitable for local development but not a portable distribution contract.

The fork's plugin parser requires contained regular `plugin.json`/`mcp.json` files, plugin-relative commands or a bare executable, contained `cwd`, and supported path placeholders. A plugin manifest is not a secure identity injection mechanism. Distribution therefore needs a reproducible Python environment/launcher and a user-local identity path. Rust changes should be limited to fixtures or narrowly demonstrated generic gaps.

### Backend contracts (`BACKEND_CONTRACTS.md`)

The two data planes and current route/tool matrix are largely present, but “route exists” is not equivalent to “safe, complete capability.” The highest-priority contract defect is `GET /v1/fields/{field_id}/irrigation-plan`, which inserts a plan on every read. Other material gaps include missing idempotency for sensor/diagnosis/advisor/voice mutations, inconsistent error envelopes, absent server-side request-ID echo/persistence, unbounded list routes, incomplete advisor streaming/history, and no authenticated ownership boundary.

Existing farmer-safe tools cover overview, profile, fields, field timeline, soil, observations, weather, irrigation/reminders, alerts, reports, market, MSP, and scheme listing. Missing or partial parity includes an explicit farm-map tool, field update, crop/catalog/guidance and seed/fertilizer recommendations, scheme eligibility, machinery search, advisor workflow, diagnosis, voice, and finance calculation. Central reference-data CRUD must stay out of the farmer-facing tool surface until role protection exists.

### Frontend coverage (`FRONTEND_COVERAGE.md`)

The navigable shell is complete: 17 routes are registered, no route points to `PlaceholderPage`, and active business values are API-derived rather than legacy fixtures. Profile/settings, fields, map, field detail, soil, weather, irrigation/reminders, market, schemes listing, machinery listing, reports, diagnosis transport, advisor transport, and voice transport form usable vertical slices. `npm run lint` and `npm run build` pass; the build emits a large-main-chunk warning.

The frontend is not feature-complete. Dashboard and soil/irrigation sub-request failures can silently become blank cards; irrigation lacks initial loading; Crop Guide is only a recorded timeline viewer; schemes do not call eligibility; market history/MSP are unused; reports lack detail/export; advisor stream/history is not consumed; and provider-assisted features are transport-live but output-gated. Finance is intentionally local storage and must not be mistaken for backend truth. The strongest frontend dependency order is fields/identity/map, then soil/weather/irrigation decisions, then reference data, then provider workflows, then reports/alerts/local finance polish.

### Testing and security (`TESTING_SECURITY.md`)

The current green baseline is real but narrow: backend tests are **11/11**, agent tests **8/8**, frontend lint/build pass, and compileall passes. The backend and agent suites use appropriate temporary SQLite and mocked HTTP patterns. There are no frontend unit/component/browser tests, no MCP stdio harness, no Codex approval lifecycle test, no prompt-injection evaluator, and no complete cross-process farmer-isolation test.

The release-blocking security findings are: arbitrary `X-Farmer-ID` selection/default-to-`demo`; no resource ownership or role model; unauthenticated shared reference-data mutation; permissive credentialed CORS; and no immutable approval/audit record. These are not fixed by MCP annotations alone. Production authentication is out of this milestone, so the roadmap must either explicitly constrain the milestone to trusted local use or introduce a minimal authenticated subject boundary before any broader deployment claim.

## Conflicts, Risks, and Required Decisions

### Conflicts to resolve in roadmap definition

1. **Aman merge timing conflicts.** The requirements and merge plan place branch reconciliation in the first integration phase, but the merge plan's final checkpoint says to prove the plugin shell before merging Aman. Recommended decision: protect the WIP first, perform a read-only Aman ancestry/diff audit immediately, and merge exactly once before feature work only if required changes are evidenced. If the shell-first checkpoint is retained, document why the audit result permits postponement; do not silently choose an order.
2. **Plugin source ownership is unresolved.** Research permits using `agent/` as a plugin root or a packaging directory; the merge plan proposes promoting it to `codex/plugins/kisansathi/server/`. Choose one canonical source and make any transition atomic. Do not leave two independently edited Python implementations.
3. **Local native config versus final plugin packaging.** Native config is the fastest proof and supports explicit approval settings; portable `mcp.json` owns transport while Codex policy owns approval and enablement. Treat native config as Phase-1 validation, not the final artifact.
4. **v1 identity requirements versus production-auth scope.** INT-03/04 require launcher-scoped identity and isolation, while AUTH-01/production authentication are v2/out of scope. The roadmap must define “secure enough” for a local harness: prove model arguments cannot override launcher identity and prove two honest configured processes cannot cross data, while labeling header spoofing as an accepted local-only limitation.
5. **Full frontend parity versus provider readiness.** Requirements ask for advisor, diagnosis, voice, and finance capabilities, while current providers are unavailable and media transport is not proven end to end. Implement truthful degraded states and stateless/local boundaries first; only promote these to supported tools after explicit gates pass.

### Top risks and prevention

- **Cross-farmer data access:** replace header-selected subject with authenticated claims in a future deployment; now add missing/forged-header, resource-substitution, two-process, and no-model-override tests.
- **Unapproved or duplicated writes:** keep Codex write approval and explicit confirmation distinct; add stdio/app-server tests for preview, approval, denial, cancellation, timeout, retry, idempotency, and unchanged state after rejection.
- **Read endpoints mutating state:** make irrigation advice pure and add explicit idempotent persistence; document weather cache writes as infrastructure side effects.
- **False provider capability:** preserve `provider_unavailable`/`inconclusive`; gate image/audio and advisor quality on provider, size/type, privacy, timeout, and end-to-end tests.
- **Shared catalog mutation:** make farmer-facing reference routes read-only; isolate admin/ingestion roles and test the route matrix.
- **Unbounded or low-fidelity answers:** paginate/bound upstream lists, preserve provenance/freshness/assumptions, standardize error envelopes, and treat external text as untrusted data for prompt-injection evaluation.
- **Platform/package drift:** lock Python dependencies, use plugin-contained launchers, validate Windows/macOS/Linux path rules, and unblock Rust verification on a host with MSVC/linker or documented CI.

## Implications for Roadmap

### Phase 1: Protect workspace and reconcile integration history

**Rationale:** The worktree is intentionally dirty and contains the application, backend, and untracked adapter. Git safety is a dependency for every later phase.

**Delivers:** Recoverable checkpoint; local integration branch/worktree; Aman ancestry/diff audit; one documented merge or evidence-based decision not to merge; preserved Prachi/backend merge commits; integration log; baseline status/diff evidence.

**Addresses:** INT-01, INT-02, INT-06, VER-06.

**Avoids:** Destructive reset/clean, duplicated merges, accidental overwrite, and mixing conflict resolution with feature implementation.

**Research flag:** Needs a short planning-time branch audit because the current report does not establish whether Aman contains required changes.

### Phase 2: Prove the existing 28-tool harness and plugin boundary

**Rationale:** This is the highest-leverage architectural proof and should occur before adding new domain tools or Rust code.

**Delivers:** Native Codex MCP read/write proof; plugin shell with valid manifests, contained launch paths, skill instructions, dependency setup, stderr-only diagnostics, farmer identity inheritance, and `tools/list`/representative `tools/call` integration evidence.

**Addresses:** MCP-01, MCP-05/06/08, CODEX-01/02/03/05, the merge plan's first implementation checkpoint.

**Avoids:** Native Rust duplication, invalid plugin paths, hard-coded identity, protocol corruption, and confusing manifest approval policy with backend confirmation.

**Research flag:** Needs deeper phase research for the fork's exact marketplace/install path, plugin overlay shape, launcher strategy, and cross-platform Python environment. Existing parser/loader patterns are otherwise well documented.

### Phase 3: Harden backend contracts and local identity semantics

**Rationale:** Frontend and MCP correctness depend on stable, side-effect-safe REST behavior. Fixing contracts after client/tool expansion multiplies drift.

**Delivers:** Pure irrigation GET plus explicit save route if needed; stable error/request-ID/retryability envelopes; server-side idempotency for enabled writes; bounded/paginated lists; provider-unavailable contracts; upload/audio limits; local launcher identity enforcement and honest cross-farmer isolation tests; protected reference-data mutation boundary for the local deployment model.

**Addresses:** API-01/04/05/06/07/08, INT-03/04, VER-02, and the security findings H1-H4/H6.

**Avoids:** Durable writes on reads, retry duplicates, unbounded model context, spoofed resource access being mistaken for tenant security, and inconsistent UI/MCP error handling.

**Research flag:** Needs research for the chosen error schema, idempotency retention, CORS policy, reference-data roles, and whether SQLite remains acceptable for the intended local process topology. True production auth should remain a separate v2 decision unless scope changes.

### Phase 4: Close frontend contract coverage with truthful states

**Rationale:** The frontend is the visible consumer of the backend and already supplies most of the vertical slices; it needs per-source failure semantics and the missing product contracts before the harness can claim parity.

**Delivers:** Independent loading/empty/stale/unavailable/error rendering; field update/map semantics; crop catalog/guidance boundary; scheme eligibility UI; market freshness/history/MSP decisions; advisor stream/history handling; report refresh/detail decisions; explicit finance-local/stateless labels; browser smoke coverage for core slices.

**Addresses:** FRM-01–16, API-02/03, VER-01/04.

**Avoids:** Blank cards that imply healthy data, fabricated agronomy/provider output, fixture IDs, accidental finance synchronization, and “endpoint wired” being treated as “feature complete.”

**Research flag:** Standard React/API-state patterns can skip broad research. Plan-time validation is still needed for product decisions on crop guidance, scheme criteria, report semantics, and finance UX.

### Phase 5: Expand MCP coverage by safe capability class

**Rationale:** Add tools only after the backend and corresponding frontend semantics are stable, and group them by risk rather than by page count.

**Delivers:** Explicit map, field update, crop/catalog/guidance, seed/fertilizer recommendation, scheme eligibility, machinery search, advisor session/message, diagnosis text workflow, and stateless finance calculation tools. Each tool gets a task-oriented schema, bounded result, provenance, annotations, identity protection, and backend/MCP tests.

**Addresses:** MCP-02/03/06/07/08 and the missing rows in the coverage matrix.

**Avoids:** Exposing central CRUD, booking/contact claims, unsupported provider behavior, financial persistence, physical control, or model-controlled identity.

**Research flag:** Needs research for provider/tool contracts, bounded eligibility inputs, advisor session semantics, and prompt-injection evaluation. Machinery list and standard REST-to-MCP wrappers can use existing patterns.

### Phase 6: Gate media/provider capabilities and run full acceptance verification

**Rationale:** Image/audio and Codex approval behavior are external/runtime gates and cannot be proven by unit tests alone.

**Delivers:** Real MCP stdio subprocess harness; Codex plugin load/start/discovery/read/approved-write/rejection/backend-failure tests; two-farmer isolation scenarios; provider-degraded and prompt-injection scenarios; media type/size/redaction/timeout tests; frontend UAT; targeted Rust `just` verification on a provisioned host or documented CI alternative.

**Addresses:** MCP-04/05/07, CODEX-04, VER-03/04/05, and the eight acceptance scenarios in the merge plan.

**Avoids:** Treating mocked HTTP tests as MCP framing proof, treating annotations as approval enforcement, accepting the missing `link.exe` as a product result, and shipping unsupported voice/image behavior.

**Research flag:** Needs phase-specific research for Codex app-server test seams and provider/attachment transport. Rust command patterns are documented, but current Windows validation is blocked by missing MSVC `link.exe`.

### Phase ordering rationale

- Protecting the user-owned worktree and resolving branch history precedes all mutations.
- The existing 28-tool/plugin proof is intentionally narrow and gives an early architectural checkpoint without multiplying unsupported contracts.
- Backend semantics precede frontend/MCP expansion because both consumers depend on idempotency, error, identity, bounds, and provenance rules.
- Frontend parity and reference workflows precede new MCP tools so tool behavior follows the same user-visible contracts.
- Provider/media and final Codex integration are last because they require external configuration, process framing, approval lifecycle, and platform evidence.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Architecture | HIGH | Confirmed directly from current FastAPI, `agent/`, frontend, and Codex loader/connection-manager sources; merge plan agrees. |
| Backend contracts | HIGH for current behavior; MEDIUM for intended scope | OpenAPI/routes and tests were inspected, but provider/auth production semantics remain incomplete. |
| Frontend coverage | HIGH for source behavior; MEDIUM for runtime providers | Lint/build pass and API usage are verified; no browser suite or live provider run exists. |
| Testing/security | HIGH for identified gaps; MEDIUM for end-to-end conclusions | Existing tests pass, but stdio, approval, browser, prompt-injection, and Rust integration gates are absent or blocked. |
| Roadmap order | MEDIUM-HIGH | Dependencies converge across reports; Aman merge timing, plugin source ownership, and identity scope still require decisions. |

**Overall confidence:** MEDIUM-HIGH for the local MVP roadmap; LOW for any production multi-tenant or provider-quality claim.

### Decisions required during planning

- Is Aman merged before or after the thin plugin proof, and what exact evidence makes that choice safe?
- Is `codex/plugins/kisansathi/server/` the canonical adapter location, or is `agent/` temporarily/finally the plugin root?
- What exact local identity threat model is accepted for v1, and what tests/documentation prevent accidental production claims?
- Which missing capabilities are mandatory for this milestone versus explicitly deferred: crop guidance, map tool, eligibility, machinery, advisor, diagnosis, voice, finance calculator?
- Is scheme eligibility state-only, or which bounded farmer inputs are authoritative?
- What is the canonical error/request-ID/idempotency contract and retention policy?
- Does irrigation need persisted plans at all, or only explainable read advice plus irrigation events/reminders?
- What provider and attachment transport must pass before image/audio tools are enabled?
- What plugin installation/marketplace and managed Python environment will be supported across Windows, macOS, and Linux?

### Gaps to carry into roadmap/phase plans

- No `CODEX_MCP.md`-style Rust execution result beyond the missing-linker blocker; Codex targeted suites need a provisioned host.
- No browser test runner, MCP stdio subprocess harness, approval/audit implementation, or prompt-injection evaluator.
- No authenticated farmer subject, ownership checks, role model, or audit log.
- No complete backend route matrix tests for all frontend adapters or shared reference authorization.
- Provider outputs for advisor, diagnosis, and voice are intentionally unavailable in the checked-in configuration.
- Current codebase planning `TESTING.md` is stale and must not override the newly observed backend/agent test baseline.

## Sources

- [PROJECT.md](../PROJECT.md) — product boundary, constraints, key decisions, and current milestone context.
- [REQUIREMENTS.md](../REQUIREMENTS.md) — v1/v2 scope, traceability, acceptance groups, and out-of-scope decisions.
- [CODEX_MCP.md](./CODEX_MCP.md) — Python adapter, Codex MCP/plugin surfaces, packaging constraints, and launch risks.
- [BACKEND_CONTRACTS.md](./BACKEND_CONTRACTS.md) — route/tool matrix, contract defects, idempotency/provenance findings, and recommended backend order.
- [FRONTEND_COVERAGE.md](./FRONTEND_COVERAGE.md) — route coverage, integration topology, vertical slices, and UI gaps.
- [TESTING_SECURITY.md](./TESTING_SECURITY.md) — test inventory, security boundaries, verification matrix, and high-risk gaps.
- [CODEX_AI_HARNESS_MERGE_PLAN.md](../../CODEX_AI_HARNESS_MERGE_PLAN.md) — local merge sequence, target plugin layout, tool matrix, acceptance scenarios, and definition of done.

---
*Research synthesized: 2026-08-19*
*Ready for phased roadmap creation: yes, with the decisions and gates above carried forward.*
