# Phase 7: Standalone Kisan Sathi Web Migration - Pattern Map

**Mapped:** 2026-09-17  
**Phase directory:** `.planning/phases/07-standalone-kisan-sathi-web-service-migration/`  
**Planning inputs:** `07-CONTEXT.md`; `.planning/REQUIREMENTS.md` WEB-01..10, CVWEB-01..02, MIG-01..02, WEBVER-01..02  
**Research input:** `07-RESEARCH.md` exists and resolves the OIDC/session, replay-retention, voice, approved-model, and browser-test-runner decisions. Codebase evidence remains authoritative for migration parity.  
**Files analyzed:** 58 representative runtime, contract, configuration, test, and workflow files plus repository-wide inventories/searches  
**Target units classified:** 31 files or cohesive file groups  
**Analogs found:** 26 / 31 (5 genuinely new web-service concerns have no close local analog)

## Executive Pattern Decision

Build the standalone tree as a selective migration, not a repository copy.

- Copy the React product surface and FastAPI domain/reference implementation into their new ownership boundaries.
- Adapt every browser-to-server boundary: remove browser-selected `X-Farmer-ID`, replace `window.kisanHarness`, and remove Electron/Codex process assumptions.
- Convert the Python MCP tool definitions into one canonical, provider-neutral registry. Keep tool names, input shapes, read/write annotations, bounded result envelopes, idempotency, and safety wording stable.
- Treat `desktop/` as a behavioral oracle only. Its normalized events and tests seed golden web-protocol fixtures; none of its Electron/process code ships.
- Keep domain logic in `services/api/`; keep provider calls, turn state, approvals, tool selection, and stream replay in `services/harness/`.
- Browser CV is screening only. It may produce a candidate, but authoritative persistence remains an API operation and completed output remains gated by the same release manifest as server inference.
- Do not copy the full `codex/` fork, generated/runtime data, caches, private model artifacts, or rejected demo models into a deployable model bundle.

## File Classification

| New/Modified Target | Role | Data Flow | Closest Existing Analog | Match Quality |
|---|---|---|---|---|
| `Kisan Sathi Web/package.json` | config | batch/build | `package.json` | role-match |
| `Kisan Sathi Web/apps/web/src/**` (non-AI UI) | component/hook/store | request-response | `src/**` | exact copy then import-path adaptation |
| `apps/web/src/api/httpClient.js` | service | request-response | `src/api/client.js` | role-match; auth replacement required |
| `apps/web/src/api/farmStateApi.js` | service | CRUD/request-response | `src/api/farmStateApi.js` | exact surface; transport adaptation |
| `apps/web/src/api/referenceApi.js` | service | request-response/cache | `src/api/referenceApi.js` | exact |
| `apps/web/src/api/harnessClient.js` | service | streaming/request-response | `desktop/preload.cjs` + `desktop/codex-harness.cjs` | data-flow match; implementation replaced |
| `apps/web/src/context/AIConversationContext.jsx` | provider | event-driven/streaming/file-I/O | `src/context/AIConversationContext.jsx` | exact state-machine match; transport replaced |
| `apps/web/src/components/features/ai/{ConversationView,HarnessStatusCard,VoiceButton}.jsx` | component | event-driven | same paths under `src/` | exact/adapt |
| `apps/web/src/workers/vision.worker.js` | worker | file-I/O/transform | `backend/app/services/tflite_crop_health.py` | contract-match only |
| `services/api/app/**` | controller/service/model/config | CRUD/request-response/batch | `backend/app/**` | exact copy with trust-boundary adaptations |
| `services/api/app/auth/{claims,dependencies}.py` | middleware/model | request-response | `backend/app/farm_state/dependencies.py` | replacement; no production-auth analog |
| `services/api/app/farm_state/store.py` | store/migration | CRUD/file-I/O | `backend/app/farm_state/store.py` | exact behavior, storage strategy review |
| `services/api/app/routers/assistants.py` | controller | file-I/O/request-response | `backend/app/routers/assistants.py` | exact domain endpoints; remove harness/provider config ownership |
| `services/api/app/services/{crop_health,tflite_crop_health}.py` | service | file-I/O/transform | same paths under `backend/app/services/` | exact safety baseline |
| `services/api/app/services/sarvam.py` | provider adapter | request-response/file-I/O | `backend/app/services/sarvam.py` | exact for voice provider only |
| `services/harness/app/main.py` | controller | streaming/request-response | `backend/app/main.py` + `backend/app/routers/assistants.py` | role-match |
| `services/harness/app/protocol.py` | model/utility | event-driven/streaming | `desktop/codex-harness.cjs::normaliseNotification` | contract-match |
| `services/harness/app/{sessions,orchestrator}.py` | service/store | event-driven/streaming | `desktop/codex-harness.cjs` | data-flow match; process code excluded |
| `services/harness/app/providers/base.py` | provider | streaming/request-response | `backend/app/services/sarvam.py` error boundary | partial; LLM capabilities are new |
| `services/harness/app/providers/{openai,anthropic,gemini,compatible,local}.py` | provider adapters | streaming/request-response | none | no analog |
| `services/harness/app/secrets.py` | config/service | request-response | `backend/app/core/config.py` | role-match; redaction/storage is new |
| `packages/contracts/{events,tools,provider-capabilities,tool-result,crop-health}.*` | model/config | transform | desktop event normalization + agent result + ML JSON schema | exact contract sources |
| `packages/tool-registry/**` | registry/service/policy | request-response | `agent/src/kisansathi_agent/{server,tools,result,backend_client}.py` | exact semantic source |
| `packages/browser-vision/src/{manifest,preprocess,runtime}.js` | service/utility | file-I/O/transform | `tflite_crop_health.py` + release validator | contract-match only |
| `models/manifests/**` | config | file-I/O | `ml/releases/*.yaml` | exact format; approved assets only |
| `models/validate_release_manifest.py` | utility | file-I/O/transform | `ml/training/validate_release_manifest.py` | exact/adapt root paths |
| `deploy/{compose.yaml,Dockerfile.*,proxy/**}` | config | batch/request-response | `backend/docker-compose.universal-data.yml` | partial; production proxy/containers new |
| `deploy/health/**` and root scripts | utility/test | request-response/batch | `scripts/{start-demo,demo-check}.ps1` | role-match; web/container rewrite |
| `tests/contract/**` | test | request-response/transform | agent/backend/frontend contract tests | exact patterns |
| `tests/e2e/**` | test | event-driven/file-I/O | desktop harness tests + React tests | behavior match; browser runner new |
| `tests/load/**` | test | streaming/batch | none | no analog |
| `docs/{MIGRATION_MANIFEST,OPERATIONS,ROLLBACK}.md` | config/docs | batch | README/backend docs and this map | role-match/new evidence |

