# Testing, Security, and Evaluation Findings

**Project:** KisanSathi frontend/backend plus Codex MCP harness
**Researched:** 2026-08-19
**Confidence:** HIGH for repository evidence; MEDIUM for end-to-end and Codex integration coverage

## Executive Assessment

The application layer has a small but real automated base. Backend tests use FastAPI `TestClient` and temporary per-farmer SQLite directories; agent tests use `httpx.MockTransport` and inspect request headers, method shaping, MCP annotations, idempotency keys, error redaction, and output bounds. The current run is green: backend 11/11, agent 8/8, frontend lint, and frontend production build. The frontend has no test runner, component tests, browser tests, or coverage command.

The central security boundary is not authentication. The browser and MCP launcher choose an `X-Farmer-ID`; the backend sanitizes it and selects a SQLite file, defaulting to `demo` when absent. This proves honest two-ID storage isolation, but it does not prevent a caller from claiming another farmer ID. Reference-data CRUD routes also have no auth or role boundary. Treat this as local/demo-only until authenticated subject claims and ownership checks exist.

The agent correctly keeps farmer ID out of MCP tool schemas and marks persistent tools as non-read-only/idempotent. The example Codex config requests approval for writes, but the Python server itself only supplies metadata and instructions; it does not implement an approval state machine or audit trail. Approval enforcement therefore needs a real Codex stdio/app-server integration test, not only unit assertions on annotations.

Codex Rust provides the right testing model for the harness: temporary Codex homes, mocked Responses/auth servers, assertions on observable permission and identity behavior, capability probes for host-dependent sandbox tests, and `cargo nextest` through the repository `just` wrapper. The targeted Rust run was blocked on this Windows host because `link.exe` is unavailable; no Rust product conclusion should be drawn from that failure.

## Current Test Inventory

| Area | Location | Current coverage | Observed result |
|---|---|---|---|
| Backend farm state | `backend/tests/test_farm_state.py` | 6 tests: tenant-file isolation, alert/irrigation rule, degraded diagnosis/weather, idempotent replay and conflict | 6 passed |
| Backend reference/ingestion | `backend/tests/test_universal_data_sources.py`, `test_market_rules.py` | 5 tests: parser mapping, stable source IDs, n8n protected endpoint shape, net-realisation math | 5 passed |
| MCP backend client | `agent/tests/test_backend_client.py` | 2 tests: identity/request headers and safe error mapping | 2 passed |
| MCP tools/server | `agent/tests/test_tools.py` | 6 tests: field-derived weather, degraded state, tool exposure, no farmer ID schema, idempotency, HTTP verbs, bounded output | 6 passed |
| Frontend | `src/`, `package.json` | No unit, component, API-client, accessibility, or browser tests | Not configured |
| Codex Rust | `codex/codex-rs/**` | Extensive upstream unit/integration suites for exec, sandbox, auth, app-server, MCP, and identity | Targeted run blocked by missing Windows linker |

The existing `.planning/codebase/TESTING.md` is stale relative to the newly present backend and agent suites; it still reports no application tests. Update planning assumptions when the roadmap is created.

## Test Conventions to Preserve

### Backend

- Use `backend/pytest.ini` (`pythonpath = .`, `testpaths = tests`) and run from `backend`.
- Use `TemporaryDirectory()` for each farmer-state test and override `settings.FARM_STATE_DB_DIR` and `settings.FARM_STATE_UPLOAD_DIR`; never use the demo database for mutation tests.
- Exercise route contracts through `TestClient`, including status codes, response envelopes, validation, and state after the request.
- Add explicit negative tests for missing/forged identity, cross-farmer resource IDs, malformed GeoJSON, invalid dates/measurements, upload limits/types, and missing provider data.
- Keep reference Mongo tests isolated from live services. The current suite mostly tests pure parsers and workflow JSON, not Mongo lifecycle or route behavior.

### Agent/MCP

