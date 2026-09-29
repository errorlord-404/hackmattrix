# Chat-first sensor + crop-image assessment implementation plan

**Status:** implementation-ready prototype plan  
**Target:** the existing FastAPI + `kisansathi` FastMCP + farmer chat architecture  
**Primary prototype provider:** `crop.health` behind a provider-neutral backend adapter  
**Important boundary:** this feature produces screening candidates and evidence-guided next steps, not a definitive diagnosis, pesticide prescription, or fertilizer dose.

## 1. Outcome

A farmer should be able to stay inside the existing chat and say that a crop has a problem. The agent will:

1. Resolve the exact field and recorded crop inside the launcher-selected local farmer namespace. `X-Farmer-ID` is local-demo namespace selection, not production authentication.
2. Read the latest field observations, including moisture, temperature, pH, EC, nitrogen, phosphorus, and potassium.
3. Preserve whether each observation came from real hardware, a lab/Soil Health Card, farmer entry, or the Tomato simulator.
4. Ask the farmer for a close photo, a wider photo, or the underside of the leaf when required.
5. After the farmer supplies the image and consents to provider processing, call a crop-health assessment tool through the existing MCP server.
6. Let FastAPI send the image to the configured visual provider, normalize its candidates, snapshot the relevant field evidence, and produce descriptive consistency notes without changing the provider's ranking.
7. Return a differential result with supporting evidence, contradictions, missing evidence, freshness, provenance, and a safe next step.
8. Ask for another photo or recommend expert inspection when the result is ambiguous, stale, out of scope, or inconsistent.

The UI remains a conversation. There is no separate disease form that the farmer must understand or manually coordinate with sensor screens.

## 2. Current-state assessment

### What is already correct

- `agent/src/kisansathi_agent/server.py` already exposes one farmer-scoped FastMCP server. A second MCP server is unnecessary.
- `get_latest_field_observations(field_id)` already reads the canonical backend endpoint instead of reading SQLite directly.
- `get_soil_health(field_id)` already returns latest soil tests, observations, screening recommendations, and provenance.
- The Tomato simulator is field-scoped and disabled by default. When enabled, it writes source-labelled observations into the same `sensor_readings` table used by the normal observation path.
- The simulator covers moisture, temperature, pH, EC, N, P, and K, and marks its source as `simulation:tomato-demo:v1`.
- `get_tomato_demo(field_id)` exposes simulator status without presenting it as hardware evidence.
- The device-ingestion schema already restricts measurement names and validates the expected units.
- `/v1/diagnoses` already validates image type/signature and size, stores the farmer-scoped image, records a checksum, applies idempotency, calls a provider service, and persists the result.
- `get_diagnosis` and diagnosis feedback are already farmer-scoped.
- The system prompt already requires exact field resolution, crop confirmation, photo-quality guidance, sensor provenance, and conservative handling of model output.

Focused verification on 25 September 2026 passed:

```text
python -m pytest backend/tests/test_tomato_demo.py backend/tests/test_crop_health.py agent/tests/test_tools.py -q
27 passed
```

### Gaps to close

1. `backend/app/services/crop_health.py` supports local model variants but has no hosted provider adapter.
2. Image diagnosis and sensor retrieval are separate operations; the persisted diagnosis does not bind the exact observations used for the assessment.
3. The current `diagnose_crop` MCP tool accepts raw base64. Large image bytes should be staged by the trusted chat host and referenced with a farmer-scoped opaque upload ID.
4. The current root upload endpoint immediately performs inference. For an agent-initiated workflow, storage and assessment must be separable.
5. No context service currently binds visual candidates to sensor freshness, units, source, crop stage, weather, recent irrigation, or recent chemical application. The first version must be descriptive only; causal agronomic rules require a separately reviewed rule pack.
6. The result contract has candidates and limitations but lacks a structured sensor snapshot, supporting/contradicting evidence, consent/provider disclosure, and follow-up capture requests.
7. A visual-provider confidence must not be arithmetically combined with uncalibrated sensor readings into a fabricated “overall confidence.”

## 3. Architecture decision