## Source-to-Target Migration Manifest

The implementation manifest should use exactly four dispositions: `copy`, `adapt`, `replace`, and `exclude`. Directory rows below are intentional cohesive units; the implementation manifest should expand them to individual files and hashes.

| Source | Target | Disposition | Required treatment |
|---|---|---|---|
| `src/App.jsx`, `src/main.jsx`, `src/routes/**`, `src/pages/**`, `src/components/**`, `src/context/FarmDataContext.jsx`, `src/hooks/**`, `src/i18n/**`, `src/constants/**`, `src/lib/**`, live `src/data/**` modules | `apps/web/src/**` | copy | Preserve routing, responsive UI, localization, maps, forms, and domain behavior. Update only imports and service boundaries. |
| `src/index.css`, `index.html`, `public/{favicon.svg,icons.svg,farmer.jpg}` | `apps/web/` equivalents | copy | Preserve actual referenced assets. Use web-root asset paths, not Electron-relative bundling. |
| `src/api/referenceApi.js` | `apps/web/src/api/referenceApi.js` | copy/adapt | Preserve bounded local stale-cache behavior and explicit cache metadata. Route through same-origin proxy where possible. |
| `src/api/client.js`, `src/api/farmStateApi.js` | `apps/web/src/api/httpClient.js`, `farmStateApi.js` | adapt | Keep timeout/request-ID/error mapping/API methods. Delete `getFarmerId`, `VITE_DEMO_FARMER_ID`, and `X-Farmer-ID`; send session credentials and idempotency keys. Encode path IDs. |
| `src/context/AIConversationContext.jsx` | `apps/web/src/context/AIConversationContext.jsx` | adapt | Preserve state, messages, voice, selected field, image fallback, pending approval/clarification, and refresh-after-write. Replace bridge calls with typed HTTP + resumable SSE/WebSocket client. |
| `src/components/features/ai/**` | same subtree under `apps/web` | adapt | Preserve user-visible stream/tool/approval behavior. Rename Codex/plugin status to provider/harness/capabilities. Add reconnect/cancel states. |
| `src/db/localDatabase.js`, `src/features/financeStore.js` | none by default | exclude | Both are currently unreferenced. WEB requirements also forbid silent finance-ledger migration. If offline storage is reintroduced, specify consent, tenant partitioning, retention, and reconciliation as a separate plan. |
| `src/services/hostedCatalogService.js`, unreferenced fixture-only `src/data/{chat,dashboard,fields,localizedContent}.js` | none unless import graph proves use | exclude | No live imports found. Do not carry dead/demo catalogs into a standalone runtime. |
| `backend/app/models/**`, `schemas/**`, reference routers/services/scraping, `farm_state/{rules,store}.py` | `services/api/app/**` | copy | Preserve domain rules, Pydantic response shapes, Beanie models, source attribution, and farmer-state behavior. |
| `backend/app/main.py` | `services/api/app/main.py` | adapt | Preserve lifespan, degraded Mongo startup, router registration, and request IDs. Replace wildcard CORS, update health component names, add auth middleware/dependency. |
| `backend/app/farm_state/dependencies.py` | `services/api/app/auth/dependencies.py` plus a claim-scoped store dependency | replace | Never accept browser/model farmer IDs. Resolve tenant/farmer from verified session claims and reject missing/ambiguous claims. |
| `backend/app/routers/farm_state.py` | same under `services/api` | adapt | Keep endpoint/response/idempotency behavior. Require authorization on every object access; add tenant predicates/claim-scoped store selection. |
| `backend/app/routers/assistants.py` | same under `services/api` | adapt | Keep diagnosis, feedback, voice, translation, and authoritative persistence. Remove deprecated advisor/session streaming and mutable runtime key endpoint from public domain API. |
| `backend/app/services/{crop_health,tflite_crop_health,sarvam}.py` | same under `services/api` | copy/adapt | Preserve fail-closed states and provider error hygiene. Resolve model paths inside the standalone bundle/mount. Keep provider keys server-only. |
| `backend/requirements*.txt`, `pytest.ini` | `services/api/` equivalents | adapt | Pin/relock dependencies for clean builds; do not copy an environment or caches. |
| `backend/scripts/{seed_local_reference_data,seed_demo_farmer_state,refresh_live_reference_data,reset_demo_farmer_state}.py`, `backend/n8n/**` | `services/api/scripts/**`, `deploy/n8n/**` | adapt | Replace trusted farmer header inputs with an explicit admin/test bootstrap path. Retain clear demo labeling and authenticated webhooks. |
| `agent/src/kisansathi_agent/server.py` | `packages/tool-registry/registry.py` | adapt | Preserve all 78 canonical names/descriptions and 56 read/22 write annotations. Add workflow tags/allowlists and capability requirements. Do not register all tools with the model every turn. |
| `agent/src/kisansathi_agent/tools.py` | `packages/tool-registry/executor.py` | adapt | Preserve routing, validation, deterministic idempotency, output bounds, and safety summaries. Inject actor scope from server context, never tool arguments. |
| `agent/src/kisansathi_agent/{result,errors}.py` | `packages/tool-registry/{result,errors}.py` | copy | This is the canonical tool-result/error envelope. |
| `agent/src/kisansathi_agent/backend_client.py` | `packages/tool-registry/api_client.py` | adapt | Keep request IDs, timeout mapping, safe error parsing, and idempotency. Replace launcher farmer header with a signed/internal actor context. |
| `agent/skills/kisansathi/**` | `services/harness/app/policy/kisansathi/**` | adapt | Preserve routing, evidence, answer, and safety policy. Replace “desktop/launcher” wording with authenticated web-session wording and make allowlist selection machine-readable. |
| `agent/config/**`, plugin manifests/launcher, `agent/src/**/__main__.py` | none | exclude/replace | MCP stdio and Codex plugin boot are not the web runtime. Their semantics move to registry and harness services. |
| `desktop/codex-harness.cjs`, `main.cjs`, `preload.cjs` | no runtime copy; fixtures under `tests/fixtures/electron-events/**` | replace | Preserve the public bridge behavior and normalized events as fixtures. Exclude child-process spawn, IPC, temp-file transport, PowerShell quoting, and Electron window code. |
| `tests/desktop/**` | `tests/contract/test_event_stream_golden.*`, `tests/e2e/harness-resume.spec.*` | adapt | Re-express start/resume/send/interrupt/approval/error recovery against the web protocol. |
| `ml/contracts/crop-health-result.schema.json` | `packages/contracts/crop-health-result.schema.json` | adapt | Add `browser_wasm` and `browser_webgpu` inference locations while retaining strict fields, max three candidates, limitations, review state, and artifact hash. |
| `ml/releases/crop-health-v0.1.manifest.example.yaml` | `models/manifests/release.example.yaml` | copy/adapt | Use as the deployable manifest template. Add ONNX/ORT-Web artifact and preprocessing metadata if browser execution is enabled. |
| `ml/releases/crop-health-tfhub-tomato-controlled-demo-v0.2.yaml`, `v0.3.yaml` | documentation evidence only | exclude from deployable models | Both are explicitly rejected for field release; v0.3 also prohibits artifact distribution until gates pass. |
| `ml/training/validate_release_manifest.py` | `models/validate_release_manifest.py` | copy/adapt | Run during build/startup for every mounted server or browser model. Extend to validate browser artifact/checksum/runtime compatibility. |
| `ml/orchestration/**`, `backend/app/services/tflite_crop_health.py` | API inference plus browser-vision policy modules | adapt | Reuse confirmation, score, margin, quality, unsupported-crop, OOD/review, and limitation semantics. Do not port PyTorch/TFLite code directly into the browser. |
| `ml/training/**` other than release validation, private data/artifacts, demo downloads/evaluations | none in production runtime | exclude | Training and data-preparation are reproducible offline pipelines, not service runtime dependencies. |
| `scripts/check_api_contracts.py` | `tests/contract/test_openapi_client_parity.py` | adapt | Expand from path-shape presence to method, auth, request/response schema, and generated-client drift checks. |
| `scripts/{start-demo,demo-check}.ps1`, `backend/docker-compose.universal-data.yml`, `.env.example` | root scripts and `deploy/**` | replace/adapt | Preserve health wait, owned-process cleanup, Mongo volume/healthcheck, and explicit env documentation. Add API, harness, web, proxy, volumes, secrets, readiness, and clean-checkout smoke. |
| `package-lock.json` | standalone lockfile | regenerate | Do not hand-copy after workspace/dependency changes. |
| `codex/**` | none | exclude | Never fork/embed it. The web harness implements only KisanSathi conversation/tool/approval/stream requirements. |
| `.git/`, `node_modules/`, `dist/`, caches, `data/`, `backend/data/`, uploads, logs, `.runtime/`, output screenshots, `*.db`, `*.sqlite*`, secrets | none | exclude | Generated, local, private, or runtime state. Use named volumes and documented seed/migration paths. |

