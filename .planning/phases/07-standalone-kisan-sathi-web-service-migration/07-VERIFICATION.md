---
phase: 07-standalone-kisan-sathi-web-service-migration
verified: 2026-09-19T06:18:00Z
status: gaps_found
score: 15/17 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 12/17
  gaps_closed:
    - "Prototype migration rows now have SHA-256 source identities and the standalone boundary passes."
    - "The 42-test contract fixture suite passes."
    - "Plan 07-11 now names the actual deploy/nginx.conf proxy artifact."
    - "The release ledger, checksum manifest, and generated parity report are current and internally consistent."
  gaps_remaining:
    - "No approved distributable production CV release exists; cv-approval remains intentionally fail-closed."
gaps:
  - truth: "CVWEB-01 and dependent WEBVER-02 release readiness: an approved production browser/server CV release exists and all release gates pass."
    status: failed
    reason: "The current approval record explicitly marks release-cv deferred_unapproved, and the current machine ledger has exactly one failing gate: cv-approval. The three downloaded research checkpoints are valid for prototype inference but are not production-approved."
    artifacts:
      - path: "Kisan Sathi Web/docs/APPROVED_RELEASES.json"
        issue: "release-cv.approved, release_ready, activation_allowed, and diagnostic_use_allowed are false; approved_artifacts is null."
      - path: "Kisan Sathi Web/tests/results/gate-results.json"
        issue: "status=fail and release_ready=false; cv-approval exits 1 while the other 14 gates exit 0."
      - path: "Kisan Sathi Web/models/manifests/approved-release.yaml"
        issue: "No approved production release artifact is present for CVWEB-01."
    missing:
      - "A separately reviewed distributable ONNX model and labels bundle with exact hashes, release manifest, server/browser golden parity, field/OOD evidence, agronomist review, redistribution approval, and rollback identity."
      - "Independent approval that changes the release-cv record and reruns the release gate; research checkpoints must remain non-diagnostic until then."
behavior_unverified_items: []
---

# Phase 07: Standalone Kisan Sathi Web Service Migration — Verification Report

**Phase Goal:** Build `Kisan Sathi Web/` as an independently installable and deployable web service containing its own frontend, backend, API contracts, provider-neutral LLM harness, farm-tool orchestration, authentication boundary, and hybrid browser/server computer-vision path without changing the existing application's behavior.

**Verified:** 2026-09-19T06:18:00Z  
**Status:** `gaps_found`  
**Re-verification:** Yes — after manifest, contract, proxy, ledger, and parity evidence updates.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---:|---|---|---|
| 1 | WEB-01: standalone frontend, backend, contracts, harness, models, and deployment files are self-contained. | VERIFIED | `check_standalone_boundary.py --standalone-copy-check --check` passes; the standalone frontend build and deployment contract pass. |
| 2 | WEB-02: startup, health/readiness, environment validation, containers, volumes, and secret injection are defined. | VERIFIED | Compose/config health check passes; deployment, clean-checkout, rollback, and browser-matrix ledger gates pass. |
| 3 | WEB-03: identity is server-owned and cross-tenant access is denied. | VERIFIED | Current API/security evidence and the 14 non-CV release gates pass; browser clients do not select farmer identity. |
| 4 | WEB-04: provider-neutral streaming, capability, cancellation, and normalization contracts exist. | VERIFIED | Harness tests pass in the current ledger and the standalone harness suite. |
| 5 | WEB-05: the five provider families are isolated behind adapters/factory boundaries. | VERIFIED | Provider adapter/factory implementation and harness evidence pass. |
| 6 | WEB-06: provider credentials stay server-side and are redacted. | VERIFIED | Auth/security/harness evidence passes; no browser provider-secret storage path is present. |
| 7 | WEB-07: authenticated sessions, streaming, replay/resume, interruption, approvals, and clarification work over web transports. | VERIFIED | Harness, load/failure, frontend, and browser-matrix evidence passes; `deploy/nginx.conf` preserves same-origin SSE streaming. |
| 8 | WEB-08: the canonical 78-tool registry preserves the 56-read/22-write policy boundary. | VERIFIED | Tool-registry tests and the current contract gate pass. |
| 9 | WEB-09: writes are approval-bound, idempotent, bounded, actor-injected, and provenance-aware. | VERIFIED | API/harness/security/load-failure evidence passes. |
| 10 | WEB-10: the React client uses typed HTTP/SSE/media/auth transport without Electron IPC. | VERIFIED | UI tests, lint, standalone scan, and Vite build pass; standalone route/client code is wired to HTTP/SSE APIs. |
| 11 | CVWEB-01: an approved browser/server ONNX release is executable under the release contract. | FAILED (BLOCKER) | `validate_approved_releases.py --require-all` exits 1. `APPROVED_RELEASES.json` explicitly denies release-CV approval and no approved browser model/labels bundle exists. |
| 12 | CVWEB-02: unsupported/load/gate failures fall back to server or expert review without authoritative browser diagnosis. | VERIFIED | Browser-vision tests pass; API finalization returns `needs_expert_review`, `authoritative=false`, and no persisted diagnosis when no approved release is available. |
| 13 | MIG-01: every copied/adapted/replaced module is classified, hashed, and exclusions are explicit. | VERIFIED | All 281 manifest replacement rows have 64-character SHA-256 identities; manifest/standalone-copy checks pass. The eight prototype rows now have identities. |
| 14 | MIG-02: parent source remains intact and standalone runtime has no parent imports. | VERIFIED | Parent baseline check and standalone boundary check pass. This verifies stability relative to the captured parent baseline; it does not claim the pre-existing worktree is clean relative to HEAD. |
| 15 | WEBVER-01: contract/parity tests prove required workflows and safety semantics before cutover. | VERIFIED | Contract suite: 42 passed; current browser matrix, browser-vision, frontend, API/harness, and generated parity evidence pass for the implemented prototype/development scope. |
| 16 | WEBVER-02: browser/backend/harness/provider/CV/auth/tenant/deploy/load/failure/rollback evidence is reproducible and passing. | FAILED (BLOCKED) | The current checksummed ledger is reproducible and has 14 non-CV passes, but release readiness remains false because the intentional `cv-approval` gate fails. |
| 17 | Prototype scope: the three manifest-verified research crop models are exposed through the web application without becoming production-approved. | VERIFIED | The real authenticated Playwright flow fetched the prototype profile, uploaded `home_page.jpeg`, received HTTP 200 from `/api/v1/crop-disease/predict?crop=tomato`, and displayed an uncertain result with the controlled-imagery/non-diagnostic warning. |

