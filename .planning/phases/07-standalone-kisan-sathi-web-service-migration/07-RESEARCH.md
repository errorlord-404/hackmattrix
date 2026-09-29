# Phase 7: Standalone Kisan Sathi Web Migration - Research

**Researched:** 2026-09-17  
**Domain:** Provider-neutral LLM orchestration, resumable web streaming, tenant security, hybrid browser/server vision, standalone deployment  
**Confidence:** HIGH for migration contracts and boundaries; MEDIUM for new package/version choices

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- The current application remains untouched during migration implementation;
  Phase 7 writes application code only under `Kisan Sathi Web/`.
- Do not fork or embed the full Codex repository. Build a small web harness
  around the application's actual conversation, tool, approval, and streaming
  requirements.
- The harness is LLM-provider neutral. Provider-specific SDKs and wire formats
  live behind adapters and capability declarations.
- Provider credentials and model calls live on the server. API keys never ship
  to browser JavaScript or appear in tool arguments, logs, or conversation
  records.
- Existing FastAPI domain behavior and KisanSathi tool contracts are the
  migration baseline. Domain logic remains outside the LLM orchestration layer.
- Preserve the complete required tool surface in a canonical registry, but
  expose a small workflow-specific allowlist to the LLM on each turn.
- Persistent actions retain authenticated authorization, explicit confirmation,
  idempotency, auditability, and authoritative backend responses regardless of
  provider behavior.
- Replace Electron IPC and local `codex app-server` spawning with a web protocol
  supporting streaming, reconnect/resume, tool progress, approvals,
  clarifications, cancellation, images, and voice.
- Replace launcher-owned `X-Farmer-ID` with authenticated session claims and
  server-derived tenant/farmer scope.
- Computer vision uses a hybrid design: optional browser screening in a Web
  Worker (WASM baseline, WebGPU enhancement) plus a server fallback and
  authoritative persistence/review path.
- Browser CV output is a candidate unless it satisfies the same approved
  release-manifest, checksum, preprocessing, quality, confidence, margin, OOD,
  crop-confirmation, and limitation contract as the server.
- No autonomous machinery, payments, purchases, sales, subsidy submission, or
  pesticide/fertilizer action is added by this migration.

### the agent's Discretion

No explicit discretion section is present in `07-CONTEXT.md`.

### Deferred Ideas (OUT OF SCOPE)

No explicit deferred-ideas section is present in `07-CONTEXT.md`.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| WEB-01..10 | Standalone authenticated web application, API/harness behavior, streaming, tools, media, and deployment. [VERIFIED: `07-PATTERNS.md`] | Adapter, protocol, auth, deployment, and validation contracts below. |
| CVWEB-01..02 | Hybrid browser/server crop-health inference with safety parity. [VERIFIED: `07-PATTERNS.md`] | Browser-vision architecture and release-gate parity below. |
| MIG-01..02 | Selective standalone migration with manifest and no parent runtime dependency. [VERIFIED: `07-PATTERNS.md`] | Runtime-state inventory, standalone topology, and migration waves below. |
| WEBVER-01..02 | Cross-system parity, security, browser, failure, load, and deployment verification. [VERIFIED: `07-PATTERNS.md`] | Validation architecture and phase gates below. |
</phase_requirements>

## Summary

Implement the standalone system as three runtime boundaries: browser, harness, and domain API. The browser owns presentation and optional local screening; the harness owns conversation state, provider adaptation, stream replay, tool selection, approvals, and audit; the API owns domain validation, tenant authorization, idempotency, persistence, and authoritative results. [VERIFIED: `07-CONTEXT.md`, `07-PATTERNS.md`, targeted source inspection]