## Pattern Assignments

### `apps/web/src/api/httpClient.js` (service, request-response)

**Analog:** `src/api/client.js`

**Copy the timeout, correlation, safe error, and response parsing pattern** (`src/api/client.js:17-47`):

```javascript
const controller = new AbortController();
const requestId = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
const requestHeaders = { Accept: 'application/json', 'X-Request-ID': requestId, ...headers };
// fetch, parse JSON/text, map detail.code/message, preserve X-Request-ID
```

**Replace:** `getFarmerId()` and `requestHeaders['X-Farmer-ID']` (`src/api/client.js:13-15,23`). Use same-origin secure session cookies (or an Authorization token supplied by the auth client), `credentials: 'include'`, CSRF protection for cookie sessions, and caller-supplied `Idempotency-Key` for writes. Farmer/tenant identity must never be read from local storage.

### `apps/web/src/api/harnessClient.js` and `packages/contracts/events.*` (service/model, streaming)

**Behavioral analogs:** `desktop/preload.cjs:2-8`, `desktop/codex-harness.cjs:259-269`

Preserve this browser-facing capability shape, but implement it over HTTP plus resumable SSE/WebSocket:

```javascript
session: { start, resume, status }
chat: { sendText, sendImage, interrupt }
voice: { transcribe, translate, synthesize }
approval: { respond }
clarification: { respond }
onEvent(listener)
```