**Score:** 15/17 truths verified; 1 root release gap affects CVWEB-01 and dependent WEBVER-02.

The user-requested prototype scope is implemented and wired. The full phase is not release-complete because production CV approval is correctly fail-closed.

## Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `Kisan Sathi Web/docs/MIGRATION_MANIFEST.md` | Complete source mapping with identities | VERIFIED | 281 replacement rows have SHA-256 identities; boundary and manifest checks pass. |
| `Kisan Sathi Web/models/crop_disease/registry.json` and `downloaded/*/download-manifest.json` | Prototype model registry and file integrity | VERIFIED | `mesabo_resnet50`, `harimitra`, and `plantvillage_efficientnet` each verify as valid; all are marked research-only. |
| `Kisan Sathi Web/models/crop_disease/prototype.py` | Non-production prototype profile | VERIFIED | Emits `prototype_available`, `prototype_only=true`, and all production/diagnostic activation flags false. |
| `Kisan Sathi Web/services/api/app/routers/crop_disease.py` | Authenticated prototype status and inference routes | VERIFIED | `/v1/crop-disease/prototype` and `/v1/crop-disease/predict` are implemented and use the downloaded-model service. |
| `Kisan Sathi Web/apps/web/src/api/cropDiseaseClient.js` and `apps/web/src/App.jsx` | Web UI prototype wiring | VERIFIED | Same-origin authenticated status and upload calls are rendered by the Crop health card with explicit research limitations. |
| `Kisan Sathi Web/deploy/nginx.conf` and `deploy/compose.prototype.yaml` | Same-origin proxy/SSE and prototype deployment contract | VERIFIED | Plan 07-11 names the proxy artifact; the prototype overlay binds the ONNX research candidate read-only and the Docker smoke test passes. |
| `Kisan Sathi Web/tests/results/gate-results.json` | Current machine release ledger | VERIFIED as evidence, NOT release-ready | 15 results: 14 pass, `cv-approval` fails; status is correctly `fail`. API, model, browser, frontend, deployment, rollback, and boundary checks pass. |
| `Kisan Sathi Web/tests/results/artifact-checksums.json` | Integrity binding for ledger outputs | VERIFIED | 31 referenced files checked; 0 missing, size-mismatched, or hash-mismatched files. |
| `Kisan Sathi Web/docs/PARITY_REPORT.md` | Generated 16-requirement parity report | VERIFIED | Generated from the ledger; `generate_parity_report.py --check` passes. |
| `Kisan Sathi Web/models/manifests/approved-release.yaml` and `models/browser/*` | Approved production CV bundle | BLOCKED (intentional) | No approved production bundle exists; this is the sole release blocker and must not be substituted with research models or placeholders. |

## Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| Migration manifest | Standalone tree/parent baseline | SHA-256 rows and copy/boundary validator | WIRED | Boundary and parent-baseline checks pass. |
| Crop prototype API | Downloaded research registry | `build_prototype_status` and `CropDiseaseInferenceService` | WIRED | Three verified downloads are the actual configured prototype candidates. |
| Web Crop health card | Crop prototype API | `cropDiseasePrototype()` and `predictCropDisease()` | WIRED | `App.jsx` fetches capabilities and posts selected image bytes with session credentials. |
| Browser vision worker | Approved release descriptor | descriptor validation before ORT session | WIRED FAIL-CLOSED | Worker/runtime rejects unapproved descriptors and routes failures to server fallback. |
| Vision finalization | Production approval/ownership boundary | descriptor, checksum, release, and idempotency revalidation | WIRED FAIL-CLOSED | Missing approval returns expert review and does not persist a diagnosis. |
| Nginx/prototype proxy | API/harness services and ONNX prototype | same-origin proxy/SSE settings and read-only candidate bind | WIRED | `deploy/nginx.conf` is the current plan-declared artifact; prototype Compose deployment and inference checks pass. |
| Release gate runner | Ledger → parity report | checksummed JSON → generated Markdown | WIRED | Ledger checksums validate and parity `--check` passes; Markdown cannot override the failing CV gate. |

## Data-Flow Trace (Level 4)

| Artifact | Data variable | Source | Produces real data | Status |
|---|---|---|---|---|
| `apps/web/src/App.jsx` Crop health card | `prototypeCapabilities` | Authenticated `GET /v1/crop-disease/prototype` | Yes; three verified model entries and seven crop IDs | FLOWING |
| `apps/web/src/App.jsx` Crop health card | `result` | Authenticated `POST /v1/crop-disease/predict` | Real browser upload reached the downloaded-model service and rendered the bounded uncertain result plus warning | FLOWING; VERIFIED |
| `services/api/app/routers/crop_disease.py` | prediction response | `CropDiseaseInferenceService` → `CropDiseaseRouter` → verified download manifests | Yes for installed research checkpoints | FLOWING |
| Prototype Compose overlay | container prediction | Read-only ONNX candidate bind mount → CPU ONNX Runtime adapter | Healthy API container returned HTTP 200 with `uncertain`, `mesabo_resnet50_onnx`, and the research warning | FLOWING; VERIFIED |
| `docs/PARITY_REPORT.md` | requirement statuses | `tests/results/gate-results.json` | Yes; generated and checked from current machine evidence | FLOWING |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Prototype model profile is available but non-production | `python scripts/validate_prototype_models.py --json` | `prototype_available`; 3 models; 7 crops; production/activation/diagnostic flags false | PASS |
| Real browser prototype upload | Playwright CLI against local standalone web/API | Authenticated tomato upload returned HTTP 200 and rendered `Uncertain screening signal` with the non-diagnostic warning | PASS |
| Docker prototype deployment | `docker compose -f deploy/compose.yaml -f deploy/compose.prototype.yaml build api` and stack smoke test | API, harness, and web containers healthy; real JPEG inference returned HTTP 200 with ONNX Runtime and `production_approved=false` | PASS |
| Downloaded research model manifests verify | `python -m models.crop_disease.downloader --all --verify` | `mesabo_resnet50`, `harimitra`, `plantvillage_efficientnet`: valid | PASS |
| Contract fixture suite | `python -m pytest packages/contracts/tests -q` | 42 passed | PASS |
| Prototype/API/vision persistence suites | `python -m pytest models/crop_disease/tests services/api/tests/test_prototype_api.py services/api/tests/test_vision_release.py services/api/tests/test_vision_persistence.py -q` | 13 passed | PASS |
| Browser CV contract suite | `npm --prefix packages/browser-vision test` | 9 passed | PASS |
| Web UI/lint/standalone checks | `npm --prefix apps/web run test:ui`; `npm --prefix apps/web run lint`; `npm --prefix apps/web run check:standalone` | 14 UI tests passed; 57 files linted; standalone boundary passed | PASS |
| Parent/source-tree integrity | `python scripts/capture_parent_baseline.py --repo-root .. --output docs/PARENT_BASELINE.json --check` | `parent baseline: PASS` | PASS |
| Standalone boundary | `python scripts/check_standalone_boundary.py --root . --manifest docs/MIGRATION_MANIFEST.md --standalone-copy-check --check` | `standalone boundary: PASS` | PASS |
| Generated parity evidence | `python tests/reports/generate_parity_report.py --results tests/results/gate-results.json --output docs/PARITY_REPORT.md --check --release-evidence docs/RELEASE_EVIDENCE.md` | `parity report: PASS` | PASS |
| Production CV approval gate | `python scripts/validate_approved_releases.py --record docs/APPROVED_RELEASES.json --require-all` | `FAIL: release-cv scope is deferred and unapproved; production release is blocked` | EXPECTED FAIL-CLOSED |