- Use `httpx.MockTransport` to assert exact path, verb, query, headers, idempotency key, and redacted error content.
- Build the server and inspect `tools/list`; assert names, unique schemas, annotations, and absence of `farmer_id` from all tool schemas.
- Test bounded result envelopes at the configured byte limit and preserve `source`, freshness, assumptions, warnings, and request IDs.
- Add a subprocess stdio test against a temporary FastAPI instance. Mock transport tests cannot prove MCP framing, startup, shutdown, or approval behavior.
- For writes, prove both explicit confirmation and Codex write approval are required, cancellation leaves state unchanged, and a timeout/retry creates one record.

### Codex Rust

- Prefer `just test <package-or-filter>` / `cargo nextest` from `codex/codex-rs`, with `RUST_MIN_STACK=8388608` and `NEXTEST_PROFILE=local`; use `just fmt-check` and `just clippy` for Rust quality gates.
- Follow existing test helpers: `TempDir`/temporary Codex home, `MockResponsesConfig`, `TestAppServer`, wiremock/mock HTTP servers, and explicit request/notification assertions.
- For sandbox tests, probe whether enforcement is available and skip only the host capability, while failing if a supposedly enforced policy permits a forbidden operation.
- For identity tests, assert URL scheme restrictions, absolute assertion paths, size/type limits, token response validation, token redaction in `Debug`, refresh behavior, and no cross-connection process control.

## Identity and Approval Boundaries

| Boundary | Current implementation | Security meaning | Required verification |
|---|---|---|---|
| Browser → backend | `src/api/client.js` reads local storage/env and sends `X-Farmer-ID` for farm-state calls | User-controlled selector, not identity proof; default is `demo` | Missing header must be rejected in production mode; forged header must not change authenticated subject |
| MCP launcher → backend | `KISANSATHI_FARMER_ID` is validated by regex and attached on every request; absent env fails launcher startup | Trusted local configuration only; any process able to edit config/env can switch farmer | Launch two servers and prove separate subjects; test that model/tool args cannot override the configured subject |
| Backend farm state | `get_farm_store()` chooses a sanitized SQLite path and defaults absent ID to `demo` | Honest IDs are isolated; unauthorized ID selection is possible | Authenticated subject claim must own the store; cross-ID read/write and resource-ID substitution must be denied |
| Backend reference data | Farmer/crop/disease/fertilizer/market/MSP/scheme/machinery CRUD routes lack auth/role dependencies | Any reachable caller may mutate shared catalogs | Anonymous read/write matrix; admin/ingestion role tests; disable or protect destructive routes |
| n8n ingestion | `X-Ingestion-Token`, constant-time comparison, 503 when unset | Better than public mutation, but bearer token is replayable and not scoped | Wrong/missing token, rotation, replay, rate limit, source allow-list, and run audit tests |
| MCP write tools | `_WRITE` annotation: non-read-only, non-destructive, idempotent; config sets `default_tools_approval_mode = "writes"` | Metadata/config can guide Codex approval; Python layer does not enforce user confirmation | Stdio/app-server test: preview → approval → one write; denial/cancel → zero writes; retries → one write |

## Executable Verification Matrix

Run commands from the stated directory. Status reflects this research run unless marked pending.