Canonical event types come from `normaliseNotification`:

```text
ready | unavailable | diagnostic
agentMessageDelta | agentMessageCompleted
tool(inProgress|completed|failed)
approval | clarification
turnCompleted | threadStatus
```

Add `event_id`, `session_id`, `turn_id`, monotonic `sequence`, `occurred_at`, schema `version`, and reconnect cursor. Duplicate `(session_id,event_id)` delivery must be harmless. The server must persist approval/clarification requests and reject responses from a different authenticated actor.

### `apps/web/src/context/AIConversationContext.jsx` (provider, event-driven/streaming)

**Analog:** `src/context/AIConversationContext.jsx`

Retain the event reducer behavior at lines `89-134`: deltas append to a draft keyed by item ID; completion finalizes/localizes/speaks; completed write tools refresh domain state; approval and clarification become pending UI actions; turn completion clears processing.

Retain session resume semantics from lines `136-153`, but persist only an opaque conversation/session ID. On reconnect, request events after the last acknowledged sequence. Do not persist provider credentials, tool arguments containing secrets, or farmer identity in local storage.

Retain media fallback semantics from lines `219-248`: browser/model image failure falls back to `farmStateApi.createDiagnosis`. Extend this so browser CV candidates always pass through authoritative API persistence/review before they appear as a diagnosis.

### `services/api/app/main.py` and auth dependency (controller/middleware, request-response)

**Analogs:** `backend/app/main.py:27-60`, `backend/app/farm_state/dependencies.py:8-23`

Preserve degraded reference-DB startup and correlation IDs. Replace the dependency entirely:

```python
# Existing temporary boundary to remove:
x_farmer_id: str | None = Header(default=None, alias="X-Farmer-ID")
farmer_key = x_farmer_id or "demo"
```

Target dependency contract:

```python
claims = Depends(require_session_claims)
actor = ActorScope(user_id=claims.sub, tenant_id=claims.tenant_id,
                   farmer_id=claims.farmer_id, roles=claims.roles)
store = farm_store_for(actor.tenant_id, actor.farmer_id)
```

No route, query, form field, tool schema, or browser header may override this scope. Keep a test/dev token issuer behind an explicit environment mode; a production IdP integration is not implied by Phase 7's current out-of-scope statement.

### `services/api/app/routers/farm_state.py` (controller, CRUD)

**Analog:** `backend/app/routers/farm_state.py:277-355`

Copy the write sequence exactly:

1. Validate a Pydantic payload.
2. Resolve only the claim-scoped store.
3. Check `Idempotency-Key` against a canonical payload hash.
4. Return cached response for same key/same payload.
5. Return `409 idempotency_key_conflict` for same key/different payload.
6. Persist, build the authoritative response model, then save the idempotent response.

The reusable primitives are in `backend/app/farm_state/store.py:36-72`. Preserve server-generated IDs and authoritative response bodies. Apply object-level authorization before every get/update/delete, including field, session, upload, diagnosis, feedback, task, ledger entry, report, and tool result.

### `packages/tool-registry/**` (registry/service/policy, request-response)

**Analogs:** `agent/src/kisansathi_agent/server.py:13-45,47-124`, `tools.py:26-78`, `result.py:39-66,69-89,133-163`

Registry baseline is **78 tools: 56 read, 22 write**. Preserve every name, description, input schema, and read/write annotation. `farmer_id`, `tenant_id`, credentials, and authorization are context—not model arguments.

```python
_READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False,
                             idempotentHint=True, openWorldHint=False)
_WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                         idempotentHint=True, openWorldHint=False)
```

Preserve deterministic write keys (`tools.py:44-78`) and the result envelope:

```python
{
  "status": status,
  "summary": summary,
  "data": bounded_data,
  "source": source,
  "warnings": warnings,
  "request_id": request_id,
  "freshness": freshness,
  "action": {"method", "path", "resource_type", "affected_ids",
             "timestamp", "source", "warnings", "refresh"}
}
```

Add registry metadata for workflow tags and provider capabilities. The orchestrator chooses the smallest allowlist using `agent/skills/kisansathi/SKILL.md:13-49`; the full inventory remains queryable for parity tests but is not sent to the model each turn.

### `services/harness/app/{orchestrator,sessions,protocol}.py` (service/store, streaming)

**Behavioral analog:** `desktop/codex-harness.cjs:36-138,191-244`

Preserve start/resume, one active turn, cancellation, structured server requests, recoverable provider exits/errors, and cleanup. Replace all of `#spawnProcess` (`desktop/codex-harness.cjs:140-189`) with an in-process provider adapter interface:

```python
class ProviderAdapter(Protocol):
    capabilities: ProviderCapabilities
    async def stream_turn(self, request: ProviderTurnRequest) -> AsyncIterator[ProviderEvent]: ...
    async def cancel(self, provider_turn_id: str) -> None: ...
```

The orchestrator—not the provider—owns session authorization, tool allowlisting, normalized tool calls, approval gates, retries, event sequencing, audit, and persistence. Provider wire formats terminate inside adapters.

### `services/harness/app/providers/**` (provider adapters, streaming)

**Partial error-boundary analog:** `backend/app/services/sarvam.py:11-83`

Use typed safe provider errors with `code`, `retryable`, bounded message, and no raw response/credentials. Capability declaration must cover at least: text input, image input, tools, structured output, streaming, cancellation, and maximum limits. Reject unsupported requested capabilities before a turn begins or select an explicitly documented fallback.

No close local analog exists for LLM SDK calls. Implement adapters independently and test all with recorded fake transports; do not let SDK objects escape into protocol, persistence, or tool code.

### `packages/browser-vision/**` and `apps/web/src/workers/vision.worker.js` (worker/service, file-I/O/transform)

**Contract analogs:** `backend/app/services/tflite_crop_health.py:18-59,97-168,171-243`; `ml/training/validate_release_manifest.py:17-73`; `ml/contracts/crop-health-result.schema.json:1-52`

Copy policy, not Python inference code:

- quality failure is explicit and non-diagnostic;
- crop routing never silently chooses a specialist;
- score and top-1/top-2 margin gates are separate;
- model and labels checksums must match the approved manifest;
- independent field, unknown/OOD, and agronomist gates must all pass;
- limitations always accompany output;
- WASM is baseline, WebGPU is opportunistic, and all failures fall back to server;
- a browser result is a `candidate` until the API revalidates release identity and persists an authoritative result.

Preprocessing must be generated from or validated against one release manifest; do not maintain an independent browser constant set.

### `deploy/**` (config, batch/request-response)