Extend the current `kisansathi` MCP server. Do not create another MCP process.

```text
Farmer chat
  |
  | problem description
  v
KisanSathi agent
  |-- get_field / crop timeline
  |-- get_latest_field_observations
  |-- get_soil_health / weather when relevant
  |-- asks farmer for photo and provider consent
  v
Trusted chat media upload
  |-- validates JPEG/PNG/WebP and size
  |-- stores farmer-scoped private media
  |-- returns opaque upload_id + checksum
  v
MCP: assess_crop_problem(upload_id, field_id, confirmed_crop, symptoms...)
  v
FastAPI assessment service
  |-- verifies farmer/field/upload ownership
  |-- snapshots sensor + soil + crop-stage evidence
  |-- calls configured visual provider adapter
  |-- normalizes candidates
  |-- applies bounded evidence rules
  |-- persists assessment and provenance
  v
MCP structured result
  v
Agent explains differential, conflicts, missing evidence and next step
```

FastAPI remains the domain authority. MCP performs typed transport only. The LLM coordinates the conversation but does not hold provider keys, read files, query SQLite, invent measurements, calculate an uncalibrated composite probability, or decide chemical dosage.

## 4. Provider module

### Interface

Create a provider-neutral interface under `backend/app/services/crop_health_providers/`:

```python
class CropHealthProvider(Protocol):
    provider_id: str

    async def assess(
        self,
        *,
        image_paths: list[Path],
        confirmed_crop: str | None,
        locale: str,
        request_id: str,
    ) -> ProviderAssessment:
        ...
```

`ProviderAssessment` must normalize:

- `status`: `completed | inconclusive | provider_unavailable | needs_expert_review`
- provider/model/version identity when supplied
- top candidates with provider-native probability or score
- crop candidates when supplied
- symptom descriptions and representative-image/source URLs when licensed
- provider warnings and raw-response schema version
- request time, latency, provider request ID, and retryability

### Async execution boundary

Make the provider dispatcher explicitly asynchronous:

```python
async def assess_crop_health(...) -> ProviderAssessment:
    ...
```

- Await hosted HTTP providers directly with an async client.
- Wrap only local CPU/TFLite/registry inference in `asyncio.to_thread`.
- Change `/v1/diagnoses` and `/v1/crop-health/assessments` to await this service instead of wrapping the dispatcher itself in `to_thread`.
- Add a test that fails if a hosted provider coroutine is returned without being awaited, plus a concurrency test proving local inference is moved off the event loop.

### Implementations

1. `KindwiseCropHealthProvider` for the tomorrow prototype.
2. `LocalCropHealthProvider` wrapping the existing local hierarchical/TFLite/registry logic.
3. `UnconfiguredCropHealthProvider` preserving the current fail-closed behavior.
4. `RecordedFixtureCropHealthProvider` for an explicitly selected offline stage demo. It returns a result only when the uploaded SHA-256 exactly matches a fixture manifest. Its provider ID is `fixture:recorded-demo`; it is never an automatic fallback for an arbitrary upload.

Selection remains server-side through `DIAGNOSIS_PROVIDER`. Proposed configuration:

```text
DIAGNOSIS_PROVIDER=kindwise_crop_health
KINDWISE_CROP_HEALTH_API_KEY=
KINDWISE_CROP_HEALTH_BASE_URL=
KINDWISE_CROP_HEALTH_TIMEOUT_SECONDS=20
KINDWISE_CROP_HEALTH_LANGUAGE=en
KINDWISE_CROP_HEALTH_MAX_IMAGES=3
```

The API key must never appear in MCP arguments, browser code, stored provider output, logs, or chat history. Keep the provider endpoint configurable rather than hard-coding an undocumented URL. Redact response headers and provider secrets before persistence.