| ID | Risk/behavior | Command | Expected evidence | Status |
|---|---|---|---|---|
| V-01 | Backend contract and farm-state regression | `python -m pytest` in `backend` | All backend tests pass; no live Mongo required for farm-state tests | PASS: 11 passed |
| V-02 | MCP client/tool shaping and safety metadata | `python -m pytest` in `agent` | Header identity, redaction, output cap, method paths, annotations, idempotency pass | PASS: 8 passed |
| V-03 | Frontend static gate | `npm run lint` | ESLint exits 0 | PASS |
| V-04 | Frontend production gate | `npm run build` | Vite exits 0; inspect emitted bundle-size warning | PASS, warning: JS chunk >500 kB |
| V-05 | Honest two-farmer SQLite isolation | `python -m pytest backend/tests/test_farm_state.py -k farmer_databases_are_isolated` | Farmer A data appears for A and empty for B | PASS, but only honest-header isolation |
| V-06 | Forged identity / missing identity rejection | Add an API security test, then run `python -m pytest backend/tests -k 'identity or ownership or auth'` | Missing/forged subject is 401/403; resource IDs cannot cross subjects | GAP: no such tests or enforcement |
| V-07 | Shared reference-data authorization | Add route matrix test, then run `python -m pytest backend/tests -k 'reference and (auth or role)'` | Anonymous and farmer roles cannot create/update/delete shared catalogs; ingestion/admin can | GAP: no auth/role dependency |
| V-08 | Ingestion token boundary | `python -m pytest backend/tests -k ingestion` | Missing/unset token → 503; wrong token → 401; correct token reaches DB guard; replay policy explicit | PARTIAL: workflow header shape only; endpoint auth paths untested |
| V-09 | MCP schema contract | `python -m pytest agent/tests/test_tools.py -k server_exposes` | All 28 registered tools have unique valid schemas; no farmer ID; read/write annotations match policy | PARTIAL: current test checks representative tools only |
| V-10 | MCP stdio discovery/call | Start backend, install `agent` editable, launch `python -m kisansathi_agent` with `KISANSATHI_FARMER_ID=demo`, then run a JSON-RPC/MCP client against stdio | `tools/list` and `tools/call` succeed; backend state changes only after approved write | GAP: no stdio harness or approval assertion exists |
| V-11 | Cross-process farmer isolation | Launch two MCP processes with distinct `KISANSATHI_FARMER_ID` values against the same backend; call list/create/read flows for each | No fields, reminders, reports, soil tests, or finance data cross the configured subjects | GAP: plan requirement only; no integration test |
| V-12 | Grounding and prompt injection | Seed market/scheme/provider fixtures with instruction-like text; run MCP tool calls and scenario evaluator | Data is returned as untrusted content; tool policy and approval state do not change | GAP: no safety/evaluation harness |
| V-13 | Codex Rust routine suite | From `codex`, run `just fmt-check`; from `codex/codex-rs`, run `cargo nextest run --no-fail-fast -p codex-workload-identity` or repository `just test -p codex-workload-identity` | Formatting and identity tests pass on a provisioned Rust/MSVC host | BLOCKED HERE: `link.exe` missing |
| V-14 | Codex approval policy | From `codex/codex-rs`, run `cargo nextest run --no-fail-fast -p codex-exec --test all -E 'test(approval_policy)'` | `--approve-for-me` preserves on-request/workspace-write; bypass explicitly shows approval never | NOT RUN: same linker/toolchain blocker |
| V-15 | Codex sandbox enforcement | From `codex/codex-rs`, run `cargo nextest run --no-fail-fast -p codex-exec --test all -E 'test(sandbox)'` | Forbidden writes fail; allowed policy paths work; unsupported hosts skip only with a capability message | NOT RUN: same blocker; host-dependent |
| V-16 | Codex app-server identity/approval lifecycle | From `codex/codex-rs`, run `cargo nextest run --no-fail-fast -p codex-app-server --test all -E 'test(approval) or test(auth)'` | Auth status omits tokens when requested; approval/permission RPC lifecycle is explicit and scoped | NOT RUN: exact package test target should be confirmed with `cargo nextest list` |

## High-Risk Gaps

### H1 — No authenticated farmer identity or authorization

`X-Farmer-ID` is accepted directly and absent headers become `demo`. The backend has no authentication middleware, subject claim, ownership check, role model, or audit log. Existing isolation tests prove file separation only after a caller honestly chooses two IDs. This is a release blocker for multi-user or internet-exposed deployment.

Prevention: introduce an authenticated subject dependency; derive the farmer key from verified claims, not a request header; enforce ownership on every farm-state resource ID; separate farmer, admin, and ingestion roles; reject missing identity rather than defaulting to `demo`; add immutable security/audit events. Test anonymous, forged-header, cross-resource, and role-based cases before enabling deployment.

### H2 — Persistent writes are not independently approval-enforced

The agent descriptions say “confirmed” and annotations mark writes, while the example config asks Codex to approve writes. There is no backend confirmation nonce/record, approval receipt, or audit trail. A direct HTTP caller can invoke the same writes without Codex, and a future client could ignore metadata.

Prevention: keep Codex approval as a client-layer gate, but add a backend policy boundary for authenticated mutation callers, explicit operation intent/confirmation where risk requires it, and audit records containing subject, tool, request ID, approval decision, payload hash, and outcome. Prove denial/cancel/timeout/retry behavior end to end.

### H3 — Shared reference-data mutation is broadly exposed