**Analogs:** `backend/docker-compose.universal-data.yml:1-44`, `scripts/start-demo.ps1:19-121`, `scripts/demo-check.ps1:7-20`

Preserve health-gated dependencies, named persistent volumes, hidden/owned local processes, bounded health waits, and degraded optional-reference behavior. Add separate API/harness/web/proxy health and readiness checks. Production startup must fail on missing required secrets or invalid model manifests; optional providers report degraded/unavailable without fabricating capability.

## Shared Contracts to Freeze Before Transport Changes

| Contract | Baseline source | Preserve/add |
|---|---|---|
| FastAPI paths and response shapes | OpenAPI from `backend/app/main.py`; 84 path shapes currently | Preserve 53 frontend-used path shapes; version changed paths; generate shared client types. |
| Tool inventory | `agent/.../server.py` | Exact 78-name inventory, 56 read/22 write split, descriptions, JSON schemas, annotations, no farmer/tenant/secret args. |
| Tool result envelope | `agent/.../result.py` | Status, summary, bounded data, source, warnings, request ID, freshness, action/refresh hints. |
| Backend error envelope | `backend_client.py:79-129`, `src/api/client.js:30-46` | Stable `detail.code/message/retryable`, HTTP status, correlation ID; no raw provider body. |
| Idempotency | `store.py:36-72`, `tools.py:44-78` | Deterministic request hash; replay same payload; 409 on key reuse with different payload; actor/resource scope included. |
| Conversation commands | `preload.cjs:2-8` | Start/resume/status, send text/image, cancel, voice, approval, clarification, event subscription. |
| Event stream | `codex-harness.cjs:259-269` | Normalized events plus version, durable event ID, sequence, session/turn IDs, reconnect cursor and duplicate semantics. |
| Approval/clarification | `AIConversationContext.jsx:126-131,212-217` | Explicit pending state, exact request binding, authenticated responder, one terminal resolution, timeout/cancel behavior. |
| Auth/tenant scope | `farm_state/dependencies.py` and isolation tests | Replace header input with claims; enforce cross-object tenant ownership for every persistent resource. |
| Voice | `assistants.py:323-448`, `sarvam.py` | 10 MB bound, content type, completed/inconclusive/provider-unavailable, language codes, request ID, server-only key. |
| Image upload/diagnosis | `assistants.py:124-214` | MIME plus magic-byte validation, size bound, checksum, field ownership, confirmed crop, authoritative persistence, idempotency. |
| CV result | `crop-health-result.schema.json` | Strict statuses, model/version/location, quality, top-three candidates, limitations, review flag, content pack, artifact hash. |
| CV release | release YAML + validator | Exact artifact/labels hashes and size, preprocessing, thresholds, crop scope, OOD/field/agronomist gates, rollback release. |
| Workflow policy | `agent/skills/kisansathi/**` | Smallest workflow, exact field resolution, evidence/provenance, explicit writes, no machinery/payment/action claims. |

## Tests That Preserve Behavior

### Baseline fixtures to establish first

1. Export the current FastAPI OpenAPI document and representative JSON responses for all frontend-used routes.
2. Snapshot the 78-tool registry with schemas, descriptions, and annotations.
3. Convert desktop JSONL notifications/server requests into versioned normalized event fixtures.
4. Save canonical tool-result fixtures for `ok`, `degraded`, `error`, bounded/truncated, and write-action responses.
5. Record CV fixtures for low quality, crop confirmation, unsupported crop, low score, low margin, missing runtime, missing manifest, checksum mismatch, and approved completion.

### Target test mapping

