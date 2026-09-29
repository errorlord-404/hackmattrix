---
status: testing
phase: 07-standalone-kisan-sathi-web-service-migration
source: [07-VERIFICATION.md]
started: 2026-09-19T05:31:00Z
updated: 2026-09-19T06:18:00Z
---

## Current Test

number: 3
name: Production CV release review
expected: |
  Only an independently reviewed ONNX/labels bundle with field/OOD evidence,
  agronomist review, redistribution approval, golden parity, and rollback
  identity changes the production approval record.
awaiting: independent release evidence and approval authority

## Tests

### 1. Real authenticated prototype upload
expected: A supported crop image reaches the prototype API and the UI shows a bounded, non-diagnostic research result.
result: passed
evidence: |
  Playwright CLI opened the standalone Vite web app at http://127.0.0.1:5173
  with the local test session. The prototype profile request returned 200, the
  browser POST to /api/v1/crop-disease/predict?crop=tomato returned 200, and
  the Crop health card displayed “Uncertain screening signal”, 32.8% confidence,
  and the controlled-imagery/non-diagnostic warning for the real
  models/crop_disease/downloaded/harimitra/home_page.jpeg fixture.

### 2. Docker prototype deployment
expected: The standalone Compose prototype starts with the verified ONNX candidate mounted read-only and serves a real, bounded non-diagnostic inference.
result: passed
evidence: |
  `docker compose -f deploy/compose.yaml -f deploy/compose.prototype.yaml build api`
  completed successfully. The prototype stack started with healthy API, harness,
  and web containers on ports 8012/8082. A real JPEG POST to the container API
  returned HTTP 200 with status `uncertain`, model `mesabo_resnet50_onnx`,
  framework `onnxruntime`, and the controlled-imagery warning. The prototype
  profile endpoint returned `prototype_available`, one model, and
  `production_approved=false`.

### 3. Production CV release review
expected: The production CV approval record is changed only after the required independent evidence is supplied and validated.
result: pending

## Summary

total: 3
passed: 2
issues: 0
pending: 1
skipped: 0
blocked: 1

## Gaps

- The prototype browser path is verified locally.
- Production release approval remains intentionally fail-closed; research models are not promoted.
