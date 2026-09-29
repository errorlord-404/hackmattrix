# Phase 7 Validation Architecture

## Purpose

This file is the Nyquist contract for Phase 7. Every implementation task has a deterministic automated check, and each wave ends with an integration checkpoint before dependent work begins. Commands run only against `Kisan Sathi Web/` or read-only baseline fixtures from the parent tree.

## Fast-feedback policy

- Focused unit/contract commands should finish within 30 seconds where practical.
- Docker build, three-browser, load, clean-checkout, and rollback commands are phase gates and may exceed 30 seconds; they are not used as the only feedback for an implementation task.
- No watch-mode command is allowed.
- A test command must fail on missing behavior; lint/build alone cannot satisfy behavioral acceptance.

## Task-to-automation map

| Plan | Task | Wave | Automated evidence |
|---|---:|---:|---|
| 07-01 | 1 | 1 | manifest, parent-baseline, and frontend-parity baseline fixture tests |
| 07-01 | 2 | 1 | copy/export dry-run plus standalone-only boundary scan |
| 07-01 | 3 | 1 | complete contract-fixture suite |
| 07-02 | 1 | 1 | checkpoint-record schema validates exact package, image, and model approvals |
| 07-02 | 2 | 1 | schema-valid approval-record validator and negative-record tests |
| 07-03 | 1 | 2 | API store/contract parity tests |
| 07-03 | 2 | 2 | API route parity tests |
| 07-03 | 3 | 2 | data export/import/rollback tests |
| 07-04 | 1 | 3 | OIDC/JWT/session/CSRF tests |
| 07-04 | 2 | 3 | API and harness claim-verifier parity tests |
| 07-04 | 3 | 3 | cross-tenant object matrix |
| 07-05 | 1 | 2 | exact registry snapshot parity |
| 07-05 | 2 | 2 | workflow policy and prompt-injection tests |
| 07-05 | 3 | 2 | actor injection, idempotency, and API shaping tests |
| 07-06 | 1 | 4 | reconnect/replay/retention tests |
| 07-06 | 2 | 4 | approval/audit/idempotency tests |
| 07-06 | 3 | 4 | authenticated fake-provider walking slice |
| 07-07 | 1 | 5 | provider configuration/capability contract and locked transport dependency tests |
| 07-07 | 2 | 5 | five-provider normalization matrix |
| 07-07 | 3 | 5 | runtime wiring and sentinel-secret integration tests |
| 07-08 | 1 | 5 | root/web install, lint, build, standalone import scan |
| 07-08 | 2 | 5 | auth client/session gate tests |
| 07-08 | 3 | 5 | HTTP/SSE reducer and reconnect tests |
| 07-09 | 1 | 6 | authenticated media API tests |
| 07-09 | 2 | 6 | browser media behavior tests |
| 07-10 | 1 | 6 | approved manifest/artifact and preprocessing tests |
| 07-10 | 2 | 6 | WASM/WebGPU worker and fallback tests |
| 07-10 | 3 | 6 | server revalidation/persistence tests |
| 07-14 | 1 | 6 | dashboard/field/map component tests |
| 07-14 | 2 | 6 | soil/weather/irrigation/crop component tests |
| 07-14 | 3 | 6 | core farm browser smoke suite |
| 07-15 | 1 | 6 | market/scheme/machinery component tests |
| 07-15 | 2 | 6 | reports/settings/alerts/finance-boundary tests |
| 07-15 | 3 | 6 | reference/admin browser smoke suite |
| 07-11 | 1 | 7 | full API/harness suites and route inventory |
| 07-11 | 2 | 7 | Compose config/build and health config check |
| 07-11 | 3 | 7 | clean-checkout/restart/log-redaction smoke |
| 07-12 | 1 | 8 | deployed contract/security suites plus Electron-to-web frontend-parity map validation |
| 07-12 | 2 | 8 | locked three-engine farm+harness browser matrix |
| 07-16 | 1 | 9 | load/failure and provider/CV chaos suites |
| 07-16 | 2 | 9 | structured release-gate result generation bound to approval and frontend-parity digests |
| 07-16 | 3 | 9 | generated 16-requirement parity report |
| 07-13 | 1 | 10 | cutover preflight against checksummed gate-results JSON |
| 07-13 | 2 | 10 | rollback drill suite |
| 07-13 | 3 | 10 | release-evidence and parent-baseline validators |

## Wave integration gates

| Wave | Gate |
|---:|---|
| 1 | Frozen contracts, approval record, selective-copy safety, and parent baseline validate. |
| 2 | API domain parity and exact 78-tool registry pass independently. |
| 3 | OIDC/session claims and complete two-tenant object matrix pass. |
| 4 | Authenticated fake-provider read/write walking slice passes with replay and one-effect retry. |
| 5 | Real provider factory and browser shell/auth/transport integrate without secrets or identity selectors. |
| 6 | All farm UI, media, approved WASM/WebGPU candidate, server fallback, and authoritative persistence paths pass. |
| 7 | Clean-checkout deployment, readiness, restart persistence, and observability pass. |
| 8 | Contract, security, and all-workflow browser matrices pass with locked dependencies. |
| 9 | Load/failure gates pass and all prior commands produce checksummed JSON evidence and a generated parity report. |
| 10 | Dry-run cutover and rollback consume current machine evidence; parent integrity matches the Wave 1 baseline and standalone-only boundary scan passes. |

## Release-blocking invariants

- No required test may be marked skipped because credentials, an approved model, browser binaries, or an IdP are missing; deterministic fake infrastructure is required for core tests.
- WebGPU is opportunistic at runtime, but its code path must be exercised with a supported CI/browser profile or an approved hardware-run artifact tied to the release checksum.
- CVWEB-01 cannot pass without an approved distributable ONNX artifact and labels file.
- Cutover consumes machine-readable gate results, never Markdown assertions alone.
- Any path write outside `Kisan Sathi Web/` fails the parent-integrity gate.
- Dependency locks, browser image, deployable model/labels, and final test artifacts must match the validated approval-record digest.
- Every Electron-visible frontend baseline row must have one passing standalone black-box/UI evidence ID; route existence alone is not parity evidence.

## Validation Audit 2026-09-19

The phase was re-audited against all 16 plan files, all plan summaries, the
machine release ledger, the model registry, and the current standalone tree.

| Metric | Count |
|---|---:|
| Plan summaries present | 16/16 |
| Release-gate results | 14 pass, 1 fail |
| Model/pipeline tests | 43 passed |
| Model pipeline doctor | Core, ONNX, PyTorch/TorchVision, TensorFlow, TF Hub, and TFLite backends available; activation remains disabled |
| API tests | 45 passed |
| Browser matrix | 12 passed across Chromium, Firefox, and WebKit |
| Docker prototype smoke | API, web proxy, and ONNX inference passed; result remained non-diagnostic |
| Nyquist software gaps resolved | 1 (dedicated vision persistence suite) |
| Release-only manual gates | 2 |

### Requirement coverage

- **COVERED:** migration boundary, contracts, auth/OIDC, tenant isolation,
  tool registry, provider adapters, harness replay, media, API persistence,
  frontend build, deployment, browser matrix, load/failure, rollback, and
  machine-readable release evidence.
- **PARTIAL / MANUAL-ONLY:** CVWEB-01/02 executable approved-model evidence and
  the WebGPU run against an approved artifact. The browser WebGPU profile has a
  fail-closed smoke check, but no approved model may be substituted for the
  required artifact run.

The `cv-approval` gate remains intentionally failed. No placeholder, research
candidate, or structural ONNX stub was promoted, and no Markdown or user
approval statement overrides the machine approval record.