| Target test | Adapt from | Required assertions |
|---|---|---|
| `tests/contract/test_openapi_client_parity.py` | `scripts/check_api_contracts.py` | Method + path + auth + request/response schema parity; generated client has no `X-Farmer-ID`. |
| `tests/contract/test_tool_registry_parity.py` | `agent/tests/test_stdio_server.py:39-67`, `test_tools.py:65-98` | Exact 78 tools, read/write annotations, no scope/secret args, no duplicate names. |
| `tests/contract/test_tool_results.py` | `agent/tests/test_tools.py:142-192` | Deterministic idempotency, authoritative write action, UTC timestamp, output bounds. |
| `tests/contract/test_event_stream_golden.py` | `tests/desktop/codex-harness.test.cjs` | Start/resume, deltas, completed messages, tool progress, approval, clarification, completion, malformed provider data, recovery. |
| `tests/contract/test_provider_capabilities.py` | new | Each adapter declares capabilities; unsupported image/tools/stream/cancel fails or uses declared fallback without silent downgrade. |
| `tests/contract/test_provider_normalization.py` | new | All adapters produce identical normalized text/tool/error/cancel events; raw SDK objects never escape. |
| `tests/security/test_auth_scope.py` | `backend/tests/test_farm_state.py:28-85` | Missing/invalid/expired session rejected; browser-controlled farmer header ignored/rejected; claims bind tenant/farmer. |
| `tests/security/test_cross_tenant.py` | `test_farm_state.py:28-36,411-429` | User A cannot read/mutate B's farmer, field, session, upload, diagnosis, feedback, report, task, ledger, stream, approval, or tool result. |
| `tests/security/test_secret_redaction.py` | provider error tests | Keys absent from logs, events, errors, tool args/results, DB records, and browser storage. |
| `tests/integration/test_approval_idempotency.py` | farm-state idempotency tests + desktop approval test | No write before approval; decline/cancel never executes; duplicate acceptance/retry produces one effect; mismatched request rejected. |
| `tests/integration/test_reconnect_resume.py` | desktop resume test | Reconnect after every event boundary; ordered replay after cursor; duplicate events do not duplicate text, tool calls, or writes. |
| `tests/integration/test_voice_image.py` | `test_farm_state.py:365-505`, `agent/tests/test_tools.py:251-268` | Bounds, MIME, unavailable states, localization, image fallback, authoritative persistence. |
| `tests/browser-vision/*` | `backend/tests/test_crop_health.py`, ML tests | WASM baseline, optional WebGPU equivalence tolerance, preprocessing/checksum parity, all fail-closed/fallback states. |
| `tests/e2e/browser-matrix.*` | React conversation tests | Chromium/Firefox/WebKit: text, image, voice permission denial/success, stream, reconnect, approval, clarification, cancel, fallback. |
| `tests/load/streams.*` | new | Concurrent sessions, slow consumers, backpressure, reconnect storms, bounded buffers, cancellation latency. |
| `tests/failure/providers.*` | backend/agent provider failures | Timeout, 429, 5xx, malformed chunks/tool calls, duplicate events, retry exhaustion, no secret leakage. |
| `tests/deploy/clean_checkout.*` | demo scripts | Build/run with documented env only, mounted volumes, migrations, health/readiness, restart persistence, rollback to prior image/schema/model. |

Current baseline evidence: `scripts/check_api_contracts.py` reports **53 frontend adapter path shapes**, **84 OpenAPI path shapes**, and no missing frontend path shape.

## Shared Patterns

### Authentication and authorization

Apply to every API and harness route. Authentication establishes an immutable `ActorScope`; authorization verifies each resource belongs to that scope. Internal harness-to-API calls propagate a signed/service-authenticated actor context, not a model-generated header. Keep session cookie/token parsing in one dependency and object checks close to data access.

### Error handling and degraded states

Use typed codes and retryability from `agent/src/kisansathi_agent/errors.py:6-21`. Convert provider failures at the adapter boundary. Missing optional providers return explicit unavailable/degraded states; they do not become invented data or generic successful responses.

### Correlation, audit, and redaction

Preserve or generate `X-Request-ID` (`backend/app/main.py:54-60`). Add session/turn/tool-call IDs to audit records. Audit approvals, selected allowlist, tool arguments after secret redaction, authoritative result identity, retries, cancellation, and actor scope. Never log session tokens, API keys, raw authorization headers, or uploaded media bodies.

### Validation and file handling

Use Pydantic at HTTP boundaries. Preserve image/audio byte limits and image magic-byte checks from `assistants.py:124-158,161-214,323-329`. Use generated server-side upload IDs and private storage; do not accept filesystem paths from browser or model.

### Safety ownership

Provider adapters may suggest tool calls but cannot authorize them. Registry policy classifies reads/writes; orchestrator approval gates persistent writes; API authorization/idempotency/audit enforce them again. Domain responses remain authoritative after provider output.

## Disjoint Parallel Write Ownership

Publish `packages/contracts` fixtures first, then use these non-overlapping ownership lanes. No agent should edit another lane's paths.