Before writing the adapter, capture the exact current contract from the official [crop.health documentation](https://crop.kindwise.com/docs) in `backend/docs/provider-contracts/kindwise-crop-health.md`. This is a pre-flight gate and must record the endpoint paths, authentication mechanism, image encoding/limits, crop and language hints, response fields, quota/error bodies, provider request ID, deletion/retention behavior, and redacted success/failure fixtures.

Add and pin `httpx` in `backend/requirements.txt` rather than relying on a transitive test dependency. Use a layered timeout budget: provider request no more than 20 seconds, backend operation no more than 25 seconds, and browser/MCP caller at least 35 seconds. Diagnostics report `unconfigured` when the base URL or key is absent; do not implement against a guessed endpoint.

### Provider behavior

- Send the image and confirmed crop when the provider supports crop hints.
- Do not send farmer identity, field ID, full sensor history, or exact location unless a separately reviewed provider purpose requires it.
- Retry only safe transient failures and respect idempotency/provider semantics.
- Convert timeout, quota, authentication, schema drift, and upstream 5xx responses into typed unavailable states.
- Store the normalized response and a bounded redacted provider payload for audit.
- Never copy provider treatment text directly into the final farmer recommendation. Treat it as untrusted reference content requiring applicable official verification.

## 5. Private media handoff

### Target contract

Split trusted upload from provider assessment:

```text
POST /v1/media/images
Content-Type: image/jpeg | image/png | image/webp
X-Field-ID: <farmer-owned field>

-> {
  "upload_id": "opaque UUID",
  "field_id": "...",
  "mime_type": "image/jpeg",
  "size_bytes": 123456,
  "sha256": "...",
  "created_at": "...",
  "expires_at": "...",
  "status": "stored_private"
}
```

The root application can adopt the already-established `Kisan Sathi Web` concept of an opaque `upload_id`. The upload record is farmer-scoped and cannot accept an arbitrary path from the model.

The chat host attaches only this small metadata object to the agent turn. The image bytes never enter the LLM tool arguments. Keep the existing multipart `/v1/diagnoses` endpoint temporarily for UI compatibility, but route it internally through the same staging and assessment services.

The current `src/context/AIConversationContext.jsx` sends the file immediately to `/v1/diagnoses` and then separately to Codex image processing. That must change before a hosted provider is enabled:

1. Stage the file privately without inference.
2. Show separate processing purposes for crop.health and Codex/conversation-model visual inspection.
3. Let the farmer approve either or both; declining Codex vision must not prevent provider-only assessment.
4. Persist provider, purpose, notice version, decision and decision time server-side. A model-supplied boolean alone is not proof of consent.
5. Start each approved external operation only after the host records the decision.

If opaque staging cannot be finished for the hackathon, the minimum acceptable fallback is a host confirmation dialog before `farmStateApi.createDiagnosis`, with the same server-validated consent record. Prompt text alone is insufficient.

## 6. Context snapshot and descriptive evidence

Create `backend/app/services/crop_assessment_context.py` and `backend/app/services/crop_assessment_evidence.py`.

### Snapshot inputs

For the exact `field_id`, capture:

- current crop and active crop-cycle stage
- symptom onset, affected plant part, spread and recent inputs supplied by the farmer
- latest moisture, temperature, humidity, pH, EC, N, P and K
- value, canonical unit, device/source, confidence, observed time, fetched time and freshness for every measurement
- most recent soil/lab test separately from live sensor readings
- simulator state and source label when active
- recent irrigation event
- relevant recent/forecast weather when available
- provider result and image checksum

Persist the immutable snapshot used for that assessment. A later sensor tick must not silently change the evidence attached to an earlier answer.

### Descriptive evidence policy

The tomorrow implementation produces `context`, `possible_consistency`, `missing`, and `warning` entries. It does not confirm, downgrade, rerank, or contradict a disease candidate using generic sensor thresholds. Multiple stresses may coexist.

Examples:

- Reject moisture as decision evidence when its unit is not `%`.
- Mark readings stale using measurement-specific freshness policies.
- Treat `simulation:*` as demonstration evidence and label it in every response.
- Treat NPK sensor values as screening evidence unless device calibration and placement are known.
- Keep lab/Soil Health Card values distinct from live sensor values.
- Report high EC as a soil-condition observation only unless a crop/stage/device-specific reviewed rule exists.
- Report moisture and humidity as field context; dry conditions do not contradict a visual disease candidate.
- Report a low-N reading and compatible farmer-reported symptoms separately; do not confirm nutrient deficiency or determine a fertilizer dose.
- A recent herbicide/pesticide application can support chemical injury only as farmer-reported context.
- A visual disease candidate that conflicts with crop, organ, stage, or symptom distribution must be downgraded to review, not silently overridden.
- Provider disagreement, unknown crop, poor image quality, unsupported class, mixed symptoms, or missing fresh context leads to recapture or expert review.

Do not call the result “optimized treatment.” Call it an `evidence-guided assessment` or `screening recommendation` until crop-specific agronomic decision rules are validated.

Later rule-based interpretation requires a versioned, expert-reviewed rule pack keyed by crop, stage, measurement, canonical unit, soil/sampling method and device class, with citations, calibration requirements, effective dates and boundary tests. No generic hard-coded NPK, EC or moisture threshold may change a visual candidate.

## 7. Assessment API contract

Add a new backend endpoint while keeping compatibility:

```text
POST /v1/crop-health/assessments
```

Request:

```json
{
  "upload_ids": ["upload-uuid"],
  "field_id": "field-uuid",
  "confirmed_crop": "tomato",
  "affected_part": "older leaves",
  "onset": "three days ago",
  "spread": "about one quarter of the field",
  "recent_inputs": "no spray in the previous week",
  "consent_receipt_id": "opaque-host-issued-receipt",
  "locale": "en-IN"
}
```

Response:

```json
{
  "assessment_id": "assessment-uuid",
  "status": "needs_confirmation",
  "field_id": "field-uuid",
  "crop": "tomato",
  "visual": {
    "provider": "kindwise_crop_health",
    "candidates": [
      {"label": "early blight", "score": 0.81}
    ],
    "limitations": []
  },
  "context_snapshot": {
    "observations": [
      {
        "measurement": "moisture",
        "value": 76.0,
        "unit": "%",
        "source": "simulation:tomato-demo:v1",
        "observed_at": "...",
        "freshness": "fresh",
        "evidence_grade": "simulated_demo"
      }
    ]
  },
  "evidence": {
    "context": [],
    "possible_consistency": [],
    "missing": ["leaf underside photo"],
    "warnings": ["Simulated sensor values are not field measurements."]
  },
  "follow_up_requests": [
    "Upload a focused photo of the underside of an older affected leaf."
  ],
  "safe_next_steps": [
    "Separate and inspect several affected leaves; obtain local expert confirmation before changing crop protection inputs."
  ],
  "provenance": [],
  "created_at": "..."
}
```

Never return a combined numeric confidence unless it has been trained and calibrated on an independent field dataset. Keep visual scores and context evidence separate.

## 8. MCP tool design

Register one new composite tool on the existing server:

```python
assess_crop_problem(
    upload_ids: list[str],
    field_id: str,
    confirmed_crop: str,
    consent_receipt_id: str,
    affected_part: str | None = None,
    onset: str | None = None,
    spread: str | None = None,
    recent_inputs: str | None = None,
    locale: str = "en-IN",
)
```

Properties:

- The model supplies only opaque upload IDs and domain context—never base64, filesystem paths, farmer IDs, provider URLs, keys, thresholds, or policy controls.
- The trusted host—not the model—creates the opaque consent receipt. It is bound to upload ID, provider, purpose, notice version, decision and timestamp.
- Mark it as a provider/write operation because it transmits media externally and persists an assessment.
- Require immediate farmer confirmation before provider transmission.
- Use an idempotency key derived from upload checksums, field, crop and the relevant context—not raw image bytes.
- Preserve `provider_unavailable`, `inconclusive`, `needs_crop_confirmation`, `needs_recapture`, and `needs_expert_review` states.
- Both assessment routes reject a missing, declined, expired, replayed, mismatched-upload, mismatched-provider, or mismatched-purpose consent receipt. Add focused mismatch and replay tests.
- Retain `get_diagnosis` for reading a saved record and `submit_diagnosis_feedback` for later feedback.
- Deprecate direct model-facing `diagnose_crop(image_base64=...)` after UI and contract migration.

The agent may still call `get_latest_field_observations`, `get_soil_health`, `get_weather_for_field`, and `list_device_health` before assessment so it can ask better questions. The authoritative response, however, must contain the immutable snapshot captured server-side.

## 9. Conversation policy

Update the farmer prompt and KisanSathi skill with this state machine:

```text
problem reported
  -> resolve exact field
  -> confirm crop and affected part
  -> inspect latest sensor/soil freshness
  -> ask for required photo views
  -> explain external image processing and obtain confirmation
  -> call assess_crop_problem
  -> explain visual candidates separately from sensor evidence
  -> ask at most two high-value follow-up questions
  -> retrieve an applicable official advisory when making material advice
  -> return safe next action or expert escalation
```

Required conversational behavior:

- If no image is attached: ask for one close, well-lit photo and optionally a wider view/underside.
- If several fields match: ask the farmer to choose; never guess.
- If the crop is unknown: ask for confirmation; do not route a crop-specific assessment silently.
- If readings are missing/stale: say so and do not fabricate them.
- If values are simulated: say “simulated demo data” in the answer and spoken summary.
- If visual and sensor evidence disagree: describe the disagreement.
- If the provider is down: preserve the uploaded evidence and offer retry or expert review; do not default to healthy.
- No pesticide, herbicide, fungicide or fertilizer product/dose is selected from the provider response alone.

## 10. File-level work plan

### Wave 1 — provider and normalized contracts

Files:

- `backend/app/core/config.py`
- `backend/.env.example`
- `backend/app/services/crop_health.py`
- `backend/app/services/crop_health_providers/__init__.py`
- `backend/app/services/crop_health_providers/base.py`
- `backend/app/services/crop_health_providers/kindwise.py`
- `backend/app/services/crop_health_providers/local.py`
- `backend/app/schemas/farm_state.py`
- `backend/tests/test_crop_health_provider.py`
- `backend/tests/test_crop_health.py`

Tasks:

1. Define provider-neutral request/result types.
2. Move existing local-provider branching behind the interface without changing fail-closed behavior.
3. Add the crop.health adapter, timeouts, bounded response parsing, redaction, and typed failure mapping.
4. Add configuration and diagnostics that expose readiness but never the key.
5. Add golden provider fixtures for completed, ambiguous, quota, timeout, invalid-schema and authentication failures.

Verification:

- No network call in unit tests.
- Secrets are absent from logs and persisted payloads.
- Existing local-provider tests remain green.
- Provider failure never becomes `healthy` or a fabricated candidate.

### Wave 2 — media staging, consent, persistence migration and evidence snapshot

Files:

- `backend/app/farm_state/store.py`
- `backend/app/routers/assistants.py`
- `backend/app/services/crop_assessment_context.py`
- `backend/app/schemas/farm_state.py`
- `src/context/AIConversationContext.jsx`
- `src/api/farmStateApi.js`
- `backend/tests/test_assessment_media.py`
- `backend/tests/test_crop_assessment_context.py`
- `backend/tests/test_farm_state_migrations.py`

Tasks:

1. Add local-namespace-scoped upload staging with opaque IDs, checksum, MIME, size and retention state.
2. Prevent arbitrary paths and cross-namespace/cross-field upload reuse within the local demo boundary.
3. Add assessment, consent and evidence-snapshot persistence using a schema-v2 migration, not only changes to the `CREATE TABLE IF NOT EXISTS` block. Add `media_uploads`, `media_processing_consents`, `crop_health_assessments`, and `crop_health_evidence_snapshots` tables plus field/status/checksum indexes. Test a v1 database upgrade in place.
4. Read the newest value per measurement using the existing canonical route/query behavior.
5. Record source, unit, confidence and timestamps; keep soil tests and sensors distinct.
6. Keep the existing `/v1/diagnoses` path as a compatibility wrapper.
7. Define a short demo retention period, enforce expiry on access, and run a startup/maintenance sweep that removes expired rows and physical files. Add an explicit deletion path for farmer requests; failed and unavailable assessments follow the same policy.
8. Change `AIConversationContext.jsx` so selection stages first and neither crop.health nor `window.kisanHarness.chat.sendImage` runs until its purpose has been approved.

Verification:

- One launcher-selected local namespace cannot assess an upload or field from another namespace.
- A staged upload cannot be assessed after expiry/deletion.
- Expiry removes both metadata and the physical file.
- The stored checksum matches the assessed image.
- A later simulator tick does not mutate a saved assessment snapshot.
- Separate crop.health and Codex-processing decisions are persisted and enforced.

### Wave 3 — descriptive context evidence and assessment route

Files:

- `backend/app/services/crop_assessment_evidence.py`
- `backend/app/routers/assistants.py`
- `backend/app/schemas/farm_state.py`
- `backend/tests/test_crop_assessment_evidence.py`
- `backend/tests/test_assistants.py`

Tasks:

1. Implement typed context items and measurement freshness policies.
2. Add unit, source, simulator and calibration-state reporting without modifying provider rankings.
3. Add `/v1/crop-health/assessments` with idempotency and consent enforcement.
4. Persist the normalized visual result and exact context snapshot.
5. Produce follow-up capture requests and expert-review states.

Verification scenarios:

- fungal candidate + fresh high-moisture context reported separately
- visual disease candidate + severe low moisture coexisting without false contradiction
- nutrient-like symptoms + low-N simulated context explicitly labelled unconfirmed
- salinity-like symptoms + high EC reported as context rather than diagnosis
- stale NPK values
- incorrect units
- missing image
- multiple conflicting provider candidates
- unsupported crop and unrelated image
- provider outage

### Wave 4 — MCP tool and contracts

Files:

- `agent/src/kisansathi_agent/tools.py`
- `agent/src/kisansathi_agent/server.py`
- `agent/contracts/farmer_ui_tool_parity.json`
- `agent/tests/test_tools.py`
- `Kisan Sathi Web/packages/tool-registry/workflows/kisansathi.yaml` if the standalone registry is the active demo runtime

Tasks:

1. Add `assess_crop_problem` with bounded string/list fields and no identity/path/key arguments.
2. POST only the typed assessment payload to FastAPI.
3. Preserve all backend statuses, provenance, warnings and request IDs.
4. Mark it as a provider/write tool requiring confirmation.
   Add a distinct `_EXTERNAL_WRITE` annotation with `readOnlyHint=False`, `destructiveHint=False`, `openWorldHint=True`, and an `idempotentHint` matching the backend/provider contract. Do not reuse `_WRITE`, which currently declares `openWorldHint=False`.
5. Retain read-only diagnosis inspection and feedback tools.
6. Plan the later removal of raw `image_base64` from model-facing contracts.

Verification:

- Exact HTTP path, headers, payload and idempotency behavior are asserted.
- Tool schema cannot accept farmer identity, arbitrary URL/path, API key, threshold or treatment override.
- Oversized tool results remain bounded without dropping safety warnings.
- Provider and backend errors retain typed codes and retryability.

### Wave 5 — chat UX and agent workflow

Files:

- `agent/prompts/farmer_system_prompt.md`
- `agent/skills/kisansathi/SKILL.md`
- `agent/skills/kisansathi/references/farm-lifecycle-workflow.md`
- `src/components/features/ai/ConversationView.jsx`
- `src/context/AIConversationContext.jsx`
- `src/api/farmStateApi.js`
- `desktop/codex-harness.cjs` only if attachment metadata or approval transport requires a host change
- associated frontend and harness tests

Tasks:

1. Let the agent request a photo naturally in chat.
2. Stage selected/captured images and inject only `upload_id`, field binding, checksum and MIME metadata into the agent turn.
3. Show upload, analyzing, inconclusive, unavailable, recapture and expert-review states in conversation.
4. Make external-provider disclosure and consent visible before assessment.
5. Render visual candidates separately from sensor/context evidence.
6. Always show source/freshness and a “Simulated demo data” badge where applicable.
7. Make the spoken farmer summary preserve uncertainty and the immediate next action.

Verification:

- The complete flow works without leaving chat.
- The agent asks for an image when none is supplied.
- The image is not sent to the provider before confirmation.
- Refresh/resume can reload the assessment by ID.
- A provider outage does not erase the upload or sensor context.

### Wave 6 — documentation, demo fixtures and end-to-end gate

Files:

- `backend/ChangeLog.md`
- `backend/Decisions.md`
- `backend/Flow.md`
- `docs/sih26180/` demo runbook
- API/MCP contract fixtures
- end-to-end chat tests

Tasks:

1. Update required backend memory files.
2. Add an explicit `recorded_fixture` provider mode for offline continuity. Bind every result to an exact known image SHA-256 and manifest; never replay it for an unmatched image or silently fall back from a live provider.
3. Prepare five demo scenarios: balanced/healthy, likely foliar disease, water stress, nitrogen stress, salinity risk, plus one inconclusive image.
4. Record provider/model identity, API availability, and simulator status in diagnostics.
5. Run backend, agent and frontend verification suites.

## 11. Tomorrow prototype cut

If only one day is available, implement this vertical slice:

1. Complete the official provider-contract preflight, pin `httpx`, and add the async crop.health adapter behind `DIAGNOSIS_PROVIDER`.
2. Limit the first cut to crop.health processing. Do not send the image to Codex vision; `AIConversationContext.jsx` must omit `window.kisanHarness.chat.sendImage` for this path.
3. Add one host-side crop.health disclosure and approval. Persist a server-issued consent receipt bound to upload checksum, provider, purpose and notice version before calling `/v1/diagnoses`.
4. Make `/v1/diagnoses` reject absent, declined, expired or mismatched consent and snapshot the latest observations for its `field_id` before calling the provider.
5. Persist and return `context_snapshot`, descriptive `evidence`, and `limitations` in `DiagnosisResponse`.
6. Have the agent ask for the image and read the saved record through `get_diagnosis`; the agent never resubmits image bytes.
7. Update the prompt so it first calls `get_latest_field_observations`, asks for the image, and explains the saved visual candidates separately from the immutable sensor snapshot.
8. Add mocked provider, consent-mismatch and one end-to-end demo test.
9. Add one operator-selected, checksum-bound recorded fixture for presentation continuity.

This cut does not yet add Codex image inspection, remove base64 from the legacy direct MCP tool, or expose the new composite tool. The opaque-upload/composite-tool design and separate Codex-processing consent follow immediately after the demo.

## 12. Acceptance criteria

- A farmer can start with “my tomato plants have yellow spots” and complete the workflow without opening another page.
- The agent identifies one exact field and retrieves current field observations before interpreting the problem.
- The farmer is asked for an appropriate photo and is told when more views are needed.
- No crop.health or Codex image transmission occurs without a purpose-specific host confirmation recorded server-side.
- The visual API is called only by FastAPI; no browser or MCP argument contains its key.
- The result binds an immutable image checksum and immutable context snapshot.
- Moisture, temperature, pH, EC, N, P and K retain value, unit, source, time, freshness and evidence class.
- Simulator values are unmistakably labelled and never described as hardware measurements.
- Visual candidates and sensor evidence remain separate; no fabricated combined confidence is emitted.
- Missing, stale, invalid-unit, conflicting and unavailable cases return explicit degraded states.
- The system never emits a pesticide/fertilizer product or dose solely from image/API/sensor inference.
- Backend, MCP and UI tests cover the happy path, provider outage, local namespace isolation, stale sensors, simulated data, invalid image, consent denial, expired media and expert escalation.

## 13. Implementation order and dependency map

```text
Wave 1 provider interface
   |
   +--> Wave 2 upload + snapshots
            |
            +--> Wave 3 fusion + assessment endpoint
                      |
                      +--> Wave 4 MCP tool
                                |
                                +--> Wave 5 chat UX
                                          |
                                          +--> Wave 6 E2E/demo gate
```

For the hackathon, Waves 1 and the narrow parts of Waves 2, 3 and 5 form the smallest working slice. Do not start with new model training, a second MCP process, or a large crop-specific model registry.