Reference routers expose POST/PUT/DELETE for farmer, crop, disease, fertilizer, MSP, schemes, market prices, seeds, and machinery without role protection. Ingestion is token-protected, but other mutation paths remain reachable if the service is reachable.

Prevention: make reference data read-only to farmer clients; protect admin/manual mutation and ingestion with separate least-privilege credentials; add route-level authorization tests and disable destructive routes unless required.

### H4 — CORS is permissive and credentialed

FastAPI config uses `allow_origins=["*"]`, `allow_credentials=True`, and wildcard methods/headers. This is unsuitable once authenticated browser credentials are introduced and lacks a CORS integration test.

Prevention: deployment-specific origin allow-list, minimal methods/headers, explicit credential policy, and tests for allowed origin, disallowed origin, preflight, and credential behavior.

### H5 — No end-to-end safety/evaluation harness

The merge plans specify eight user scenarios, prompt-injection resistance, grounded/provenance-preserving answers, provider-unavailable behavior, approval, and duplicate mutation after timeout. None has a committed UAT/evaluation runner. There is no frontend browser smoke suite and no MCP stdio integration harness.

Prevention: build a deterministic local stack test with temporary SQLite, mocked provider/Mongo responses, a real MCP stdio process, and a Codex/app-server test client. Store scenario fixtures and assert tool selection, approval transitions, final state, source/freshness, degraded status, and no cross-farmer leakage.

### H6 — Input, abuse, and operational security coverage is incomplete

Upload validation and max bytes exist, but tests do not cover invalid MIME/content, oversized multipart bodies, path handling, or stored-file privacy. There are no rate-limit, replay, pagination, request-size, dependency-vulnerability, or audit-log checks. Backend pytest also reports a Starlette/httpx deprecation warning and agent pytest reports an unset `pytest-asyncio` loop-scope warning.

Prevention: add boundary/property tests, explicit limits, dependency/security scanning in CI, warning cleanup, and observability tests that ensure secrets and user content are not logged.

## Recommended Roadmap Order

1. Establish a single application test entry point and CI gates for backend, agent, frontend lint/build, dependency scanning, and warning policy.
2. Replace header-selected identity with authenticated claims and add ownership/role tests before exposing the service beyond local demo use.
3. Add MCP stdio integration and Codex approval lifecycle tests using temporary homes and mocked Responses/provider servers.
4. Add security-focused contract tests: CORS, ingestion replay/rotation, uploads, request limits, redaction, audit records, and cross-farmer resource substitution.
5. Add deterministic scenario evaluation/UAT for the eight documented flows, including prompt injection, provider degradation, grounded citations/freshness, approval denial, and timeout retry.
6. Run targeted Codex Rust suites through `just test` on a provisioned Windows MSVC or Linux/macOS CI runner; do not treat the current linker failure as a passing or failing product result.

## Sources Inspected

- `backend/tests/test_farm_state.py`, `backend/tests/test_market_rules.py`, `backend/tests/test_universal_data_sources.py`
- `backend/app/main.py`, `backend/app/farm_state/dependencies.py`, `backend/app/routers/ingestion.py`, `backend/app/core/config.py`
- `agent/tests/test_backend_client.py`, `agent/tests/test_tools.py`, `agent/src/kisansathi_agent/server.py`, `agent/src/kisansathi_agent/backend_client.py`
- `src/api/client.js`, `package.json`, `backend/pytest.ini`, `agent/pyproject.toml`
- `agent/config/codex.mcp.example.toml`, `backend/Decisions.md`, `backend/Flow.md`
- `MCP_AGENT_IMPLEMENTATION_PLAN.md`, `CODEX_AI_HARNESS_MERGE_PLAN.md`
- Codex conventions: `codex/justfile`, `codex/codex-rs/exec/tests/suite/approval_policy.rs`, `sandbox.rs`, `codex/codex-rs/app-server/tests/suite/v2/request_permissions.rs`, `command_exec.rs`, `auth.rs`, and `workload-identity/src/workload_identity_tests.rs`
- Existing planning notes: `.planning/codebase/TESTING.md`, `.planning/codebase/CONCERNS.md` (noting that TESTING.md predates the current suites)