| Agent lane | Exclusive write paths | Depends on | Integration checkpoint |
|---|---|---|---|
| 0. Scaffold/contracts | root workspace config, `packages/contracts/**`, `docs/MIGRATION_MANIFEST.md` | baseline fixture export | Contract schemas validate; source manifest covers every copied/adapted/excluded path. |
| 1. Web shell/auth/transport | root `package.json`; `apps/web` build shell, auth client/gate, harness client, and conversation context only | lane 0 event/API contracts plus shared auth | OIDC session and fake harness drive text/tool/approval/reconnect flows. |
| 1a. Core farm UI | `apps/web/src/features/core-farm/**`, `features/conversation/**`, core localization/hooks/assets/layout | web shell plus domain API | Dashboard through irrigation and conversation smoke pass. |
| 1b. Reference/admin UI | `apps/web/src/features/{reference,advisor,reports,settings,finance}/**`, reference client/localization/hooks | web shell plus domain API | Market through finance-boundary smoke pass. |
| 1c. Browser media | media API client and explicitly named voice/image components only | web shell plus auth/media API | Voice/image browser parity and degraded states pass. |
| 2. Domain API | `services/api/**` | lane 0 API/auth contracts | Existing backend suite ported; OpenAPI parity and tenant-scope tests pass. |
| 3. Tool registry/policy | `packages/tool-registry/**` | lane 0 tool-result schema | Exact 78-tool parity, annotations, output bounds, allowlists. |
| 4. Harness core/auth | `services/harness/app/**` except `providers/**` | lanes 0 and 3 | Fake provider passes golden stream, approval, cancel, reconnect, idempotency tests. |
| 5. Provider adapters | `services/harness/app/providers/**`, adapter unit fixtures | lane 4 adapter protocol | Capability/normalization/redaction tests pass per adapter. |
| 6. Browser vision/models | `packages/browser-vision/**`, `apps/web/src/workers/**`, `models/**` | lane 0 CV contracts; API persistence endpoint from lane 2 | WASM/fallback/checksum/preprocessing tests pass; no candidate is presented as authoritative. |
| 7. Deployment/ops | `deploy/**`, root startup/health scripts, `docs/{OPERATIONS,ROLLBACK}.md` | service interfaces stable | Clean-checkout compose smoke, volume persistence, readiness, rollback evidence. |
| 8. Cross-system verification | `tests/**` only | all lanes | Browser matrix, tenant isolation, stream/load/failure tests and parity report. |

Integration order:

1. Contracts and fixtures.
2. Walking slice: authenticated web session -> harness fake provider -> one read tool -> API -> streamed response.
3. One confirmed idempotent write with audit and UI refresh.
4. Full registry and provider adapters.
5. Voice/image and browser CV fallback.
6. Deployment and complete browser/contract gates.
7. Load/failure aggregation into checksummed JSON evidence.
8. Rollback rehearsal, final parent-integrity comparison, then cutover evidence.

## No Close Analog Found

| Target | Role/Data Flow | Reason / planning consequence |
|---|---|---|
| Production LLM provider adapters | provider, streaming | Current code spawns Codex; no SDK-neutral adapter exists. Define protocol and fake adapter first. |
| Durable resumable web event store | store, pub-sub/streaming | Desktop uses in-memory EventEmitter/JSONL. Design sequence/cursor/retention/duplicate semantics explicitly. |
| Production OIDC integration | middleware, request-response | Current header is explicitly not auth. Implement generic OIDC Authorization Code + PKCE, shared cookie verification for API/harness, and a test/dev issuer; production startup requires configured discovery/JWKS and fails closed. |
| ONNX Runtime Web WASM/WebGPU worker | worker, file-I/O/transform | Current inference is Python/TFLite/PyTorch. Port the release contract and preprocessing evidence, not implementation code. |
| Load/failure harness | test, streaming/batch | No current concurrent-stream or reconnect-storm suite. Choose a reproducible runner and committed thresholds. |

## Planner Guardrails

- Do not plan a bulk copy command without an allowlist and migration-manifest entry per file.
- Do not allow implementation outside `Kisan Sathi Web/`.
- Do not introduce a reverse runtime import, symlink, editable install, or parent-relative model/config path.
- Do not expose all 78 tools to every model turn; keep all 78 in the registry and select workflow-specific subsets.
- Do not put provider keys in browser configuration, runtime-config responses, tool arguments, events, logs, or conversation records.
- Do not classify translation, speech synthesis, transcription, or diagnosis as persistent merely because current MCP annotations mark them `_WRITE`; define side-effect policy explicitly while preserving approval where persistence occurs.
- Do not copy a rejected/demo manifest's artifact into `models/` as a deployable release.
- Do not migrate browser-local finance data silently.
- Do not claim browser inference parity from matching labels alone; require artifact hash, preprocessing, quality gate, thresholds, OOD behavior, and limitations.
- Do not cut over until parity, security, clean-checkout deployment, failure, load, and rollback evidence are all recorded.

## Metadata

**Analog search scope:** `src/`, `backend/app/`, `backend/tests/`, `backend/scripts/`, `agent/src/`, `agent/tests/`, `agent/skills/`, `desktop/`, `tests/desktop/`, `ml/contracts/`, `ml/releases/`, `ml/orchestration/`, `ml/training/`, `ml/tests/`, `scripts/`, root build/config files.  
**Explicit exclusion from analog search:** the full `codex/` implementation; only references proving current plugin coupling were inventoried.  
**Current-worktree note:** several baseline files are already modified/untracked by the user. This map describes the inspected working-tree state and does not overwrite or normalize it.  
**Pattern extraction date:** 2026-09-17
