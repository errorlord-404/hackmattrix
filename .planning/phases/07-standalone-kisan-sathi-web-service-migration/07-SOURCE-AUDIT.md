# Phase 7 Multi-Source Coverage Audit

## Locked decision IDs

The source context lists locked decisions without identifiers. Plans use these stable IDs in source order:

| ID | Locked decision |
|---|---|
| D-01 | All implementation writes stay under `Kisan Sathi Web/`; the existing application remains untouched. |
| D-02 | Do not embed Codex; build a focused web harness. |
| D-03 | Keep the harness provider-neutral behind capability-declared adapters. |
| D-04 | Keep credentials/model calls server-side and secrets out of browser, tools, logs, and conversations. |
| D-05 | Preserve FastAPI domain behavior/tool contracts; domain logic stays outside orchestration. |
| D-06 | Preserve the canonical full tool surface but send workflow-specific allowlists per turn. |
| D-07 | Persistent actions retain auth, confirmation, idempotency, audit, and authoritative responses. |
| D-08 | Replace Electron/Codex process transport with resumable web streaming, approvals, media, and cancellation. |
| D-09 | Replace `X-Farmer-ID` with authenticated claims and server-derived scope. |
| D-10 | Use hybrid worker WASM/WebGPU screening with server fallback and authoritative persistence. |
| D-11 | Browser CV candidates must satisfy the same release/checksum/preprocessing/safety contract. |
| D-12 | Add no autonomous machinery, financial/legal commitment, or chemical action. |

## Coverage