Use same-origin authenticated HTTP commands plus server-sent events (SSE) for the main conversation transport. Every durable event must carry a stable event ID and per-session monotonic sequence; reconnect resumes after the last applied cursor and duplicates are ignored. Native EventSource reconnect behavior and `Last-Event-ID` support this shape, but retention, authorization, ordering, and deduplication remain application responsibilities. [CITED: https://html.spec.whatwg.org/multipage/server-sent-events.html]

**Primary recommendation:** Freeze contracts and golden fixtures first, then prove one authenticated read and one confirmed idempotent write through a fake provider before adding real provider adapters, media, browser vision, or deployment. [VERIFIED: `07-PATTERNS.md`]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Conversation UI and media capture | Browser / Client | Harness | UI state stays client-side; privileged work stays server-side. [VERIFIED: `AIConversationContext.jsx`] |
| Session, turns, provider calls, replay | Harness service | Database / Storage | Provider-neutral orchestration and durable event ordering belong outside provider adapters. [VERIFIED: `07-CONTEXT.md`, `codex-harness.cjs`] |
| Tool authorization and execution | Harness policy + API | Tool registry | Harness gates calls; API re-authorizes and returns authoritative state. [VERIFIED: `07-CONTEXT.md`, `server.py`] |
| Tenant/farmer scope | API / Backend | Harness | Scope derives from verified claims and is propagated internally, never model/browser input. [VERIFIED: `07-CONTEXT.md`] |
| Browser crop screening | Browser Web Worker | API fallback | Local output is a candidate; API owns release validation and persistence. [VERIFIED: `07-CONTEXT.md`, `tflite_crop_health.py`] |
| Static assets and model artifacts | CDN / Static | Browser worker | Versioned immutable files need checksum validation and cache-safe URLs. [CITED: https://onnxruntime.ai/docs/tutorials/web/deploy.html] |
| Domain records and audit | API / Backend | Database / Storage | Domain rules, idempotency, ownership, and authoritative responses remain server-side. [VERIFIED: `07-PATTERNS.md`] |

## Standard Stack

### Core

| Component | Version policy | Purpose | Recommendation |
|---|---|---|---|
| React web app | Preserve existing compatible version, then regenerate standalone lockfile. [VERIFIED: `07-PATTERNS.md`] | Browser UI/state | Adapt `AIConversationContext` behind a typed `harnessClient`; do not expose SDK objects. |
| FastAPI services | Preserve existing compatible version and Python 3.12 support. [VERIFIED: targeted environment and `07-PATTERNS.md`] | API and harness HTTP boundaries | Separate `services/api` from `services/harness`; share schemas, not domain implementation. |
| SSE + ordinary HTTP | Browser standard | Downstream events plus upstream commands | SSE for replayable one-way stream; POST for turns, approval, clarification, cancel, voice, and uploads. [CITED: https://html.spec.whatwg.org/multipage/server-sent-events.html] |
| ONNX Runtime Web | Pin only after human verification; registry latest observed `1.30.0`. [VERIFIED: npm registry] | Worker inference | Use `wasm` baseline and `webgpu` enhancement with explicit fallback. [CITED: https://onnxruntime.ai/docs/tutorials/web/env-flags-and-session-options.html] |
| PyJWT | Pin only after human verification; registry latest observed `2.14.0`, environment has `2.13.0`. [VERIFIED: PyPI registry] | Test/dev JWT issue/verify or production verifier building block | Use verified signature, issuer, audience, expiry, and subject claims; production IdP remains an extension point. [CITED: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/] |
| Docker Compose | Host Docker `29.7.2`. [VERIFIED: environment probe] | Reproducible standalone stack | Health-gate dependencies and mount durable state/secrets. [CITED: https://docs.docker.com/compose/how-tos/startup-order/] |

### Do Not Add Yet

Do not add Redis, a WebSocket framework, a provider router package, or a separate workflow engine in the first slice. The existing datastore can hold sessions/events initially, and HTTP+SSE covers the required asymmetric interaction model. [ASSUMED]

## Package Legitimacy Audit

| Package | Registry | Observed version | Source Repo | Verdict | Disposition |
|---|---|---:|---|---|---|
| `onnxruntime-web` | npm | 1.30.0 | `github.com/Microsoft/onnxruntime` | SUS: seam flagged newest release as too new; no postinstall script observed. [VERIFIED: npm registry] | Keep recommendation, but planner must add `checkpoint:human-verify` before pin/install. |
| `PyJWT` | PyPI | 2.14.0 | `github.com/jpadilla/pyjwt` | SUS: seam flagged newest release as too new and download signal unavailable. [VERIFIED: PyPI registry] | Prefer already-installed 2.13.0 for development; planner must add `checkpoint:human-verify` before changing lock. |

**Packages removed due to SLOP verdict:** none. [VERIFIED: package-legitimacy seam]  
**Packages flagged as suspicious [SUS]:** `onnxruntime-web`, `PyJWT`; these are official-project packages, but the mandatory gate still requires human verification because the latest releases are very recent. [VERIFIED: package-legitimacy seam; official ONNX Runtime and FastAPI docs]

## Provider-Neutral LLM Adapter Contract

The adapter boundary must be smaller than any provider SDK. The orchestrator supplies normalized messages, a turn-scoped tool allowlist, and required capabilities; the adapter emits only normalized provider events. [VERIFIED: `07-CONTEXT.md`, `07-PATTERNS.md`]

```python
# Source: derived from codex-harness.cjs behavior and locked Phase 7 boundaries.
class ProviderAdapter(Protocol):
    id: str
    capabilities: ProviderCapabilities
    async def stream_turn(self, request: ProviderTurnRequest) -> AsyncIterator[ProviderEvent]: ...
    async def cancel(self, provider_turn_id: str) -> None: ...

class ProviderCapabilities(BaseModel):
    text: bool
    images: bool
    tools: bool
    structured_output: bool
    streaming: bool
    cancellation: bool
    max_input_bytes: int
    max_output_tokens: int | None
```

`ProviderTurnRequest` should contain normalized role/content parts, selected model alias, bounded tool schemas, response constraints, and trace IDs. It must not contain tenant selectors, API keys, raw cookies, or authorization headers. [VERIFIED: `07-CONTEXT.md`; ASSUMED contract field names]

Normalize adapter output to `text_delta`, `message_completed`, `tool_call_requested`, `provider_usage`, `provider_warning`, `provider_error`, and `provider_completed`. Reject malformed tool JSON before policy evaluation. Never persist raw SDK objects or raw provider response bodies. [VERIFIED: `codex-harness.cjs`, `07-PATTERNS.md`]

Capability negotiation happens before provider invocation. Missing mandatory capabilities fail with a typed non-secret error; optional image capability may select the documented server diagnosis fallback. Silent downgrade is forbidden. [VERIFIED: `07-CONTEXT.md`, `AIConversationContext.jsx`, `07-PATTERNS.md`]

## Web Streaming and Resume Protocol

### Command endpoints

| Endpoint | Purpose | Required invariants |
|---|---|---|
| `POST /v1/sessions` | Start session | Authenticated actor scope; returns opaque session ID and capabilities. [ASSUMED path; VERIFIED behavior from `codex-harness.cjs`] |
| `GET /v1/sessions/{id}/events?after={sequence}` | SSE stream/replay | Actor owns session; ordered replay; heartbeat; bounded retention response. [ASSUMED path; CITED: HTML SSE standard] |
| `POST /v1/sessions/{id}/turns` | Send text/image reference | Client message ID is idempotent; one active turn per session. [VERIFIED: `codex-harness.cjs`] |
| `POST /v1/sessions/{id}/turns/{turn}/cancel` | Cancel | Terminal event is durable; duplicate cancel is harmless. [VERIFIED: `codex-harness.cjs`; ASSUMED endpoint] |
| `POST /v1/sessions/{id}/requests/{request}/resolve` | Approval or clarification | Exact request binding, actor match, one terminal resolution, expiry check. [VERIFIED: `AIConversationContext.jsx`, `07-PATTERNS.md`] |

### Event envelope

```json
{
  "version": 1,
  "event_id": "uuid",
  "session_id": "opaque",
  "turn_id": "opaque-or-null",
  "sequence": 42,
  "occurred_at": "RFC3339 UTC",
  "kind": "agent.message.delta",
  "payload": {}
}
```

Preserve the desktop behavior set: ready/unavailable/diagnostic, message delta/completion, tool progress/completion/failure, approval, clarification, turn completion, and session status. [VERIFIED: `codex-harness.cjs:259-269`]

Use a unique `(session_id, sequence)` index and stable `event_id`; append before publish. The browser stores only opaque session ID and last applied sequence, drops already-applied events, reconstructs drafts by stable message item ID, and requests replay after reconnect. [ASSUMED implementation; VERIFIED reducer behavior from `AIConversationContext.jsx`]

If the cursor is older than retention, return a typed `resume_window_expired` response and force a state snapshot/reload; never silently continue from the live tail. [ASSUMED]

## Server Secrets, Authentication, and Tenant Scope

Create one immutable `ActorScope(sub, tenant_id, farmer_id, roles, session_id)` from verified server-side claims. No route, upload field, query parameter, tool argument, model output, or `X-Farmer-ID` header may override it. [VERIFIED: `07-CONTEXT.md`, `07-PATTERNS.md`]

Centralize token verification and validate signature, allowed algorithm, issuer, audience, expiry/not-before, and required subject/tenant/farmer claims. FastAPI officially documents OAuth2 bearer/JWT dependencies, while production identity-provider selection remains out of this bounded phase. [CITED: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/; VERIFIED: `07-PATTERNS.md`]

For same-origin browser deployment, prefer an `HttpOnly`, `Secure`, appropriately scoped `SameSite` session cookie plus CSRF protection on unsafe methods; if bearer tokens are used, keep them out of local storage and use a fetch-based SSE client capable of setting authorization headers. [ASSUMED]

Harness-to-API calls use a service-authenticated, short-lived signed actor context containing the original actor and trace IDs. API routes still perform object-level tenant predicates and never trust a model-supplied ID as proof of ownership. [VERIFIED: `07-PATTERNS.md`; ASSUMED signing mechanism]

Secrets load only from environment/secret mounts at process startup. Redact known secret values and authorization-like keys before logs, event persistence, tool audit, or provider error mapping. Startup fails for required secrets; optional providers expose `unavailable` capability state. [VERIFIED: `07-CONTEXT.md`, `07-PATTERNS.md`]

## Tool Policy and Approval Parity

Preserve the canonical 78-tool inventory and its 56 read/22 write annotation baseline for parity tests. The current registry deliberately excludes farmer identity from tool arguments and marks all tools non-destructive/idempotent. [VERIFIED: `server.py`, `07-PATTERNS.md`]

Add policy metadata without changing canonical names/schemas: `workflow_tags`, `required_capabilities`, `effect_class`, `requires_confirmation`, `risk_level`, and `result_schema_version`. [ASSUMED metadata names]

Use `effect_class` to distinguish pure reads, external compute, authoritative persistence, and prohibited action. The existing `_WRITE` annotation over-classifies transcription/translation/synthesis/diagnosis as writes; retain parity metadata but require human confirmation specifically for persistent domain changes, not merely paid/provider computation. [VERIFIED: `server.py`, `07-PATTERNS.md`]

Approval state machine: `proposed -> awaiting_confirmation -> accepted|declined|expired|cancelled -> executing -> succeeded|failed`. Only the orchestrator transitions to executing; the API rechecks actor scope and idempotency. Duplicate acceptance returns the original authoritative result and never repeats the effect. [ASSUMED state names; VERIFIED invariants from `07-CONTEXT.md`]

The LLM receives only the smallest workflow-specific allowlist. Unknown tools, out-of-allowlist calls, schema-invalid calls, persistent calls without accepted approval, and prohibited machinery/payment/purchase/sale/subsidy/chemical actions fail closed and are audited. [VERIFIED: `07-CONTEXT.md`, `server.py`]

## Hybrid ONNX Browser/Server Vision

Run browser inference in a dedicated Web Worker. Attempt `webgpu` only when supported, with `wasm` as the guaranteed baseline/fallback; ONNX Runtime Web officially supports ordered execution-provider configuration and notes that GPU providers support only subsets of operators. [CITED: https://onnxruntime.ai/docs/tutorials/web/env-flags-and-session-options.html; https://onnxruntime.ai/docs/tutorials/web/]

Serve the exact ORT WASM/JSEP files expected by the pinned package or set `ort.env.wasm.wasmPaths`; missing/misplaced binaries prevent initialization. [CITED: https://onnxruntime.ai/docs/tutorials/web/deploy.html]

The worker accepts bytes plus a server-issued release descriptor, verifies model/labels hashes, derives resize/color/normalization/top-k rules from that descriptor, performs quality checks, and returns a non-authoritative candidate with runtime, model, release, artifact hash, candidates, thresholds, limitations, and fallback reason. [VERIFIED: `tflite_crop_health.py`; ASSUMED browser descriptor transport]

Port these fail-closed gates exactly: minimum dimensions/exposure/detail, explicit crop confirmation, supported crop, separate top score and top1-top2 margin, manifest status, model/labels SHA-256, independent field test, unknown/OOD test, agronomist review, and limitations. [VERIFIED: `tflite_crop_health.py`]

Browser output becomes authoritative only after API ownership checks, upload checksum binding, release identity revalidation, idempotent persistence, and server response. Any worker, model, WebGPU, checksum, preprocessing, or gate failure falls back to server inference or `needs_expert_review`; it never becomes a completed diagnosis. [VERIFIED: `07-CONTEXT.md`, `AIConversationContext.jsx`, `tflite_crop_health.py`]

## Standalone Deployment

Deploy behind one same-origin reverse proxy with `/` -> web, `/api/` -> domain API, and `/harness/` -> harness. This simplifies cookie scope, CORS, and SSE routing. [ASSUMED]

Compose services should include proxy/web, API, harness, and the existing datastore, each with liveness/readiness checks, named persistent volumes, restart policy, resource limits, and explicit network boundaries. Compose can gate dependent startup on `service_healthy`; container writable layers are not durable storage. [CITED: https://docs.docker.com/compose/how-tos/startup-order/; https://docs.docker.com/compose/gettingstarted/]

Build context must be `Kisan Sathi Web/`; CI must reject parent-relative imports, symlinks, model/config paths, and undeclared copied files. Produce a migration manifest with `copy|adapt|replace|exclude`, source hash, target path, and rationale. [VERIFIED: `07-CONTEXT.md`, `07-PATTERNS.md`]

Readiness requires datastore connectivity, valid schema/migrations, writable required volumes, valid required secret references, and approved model manifests. Optional provider outage is degraded readiness only when another declared path can satisfy the request. [ASSUMED readiness split; VERIFIED fail-closed model policy]

## Runtime State Inventory

| Category | Items Found | Action Required |
|---|---|---|
| Stored data | Existing local DBs, uploads, and generated data are explicitly excluded from copying; durable domain data may still need export/import. [VERIFIED: `07-CONTEXT.md`, `07-PATTERNS.md`] | Add an explicit data migration/seed decision and rehearsal; do not copy runtime directories. |
| Live service config | Provider keys/config and external workflow state were not inspectable in the bounded source set. [VERIFIED: bounded inspection scope] | Pre-cutover inventory; migrate only documented server-side configuration and rotate exposed/legacy credentials. |
| OS-registered state | Desktop Codex spawning is being removed; no OS registration inventory was provided. [VERIFIED: `codex-harness.cjs`; bounded scope] | Verify and retire obsolete launchers/tasks after rollback window; do not make them a web dependency. |
| Secrets/env vars | `CODEX_BINARY`, `KISANSATHI_*`, provider keys, and farmer launcher identity are legacy concerns. [VERIFIED: `codex-harness.cjs`, `07-CONTEXT.md`] | Map to server secret names; remove farmer identity env injection; document rotation and startup validation. |
| Build artifacts/packages | `.git`, `node_modules`, caches, builds, downloaded runtimes, models not approved for release, and local databases are excluded. [VERIFIED: `07-CONTEXT.md`, `07-PATTERNS.md`] | Rebuild from clean locks/images and checksum every deployable model/runtime artifact. |

## Common Pitfalls

| Pitfall | Failure | Prevention |
|---|---|---|
| Adapter leakage | Provider SDK types infect events, persistence, and tools. [ASSUMED] | Contract tests assert only normalized DTOs cross the adapter boundary. |
| Replay after publish | Crash loses an event already seen by a client. [ASSUMED] | Persist event and sequence atomically before fan-out. |
| Duplicate side effects | Reconnect/retry repeats an accepted write. [VERIFIED: required verification] | Bind approval, actor, canonical payload hash, and idempotency key; replay authoritative response. |
| Scope confused with selection | Browser/model field ID is treated as authorization. [VERIFIED: migration baseline risk] | Claim-scoped query plus object ownership check on every resource. |
| SSE proxy buffering | Deltas arrive in large delayed bursts. [ASSUMED] | Disable buffering/compression where needed, emit heartbeats, and test through the real proxy. |
| Secret-bearing errors | Raw provider body/header reaches logs or browser. [VERIFIED: locked constraint] | Typed bounded errors and redaction at adapter boundary. |
| Browser/server CV drift | Same label but different preprocessing/gates. [VERIFIED: `tflite_crop_health.py`, locked constraint] | One release descriptor, cross-runtime golden tensors, tolerance tests, checksum binding. |
| WebGPU assumed universal | Unsupported browser/operator breaks diagnosis. [CITED: https://onnxruntime.ai/docs/tutorials/web/] | WASM baseline, feature detection, worker timeout, server fallback. |
| Premature parallelism | Teams cross-edit contracts and create incompatible clients. [VERIFIED: `07-CONTEXT.md`] | Freeze contracts/fixtures and assign disjoint path ownership before fan-out. |

## Recommended Waves

1. **Wave 0 — Inventory and frozen contracts:** scaffold standalone tree; migration manifest; OpenAPI/tool/event/tool-result/CV fixtures; fake provider; test skeleton. [VERIFIED: `07-PATTERNS.md`]
2. **Wave 1 — Authenticated walking slice:** test/dev issuer, immutable actor scope, one read tool, API call, persisted SSE events, browser rendering, reconnect. [VERIFIED: `07-PATTERNS.md`]
3. **Wave 2 — Confirmed write:** approval state machine, deterministic idempotency, audit, authoritative response, UI refresh, cross-tenant denial. [VERIFIED: `07-CONTEXT.md`]
4. **Wave 3 — Parallel migration lanes:** web UI, domain API, full tool registry/policy, and harness core on frozen contracts with disjoint paths. [VERIFIED: `07-PATTERNS.md`]
5. **Wave 4 — Provider adapters:** capability negotiation, normalized streaming/tool calls, cancellation, timeout/rate-limit handling, redaction; fake transport tests before live credentials. [VERIFIED: `07-PATTERNS.md`]
6. **Wave 5 — Media and hybrid vision:** voice/image transport, worker WASM, optional WebGPU, release parity, server fallback, authoritative persistence. [VERIFIED: `07-CONTEXT.md`]
7. **Wave 6 — Deployment and phase gate:** clean-checkout Compose, health/readiness, persistent restart, browser matrix, load/failure tests, rollback rehearsal, parity report. [VERIFIED: `07-CONTEXT.md`, `07-PATTERNS.md`]

## Validation Architecture

| Layer | Fast check | Phase gate |
|---|---|---|
| Python API/harness | Focused `pytest` contract/security module under 30 seconds. [ASSUMED command structure] | Full API/harness suites plus coverage of auth, replay, approval, idempotency, and redaction. |
| Web/contracts | Existing compatible JS unit runner against reducer and generated contracts. [ASSUMED runner; bounded scope did not inspect package scripts] | Browser matrix for Chromium, Firefox, WebKit. [VERIFIED: `07-CONTEXT.md`] |
| Vision | Golden preprocessing/candidate fixtures in worker and server. [VERIFIED: `07-PATTERNS.md`] | WASM/WebGPU tolerance, fallback, checksum, and every fail-closed state. |
| Deployment | Compose config/build and service health smoke. [CITED: Docker Compose docs] | Clean checkout, documented env only, restart persistence, rollback. [VERIFIED: `07-CONTEXT.md`] |

### Required test map

| Requirement group | Automated evidence |
|---|---|
| WEB | Provider normalization, golden event stream, reconnect after every event boundary, tool allowlist, approval/cancel, voice/image fallback. [VERIFIED: `07-CONTEXT.md`] |
| CVWEB | Manifest/checksum/preprocessing parity, quality/score/margin/OOD/crop gates, WASM baseline, WebGPU enhancement, server fallback. [VERIFIED: `tflite_crop_health.py`, `07-CONTEXT.md`] |
| MIG | Migration manifest completeness and a runtime import/path scan proving no parent dependency. [VERIFIED: `07-CONTEXT.md`] |
| WEBVER | Cross-tenant matrix, secret scan, concurrent streams, slow consumer/backpressure, provider failure/rate limit, deployment and rollback evidence. [VERIFIED: `07-CONTEXT.md`] |

### Wave 0 gaps

- Create shared JSON Schema/OpenAPI fixtures and a fake deterministic provider before application migration. [VERIFIED: `07-PATTERNS.md`]
- Create a stream test harness that can disconnect after each sequence and replay duplicates. [VERIFIED: required verification]
- Add package-human-verification checkpoints before installing the two SUS-version packages. [VERIFIED: package-legitimacy seam]
- Resolve exact JS test runner commands from the standalone lockfile during scaffold because package scripts were outside this bounded inspection. [ASSUMED]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | yes | Central JWT/session verification, expiry, issuer/audience, secure transport. [CITED: FastAPI security docs] |
| V3 Session Management | yes | Opaque session IDs, actor binding, expiry, cancellation, replay authorization. [ASSUMED] |
| V4 Access Control | yes | Immutable actor scope plus object-level tenant predicates on every resource. [VERIFIED: `07-CONTEXT.md`] |
| V5 Input Validation | yes | Pydantic/JSON Schema, upload MIME+magic/size checks, normalized tool schemas. [VERIFIED: `07-PATTERNS.md`] |
| V6 Cryptography | yes | Standard JWT/signature and SHA-256 artifact verification; never custom crypto. [VERIFIED: `tflite_crop_health.py`; CITED: FastAPI JWT docs] |
| V7 Error/Logging | yes | Typed bounded errors, correlation IDs, audit, centralized secret redaction. [VERIFIED: `07-PATTERNS.md`] |
| V12 Files/Resources | yes | Private uploads, generated IDs, no client filesystem paths, size/type/checksum enforcement. [VERIFIED: `07-PATTERNS.md`] |
| V13 API/Web Services | yes | Authenticated commands/streams, schema versions, idempotency, rate/size limits. [VERIFIED: `07-CONTEXT.md`] |

### Threats and mitigations

| Threat | STRIDE | Mitigation |
|---|---|---|
| Forged farmer/tenant scope | Spoofing/Elevation | Verified claims; ignore/reject `X-Farmer-ID`; object ownership predicates. [VERIFIED: locked decision] |
| Cross-session stream/approval access | Information Disclosure/Elevation | Actor-bind every session, cursor, and request resolution. [VERIFIED: required verification] |
| Duplicate write on replay | Tampering | Approval binding plus scoped idempotency and authoritative response replay. [VERIFIED: locked decision] |
| Tool-call prompt injection | Elevation/Tampering | Turn allowlist, schema validation, policy engine, explicit confirmation, API re-authorization. [VERIFIED: locked decision] |
| Secret leakage | Information Disclosure | Server-only secrets, adapter redaction, no raw provider errors/events. [VERIFIED: locked decision] |
| Stream/resource exhaustion | Denial of Service | Per-actor limits, bounded event retention/buffers, slow-consumer policy, upload/token limits, cancellation. [ASSUMED] |
| Model/artifact substitution | Tampering | Operator-mounted manifest plus exact model/labels checksum and release gates. [VERIFIED: `tflite_crop_health.py`] |

## Assumptions Log

| # | Claim | Risk if Wrong |
|---|---|---|
| A1 | HTTP commands plus SSE are sufficient; bidirectional WebSocket transport is unnecessary for v1. | Rework transport if provider audio must be truly real-time/full duplex. |
| A2 | Existing datastore can persist sessions/events without adding Redis. | Load/backpressure design may need a broker after measurement. |
| A3 | Same-origin secure-cookie deployment is acceptable. | Bearer-only IdP may require fetch-streaming and different CSRF/storage controls. |
| A4 | Exact endpoint, metadata, and approval-state names may be selected during contract freeze. | Generated clients/tests must follow the final schema. |
| A5 | Existing JS test runner can be reused. | Wave 0 must select/configure a runner if none survives the standalone copy. |

## Open Questions (RESOLVED)

1. **Production identity provider — RESOLVED:** Implement standards-based OIDC Authorization Code with PKCE. The API owns login/callback/logout/session endpoints and issues a short-lived `HttpOnly`, `Secure`, `SameSite=Lax` signed session cookie. API and harness independently verify the cookie through a shared standalone auth package. Production requires configured issuer discovery/JWKS, audience, client ID, redirect URI, and server-side client secret; the test issuer is development/test-only and production startup fails closed without OIDC configuration.
2. **Replay retention — RESOLVED:** Retain each session for 24 hours subject to earlier eviction at 10,000 events or 10 MiB, whichever is reached first. Persist a compact state snapshot before eviction and return `resume_window_expired` with the snapshot version when the requested cursor is unavailable.
3. **Voice scope — RESOLVED:** Preserve current record-blob → transcribe/translate → text-turn behavior. Duplex realtime audio is not part of Phase 7; browser permission, upload, provider, cancellation, and degraded-state parity remain mandatory.
4. **Approved browser model — RESOLVED:** CVWEB-01 is release-blocking. Plan 07-02 must approve an exact ONNX model, labels artifact, release manifest, hashes, redistribution status, and server-equivalent golden fixtures before Plan 07-10 runs. Phase 7 cannot complete with browser vision merely disabled. If no artifact is approved, execution stops at the checkpoint and CVWEB-01 must be moved to a separately approved phase rather than silently reduced.
5. **Browser test runner — RESOLVED:** Use a pinned `@playwright/test` version recorded in a dedicated lockfile and exactly matched to an immutable-digest Microsoft Playwright image. Plan 07-02 verifies both identities before Plan 07-12 installs or executes them; `npx` may not download an undeclared package.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Node.js | web/contracts | yes | 20.20.2 | Container build image. [VERIFIED: environment probe] |
| npm | web lock/build | yes | 10.8.2 | Container build image. [VERIFIED: environment probe] |
| Python | API/harness | yes | 3.12.10 | Container runtime image. [VERIFIED: environment probe] |
| pip | Python locks/tests | yes | 26.1.2 | Container build image. [VERIFIED: environment probe] |
| Docker | standalone deployment | yes | 29.7.2 | None for deployment smoke; local unit tests can run without it. [VERIFIED: environment probe] |
| Approved ONNX model/release | browser vision | not established | — | Server fallback or explicit unavailable/review state. [VERIFIED: bounded inspection] |

## Sources

### Primary codebase evidence (HIGH confidence)

- `07-CONTEXT.md` — locked scope, safety, verification, and ownership boundaries.
- `07-PATTERNS.md` — migration map, parity counts, target responsibilities, test map, and waves.
- `desktop/codex-harness.cjs` — session/turn/approval behavior and normalized desktop event baseline.
- `agent/src/kisansathi_agent/server.py` — canonical tool registration and read/write annotations.
- `backend/app/services/tflite_crop_health.py` — quality, confidence, margin, crop, checksum, and release gates.
- `src/context/AIConversationContext.jsx` — reducer, resume, approval, voice, image fallback, and refresh behavior.

### Official documentation (MEDIUM confidence)

- https://html.spec.whatwg.org/multipage/server-sent-events.html — EventSource events, reconnection, event IDs, `Last-Event-ID`.
- https://onnxruntime.ai/docs/tutorials/web/ — browser execution providers and support constraints.
- https://onnxruntime.ai/docs/tutorials/web/env-flags-and-session-options.html — ordered WebGPU/WASM providers.
- https://onnxruntime.ai/docs/tutorials/web/deploy.html — WASM/JSEP asset deployment.
- https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ — OAuth2/JWT dependency and verification pattern.
- https://docs.docker.com/compose/how-tos/startup-order/ — health-gated service startup.
- https://docs.docker.com/compose/gettingstarted/ — health checks and persistent volumes.

## Metadata

**Confidence breakdown:**
- Contracts and architecture: HIGH — directly derived from locked context and targeted source behavior.
- Streaming/auth/deployment: MEDIUM-HIGH — official standards plus project constraints; exact endpoint/IdP/retention choices remain open.
- Browser vision: HIGH for safety invariants, MEDIUM for package version until the SUS checkpoint is resolved.
- Recommended waves: HIGH — aligns with disjoint ownership and integration order in the pattern map.

**Research date:** 2026-09-17  
**Valid until:** 2026-10-17 for architecture; recheck package versions at implementation.

## RESEARCH COMPLETE