## Probe Execution

No `probe-*.sh` files are declared by the phase or present under `scripts/`; probe execution is not applicable.

## Requirements Coverage

| Requirement | Source plan(s) | Status | Evidence |
|---|---|---|---|
| WEB-01 | 07-03, 07-14, 07-15 | SATISFIED | Standalone runtime tree, frontend/domain/reference artifacts, boundary scan, and build pass. |
| WEB-02 | 07-02, 07-11 | SATISFIED for prototype/deployment contract | Development dependency approval, Compose, health, volumes, env, proxy, clean-checkout, and rollback evidence pass. Production release readiness remains separately blocked by CV approval. |
| WEB-03 | 07-04 | SATISFIED | Claims-derived auth and tenant-isolation evidence pass. |
| WEB-04 | 07-07 | SATISFIED | Provider-neutral harness capability/streaming/cancellation evidence passes. |
| WEB-05 | 07-07 | SATISFIED | Isolated provider adapters/factory and tests pass. |
| WEB-06 | 07-07 | SATISFIED | Server-side secret boundary and redaction/security evidence pass. |
| WEB-07 | 07-06 | SATISFIED | Session, replay/resume, approval, interruption, and SSE evidence passes. |
| WEB-08 | 07-05 | SATISFIED | Canonical tool registry and policy tests pass. |
| WEB-09 | 07-06 | SATISFIED | Approval, actor scope, idempotency, provenance, and safety tests pass. |
| WEB-10 | 07-08, 07-09, 07-14, 07-15 | SATISFIED for implemented prototype/development scope | Typed browser transport, media, routes, UI tests, lint, and build evidence pass. |
| CVWEB-01 | 07-02, 07-10 | BLOCKED | No approved distributable ONNX/labels release; research models remain non-production. |
| CVWEB-02 | 07-10 | SATISFIED fail-closed | Unsupported/load/gate failures and authoritative finalization fallback to server/expert review. |
| MIG-01 | 07-01 | SATISFIED | Current manifest hashes and boundary validation pass. |
| MIG-02 | 07-01 | SATISFIED | Parent baseline and no-parent-runtime-import checks pass. |
| WEBVER-01 | 07-02, 07-12, 07-16 | SATISFIED for current implemented scope | Contract suite, browser matrix, frontend/backend/harness/CV-fallback evidence, and generated parity report pass. |
| WEBVER-02 | 07-13, 07-16 | BLOCKED by CV approval only | Current ledger is reproducible and all 14 non-CV gates pass; release readiness is false solely because `cv-approval` fails. |

All 16 required IDs are claimed by plans and appear in the generated parity report; no orphaned requirement was found.

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|---|---|---|---|
| — | No unreferenced `TBD`, `FIXME`, or `XXX` markers were found in runtime/test files. | INFO | No debt-marker blocker found. |
| `docs/APPROVED_RELEASES.json`, `models/placeholders/` | Explicit research/placeholder wording and quarantine records | INFO | Intentional policy evidence; validators keep these assets disabled and non-diagnostic. They are not production model substitutions. |

## Human Verification Required

1. **Production CV release review before any release approval.** Supply and independently review the exact ONNX model, labels, manifest, hashes, preprocessing/golden parity, field/OOD evidence, agronomist review, redistribution terms, and rollback release. Until that review changes the approval record, the current `cv-approval` failure and production fail-closed behavior are correct.

## Gaps Summary

The previously reported non-CV gaps are closed. The manifest is fully hashed, contract fixtures pass, the actual Nginx path is named by Plan 07-11, the checksummed release ledger is current, the generated parity report passes its reproducibility check, the real browser prototype upload has been exercised, and the Docker prototype overlay has served real ONNX inference after the latest API settings regression fix. The prototype request is implemented: the installed research checkpoints and ONNX candidate are integrity-verified, exposed through authenticated API routes, and wired into the web UI with non-diagnostic wording and flags.

One genuine phase-level gap remains: there is no approved distributable production CV release, so CVWEB-01 and dependent release readiness WEBVER-02 cannot pass. This is an intentional fail-closed release boundary, not permission to promote the research models. No parent source tree was edited by this verification run.

---

_Verified: 2026-09-19T06:18:00Z_  
_Verifier: the agent (gsd-verifier)_