| SOURCE | ID | Feature / requirement | Plan | Status | Notes |
|---|---|---|---|---|---|
| GOAL | — | Independently installable/deployable standalone web service with frontend, API, harness, tools, auth, and hybrid CV | 07-01..07-13 | COVERED | Contract-first walking slice, parallel lanes, deployment, and release gates. |
| REQ | MIG-01 | Source manifest and explicit exclusions | 07-01 | COVERED | Per-file hash/disposition ledger. |
| REQ | MIG-02 | Parent untouched; no reverse runtime dependency | 07-01 | COVERED | Copy safety and target-boundary checks. |
| REQ | WEB-01 | Self-contained frontend/backend/harness/API/config/migrations/models/deploy | 07-03 | COVERED | API/data foundation; remaining runtime parts are completed in dependent plans. |
| REQ | WEB-02 | Startup, health/readiness, containers, volumes, secrets | 07-11 | COVERED | 07-02 is a mandatory package prerequisite. |
| REQ | WEB-03 | Authenticated claims and no browser farmer selector | 07-04 | COVERED | Auth and cross-tenant matrices. |
| REQ | WEB-04 | Capability-declared provider-neutral streaming | 07-07 | COVERED | Shared normalized adapter protocol. |
| REQ | WEB-05 | OpenAI, Anthropic, Gemini, compatible, local adapters | 07-07 | COVERED | Isolated mappings with fake transports. |
| REQ | WEB-06 | Server-only secrets and redaction | 07-07 | COVERED | Startup validation and sentinel leak tests. |
| REQ | WEB-07 | Sessions, SSE replay, cancellation, tools, clarification, approvals | 07-06 | COVERED | Durable walking slice. |
| REQ | WEB-08 | Canonical registry and workflow allowlists | 07-05 | COVERED | Exact 78/56/22 parity. |
| REQ | WEB-09 | Provider-independent safety semantics | 07-06 | COVERED | Approval/idempotency/audit/API authority. |
| REQ | WEB-10 | Typed browser transport with text/media/localization/tool parity | 07-08, 07-09, 07-14, 07-15 | COVERED | Shell/auth/transport, media, core farm, and reference/admin lanes have disjoint ownership. |
| REQ | CVWEB-01 | Worker ORT-Web WASM/WebGPU release parity | 07-10 | COVERED | 07-02 is the package prerequisite. |
| REQ | CVWEB-02 | Failure/OOD fallback and authoritative server path | 07-10 | COVERED | API revalidation/persistence. |
| REQ | WEBVER-01 | Electron/web workflow and safety parity before cutover | 07-12, 07-16 | COVERED | Complete browser/contract matrix plus generated machine-backed parity report. |
| REQ | WEBVER-02 | Browser/API/harness/provider/CV/auth/deploy/load/failure/rollback gates | 07-16, 07-13 | COVERED | Checksummed gate JSON is completed by rollback and final integrity evidence before cutover. |
| RESEARCH | — | Freeze OpenAPI/tool/event/result/CV fixtures first | 07-01 | COVERED | Baseline counts and schemas. |
| RESEARCH | — | Blocking legitimacy check for PyJWT and onnxruntime-web | 07-02 | COVERED | Human-only registry/source verification before install. |
| RESEARCH | — | Explicit runtime-data export/import rehearsal | 07-03 | COVERED | No live DB/upload copying. |
| RESEARCH | — | Immutable ActorScope and signed internal propagation | 07-04 | COVERED | Claim and object authorization tests. |
| RESEARCH | — | Canonical registry, effect classes, injection-safe allowlists | 07-05 | COVERED | Provider-independent policy. |
| RESEARCH | — | Append-before-publish SSE and confirmed write walking slice | 07-06 | COVERED | Hard constraint scheduled before fan-out. |
| RESEARCH | — | Adapter normalization, capability checks, redaction | 07-07 | COVERED | Five adapter families. |
| RESEARCH | — | Browser transport and complete farm/media parity | 07-08, 07-09, 07-14, 07-15 | COVERED | Disjoint shell, media, core-farm, and reference/admin ownership. |
| RESEARCH | — | Shared release descriptor and fail-closed hybrid vision | 07-10 | COVERED | Candidate-to-authority boundary. |
| RESEARCH | — | Same-origin Compose, health, observability, clean checkout | 07-11 | COVERED | Reproducible deployment. |
| RESEARCH | — | Browser matrix, load/failure, machine evidence, cutover, rollback | 07-12, 07-16, 07-13 | COVERED | Release-blocking checksummed evidence. |
| CONTEXT | D-01 | Target-only implementation | 07-01, 07-03, 07-08, 07-13 | COVERED | Path checks plus final parent-integrity proof. |
| CONTEXT | D-02 | Focused harness, no Codex embed | 07-01, 07-06 | COVERED | Electron/Codex treated only as fixture oracle. |
| CONTEXT | D-03 | Provider neutrality | 07-05, 07-06, 07-07 | COVERED | Registry/orchestrator/adapter separation. |
| CONTEXT | D-04 | Server-only credentials | 07-04, 07-07, 07-08, 07-09 | COVERED | Redaction and browser scans. |
| CONTEXT | D-05 | API domain authority | 07-01, 07-03, 07-05 | COVERED | Harness does not reimplement domain logic. |
| CONTEXT | D-06 | Full registry plus small allowlists | 07-05 | COVERED | Exact inventory and policy tests. |
| CONTEXT | D-07 | Persistent action controls | 07-06 | COVERED | Approval state machine and authoritative replay. |
| CONTEXT | D-08 | Web protocol/media parity | 07-01, 07-06, 07-08, 07-09 | COVERED | HTTP/SSE command/event contracts. |
| CONTEXT | D-09 | Claims-derived scope | 07-04, 07-06, 07-08 | COVERED | No browser/model identity override. |
| CONTEXT | D-10 | Hybrid worker/server CV | 07-10 | COVERED | WASM/WebGPU plus fallback. |
| CONTEXT | D-11 | CV release and safety equivalence | 07-10 | COVERED | Cross-runtime golden gates. |
| CONTEXT | D-12 | No unsafe physical/financial/chemical actions | 07-03, 07-05, 07-06, 07-09 | COVERED | Route/tool/policy/result exclusions. |

No deferred ideas were listed in `07-CONTEXT.md`. No source item is unplanned.
