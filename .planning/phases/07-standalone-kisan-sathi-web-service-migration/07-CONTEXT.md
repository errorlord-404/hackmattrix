# Phase 7 Context: Standalone Kisan Sathi Web

## Goal

Create a standalone folder named exactly `Kisan Sathi Web/` containing a
deployable web version of KisanSathi. It must own its frontend, backend, API,
agent harness, tests, configuration, and deployment artifacts and must not rely
on the parent repository at runtime.

## Locked Decisions

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

## Standalone Folder Shape

The plan should converge on a structure equivalent to:

```text
Kisan Sathi Web/
  apps/web/                 React browser application
  services/api/             FastAPI domain/data service
  services/harness/         provider-neutral LLM orchestration service
  packages/contracts/       generated/shared API and event contracts
  packages/tool-registry/   canonical tool schemas, policies, and routing
  packages/browser-vision/  worker, preprocessing, ONNX/ORT integration
  models/                   versioned manifests and approved deployable assets
  deploy/                   containers, proxy, health checks, environments
  tests/                    parity, E2E, load, failure and security tests
  docs/                     migration manifest, operations and rollback
```

The planner may refine language/framework choices when evidence supports it,
but must preserve these responsibility boundaries.

## Migration Rules

- Inventory first; copy only source/config/assets required at runtime.
- Exclude `.git`, `node_modules`, caches, build outputs, local databases,
  uploads, downloaded runtimes, logs, secrets, and the full `codex/` fork.
- Record copied, adapted, replaced, and excluded paths in a migration manifest.
- Establish baseline contract fixtures before changing transport or identity.
- Build a walking end-to-end web slice before parallel feature migration.
- Use disjoint write ownership for parallel agents and integration checkpoints
  after every wave.
- No cutover until contract parity, safety invariants, deployment smoke tests,
  and rollback evidence pass.

## Required Verification

- Unit and contract tests for provider adapters, normalized tool calls, tool
  result envelopes, capability negotiation, approvals, idempotency, and auth.
- Golden event-stream tests comparing Electron behavior with the web protocol.
- Tool inventory/schema parity tests covering required registered tools.
- Cross-tenant tests proving one authenticated user cannot select another
  farmer, field, session, upload, diagnosis, report, or tool result.
- Browser matrix tests for text, image, voice, streaming, reconnect, approval,
  WASM vision, WebGPU enhancement, and server fallback.
- Deployment tests from a clean checkout with only documented environment
  variables and mounted persistent volumes.
- Load and failure tests for concurrent streams, provider timeouts/rate limits,
  duplicate events, reconnects, tool retries, and CV fallback.

## Agent Execution Constraint

Research and planning may inspect the parent repository. Implementation agents
must write to disjoint paths under `Kisan Sathi Web/`, must not revert
other agents' work, and must coordinate through published contracts rather than
cross-editing another agent's subsystem.
