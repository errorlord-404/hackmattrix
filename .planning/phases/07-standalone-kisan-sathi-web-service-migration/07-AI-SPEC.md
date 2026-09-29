# AI-SPEC — Phase 7: Hierarchical crop vision for standalone Kisan Sathi Web

> AI design contract generated through `$gsd-ai-integration-phase`. This
> extends the existing Phase 7 web-migration contract without approving model
> artifacts or bypassing Plan 07-02.

---

## 1. System Classification

**System Type:** Hybrid computer-vision screening and conversational orchestration

**Description:** A farmer submits a crop image. An approved compact CNN first
identifies the crop, uncertain routes require farmer confirmation, and an
approved crop-specific CNN then screens for a bounded disease label set. The
browser is the preferred inference location; the API supplies the same-model
server fallback and remains authoritative for ownership, release revalidation,
persistence, and expert escalation. The LLM explains persisted results but
does not perform or upgrade the visual diagnosis.

**Critical Failure Modes:**

1. Running the wrong crop specialist after an uncertain identifier result.
2. Treating an ImageNet backbone, dataset, research checkpoint, or browser
   candidate as an approved disease diagnosis.
3. Returning a confident known class for blur, wrong crops, unlisted disease,
   nutrient/water stress, pests, soil, hands, or other OOD inputs.
4. Browser/server preprocessing or quantization drift changing the result.
5. Allowing a visual output to authorize pesticide, fertilizer, purchase,
   payment, machinery, or irrigation actions.

---

## 1b. Domain Context

**Industry Vertical:** Agriculture / crop-health decision support

**User Population:** Indian farmers using variable mobile devices, bandwidth,
lighting, languages, crop varieties, and field conditions; agronomists review
labels, release evidence, and escalated cases.

**Stakes Level:** High

**Output Consequence:** A screening result can influence scouting and expert
consultation. It must not independently prescribe or actuate treatment.

### What Domain Experts Evaluate Against

| Dimension | Good | Bad | Stakes | Source |
|---|---|---|---|---|
| Crop routing | Correct crop or explicit confirmation request | Silent wrong specialist | High | Agronomist-reviewed field set |
| Disease recall | Released classes meet per-class gate | Minority/severe class missed | High | Field/date-held-out set |
| Unknown rejection | Wrong crop/stress/poor image rejected | Forced disease label | Critical | OOD challenge set |
| Evidence scope | Crop, variety, location, stage and limitations stated | Controlled-data score called field accuracy | High | Model card and datasheet |
| Cross-runtime parity | Browser and server match within tolerance | Runtime-dependent label changes | High | Golden tensor/image fixtures |

### Known Failure Modes in This Domain

- Models learn controlled backgrounds instead of lesions.
- Random image splits leak near-duplicate leaves across train and test.
- Similar symptoms arise from disease, pests, water stress, nutrient stress,
  chemical injury, senescence, and weather damage.
- A router trained on a narrow crop list gives high softmax confidence to an
  unsupported crop.
- Variety, growth stage, season, phone camera, and region shift performance.
- Quantization can reduce minority-class recall even when overall accuracy
  appears stable.

### Regulatory / Compliance Context

No crop-image classifier-specific Indian certification was identified in this
bounded research. Privacy, consent, data-retention, pesticide-label law, and
agronomic accountability still apply. This system is screening support and
must preserve review, provenance, limitations, and deletion controls.

### Domain Expert Roles for Evaluation

| Role | Responsibility |
|---|---|
| Plant pathologist | Disease taxonomy, ambiguous labels, failure review |
| Crop agronomist | Variety/stage/context coverage and safe next actions |
| Field data steward | Consent, provenance, field/date split integrity |
| ML release reviewer | Calibration, OOD, quantization, parity and rollback gates |

---

## 2. Framework Decision

**Selected Framework:** ONNX Runtime Web plus ONNX Runtime CPU

**Version:** Exact `onnxruntime-web` and server runtime versions remain locked
behind the Plan 07-02 approval record. The researched web candidate was 1.30.0;
it must not enter a dependency lock until the exact package and artifacts are
recorded and validated.

**Rationale:** ONNX provides one portable release artifact for browser WASM,
optional WebGPU, and lightweight server CPU fallback. WASM has broad browser
coverage; WebGPU can accelerate supported Chromium devices. A shared artifact
reduces preprocessing and label drift. The specialist-per-crop design enables
lazy loading and independent updates without retraining every crop.

**Alternatives Considered:**

| Framework | Ruled Out Because |
|---|---|
| TensorFlow.js | Viable, but would create a second runtime/export path beside the planned ONNX server fallback. |
| LiteRT/TFLite in browser | Strong mobile runtime, but browser support and packaging are less direct than ORT Web for this web-first phase. |
| TorchVision/PyTorch server only | Easier training, but uploads every image and does not meet client-first/offline goals. |
| One universal disease model | Smaller operational catalog, but routes unrelated crops/classes together and scales poorly for local validation and rollback. |
| Large vision foundation model | Too heavy for broad client hardware; research features do not equal a calibrated disease head. |

**Vendor Lock-In Accepted:** Partial. Runtime APIs use ONNX Runtime, while the
release contract, model artifacts, labels, preprocessing, and evaluation data
remain provider-neutral and replaceable.

---

## 3. Framework Quick Reference

### Installation

```bash
# Run only after Plan 07-02 records the exact approved version.
npm install --save-exact onnxruntime-web@<approved-version>
python -m pip install onnxruntime==<approved-version>
```

### Core Imports

```javascript
import * as ortWasm from 'onnxruntime-web/wasm';
import * as ortWebGpu from 'onnxruntime-web/webgpu';
```

```python
import onnxruntime as ort
```

### Entry Point Pattern

```javascript
const providers = supportsWebGpu ? ['webgpu', 'wasm'] : ['wasm'];
const session = await ort.InferenceSession.create(verifiedModelBytes, {
  executionProviders: providers,
});
```

### Key Abstractions

| Concept | What It Is | When You Use It |
|---|---|---|
| InferenceSession | Loaded ONNX graph and selected providers | One cached session per approved model version |
| Execution provider | WASM CPU or WebGPU accelerator | WebGPU opportunistically, WASM as baseline |
| Release descriptor | Signed model/labels/preprocessing/hash metadata | Before fetching or creating any session |
| Router result | Crop candidates plus acceptance/margin evidence | Before selecting a specialist |
| Specialist result | Bounded disease candidates plus all gates | Candidate only until API revalidation |

### Common Pitfalls

1. WebGPU is not universally available; fallback must be deterministic.
2. WASM/worker assets must be served from correct CSP-compatible paths.
3. Preprocessing order, interpolation, channel order, and normalization must be
   generated from the manifest, not duplicated in browser and server code.
4. Model downloads should use immutable URLs and verified hashes before cache.
5. Static INT8 is usually appropriate for CNNs, but accuracy and operator
   compatibility must be measured on every artifact.

### Recommended Project Structure

```text
Kisan Sathi Web/
├── packages/browser-vision/       # catalog policy, worker, preprocessing, ORT
├── services/api/app/services/     # server catalog and inference fallback
├── services/api/app/routers/      # descriptor/finalization APIs
├── models/                        # catalog, source ledger, mounted releases
└── tests/                         # golden parity, OOD, browser and failure gates
```

---

## 4. Implementation Guidance

**Model Configuration:** MobileNetV3-Small is the default identifier and
specialist backbone, exported as static INT8 ONNX with a target of <=6 MB per
artifact. EfficientNetV2-B0 is an accuracy benchmark, not a default. Threshold,
margin, OOD, image-quality, crop scope, and labels come only from the manifest.

**Core Pattern:** Identifier → acceptance/margin gate → farmer confirmation if
needed → lazy specialist → quality/confidence/margin/OOD gates → API ownership
and release revalidation → persistence or expert review.

**Tool Use:** The LLM receives only the normalized `diagnose_crop` tool and the
authoritative API result. Model IDs, artifact URLs, credentials, tenant IDs,
and release controls are not model arguments.

**State Management:** Immutable release files live in a read-only mounted model
volume/CDN. Browser cache keys include release ID and hash. API persistence
stores upload hash, crop confirmation, release/hash evidence, gate results,
runtime, limitations, and review status.

**Context Window Strategy:** The LLM sees compact structured candidates and
limitations, never raw tensors, full manifests, or hidden model telemetry.

---

## 4b. AI Systems Best Practices

### Structured Outputs with Pydantic

```python
class CropCandidate(BaseModel):
    label_id: str
    score: float = Field(ge=0, le=1)

class CropHealthResult(BaseModel):
    status: Literal["completed", "needs_crop_confirmation", "needs_expert_review", "unavailable"]
    result_role: Literal["candidate", "authoritative"]
    crop: str | None
    model_id: str
    model_version: str
    candidates: list[CropCandidate]
    review_required: bool
```

Validation failure is terminal for that candidate and routes to server fallback
or expert review. It is never repaired by an LLM guessing missing fields.

### Async-First Design

Model fetch, hashing, worker startup, and server fallback are cancellable. Run
browser inference in a dedicated worker with time and message-size bounds.
Stream only progress states; await final API persistence before showing an
authoritative result.

### Prompt Engineering Discipline

Prompts explain that vision results are bounded screening evidence. They cannot
invent unsupported diseases, alter confidence, hide limitations, or prescribe
treatment. Provider adapters receive the same normalized result contract.

### Context Window Management

Persist images outside conversation history. Use upload references and compact
ranked candidates. Summaries retain release/version, limitations, confirmation,
review state, and next safe action.

### Cost and Latency Budget

Cache the identifier and most recently used specialist. Lazy-load one specialist
at a time. Target p95 browser screening under 2 seconds after cache on agreed
pilot devices; target first-use model download below 12 MB. Server fallback has
bounded concurrency and image size. Actual gates require device measurements.

---

## 5. Evaluation Strategy

### Dimensions

| Dimension | Rubric | Measurement Approach | Priority |
|---|---|---|---|
| Crop routing | Per-crop recall >= release gate; ambiguous cases confirm | Code + field set + human review | Critical |
| Disease quality | Macro-F1 and every released-class recall >= approved gate | Field/date-held-out metrics | Critical |
| Unknown rejection | Wrong crop/OOD true rejection >= approved gate | Dedicated challenge set | Critical |
| Calibration | Reliability/ECE and accepted-error rate within release limit | Code | High |
| Quantization parity | Macro-F1 loss <=2 points and no critical-class regression | FP32 vs INT8 report | Critical |
| Runtime parity | Golden top-k/gates match within tolerance | Browser/server automated tests | Critical |
| Performance | p50/p95 latency, memory, size, thermal within device budget | Device/browser matrix | High |
| Safety wording | No diagnosis authority or treatment authorization | Contract tests + agronomist review | Critical |

### Eval Tooling

**Primary Tool:** Deterministic Python evaluation reports plus pytest and browser
golden tests. Arize Phoenix is not selected because model classification metrics,
artifact parity, and OOD evaluation are the release-critical evidence; LLM
tracing belongs to the separate harness evaluation path.

```bash
python scripts/validate_model_catalog.py --require-approved --crop <crop>
python -m pytest packages/contracts/tests services/api/tests -q
npm --prefix packages/browser-vision test
```

**CI/CD Integration:** Each command emits or consumes checksummed machine-readable
evidence in Phase 07 release gates; no Markdown-only approval is sufficient.

### Reference Dataset

**Size:** Per release, enough independent farms/dates to estimate each class and
unknown rejection; never fewer than 30 field images per released class for an
initial pilot, with the final minimum set by the agronomist/statistical review.

**Composition:** Supported crop/variety/stage/severity, wrong crops, healthy,
unlisted diseases, pests, water/nutrient stress, weeds, soil/hands, blur,
exposure extremes, backgrounds, devices, districts, and seasons.

**Labeling:** Dual agronomist/pathologist review for disease labels, adjudication
for disagreement, and preserved uncertain/other labels. Split by field and date.

---

## 6. Guardrails

### Online (Real-Time)

| Guardrail | Trigger | Intervention |
|---|---|---|
| Artifact integrity | Missing/hash mismatch/expired descriptor | Block local load; server fallback |
| Crop confirmation | Low identifier score or margin | Ask farmer; do not load specialist |
| Quality/OOD | Poor capture or unsupported input | Reject and request recapture/review |
| Release scope | Crop/label not approved | Needs expert review |
| Authority | Any browser candidate | API revalidation before persistence |
| Action safety | Treatment/actuation request from vision result | Block and require reviewed workflow |

### Offline (Flywheel)

| Metric | Sampling Strategy | Action on Degradation |
|---|---|---|
| Accepted wrong predictions | All feedback disagreements | Suspend affected release and rollback |
| Unknown rejection | Stratified OOD sample | Retune/retrain; no silent threshold edit |
| Per-class recall | Crop/region/device slices | Remove failing class or release |
| Runtime drift | Golden fixtures every build | Block deployment |
| Latency/memory | Browser/device telemetry without image content | Change optimization only after parity re-eval |

---

## 7. Production Monitoring

**Tracing Tool:** Structured server audit events and privacy-preserving browser
runtime metrics. Images are not included in traces.

**Key Metrics:** identifier confirmation rate, fallback rate, OOD/quality reject
rate, accepted-result feedback disagreement, per-model latency, load failures,
and active release/hash distribution.

**Alert Thresholds:** Any hash/signature mismatch; any cross-tenant access; any
golden parity failure; accepted-error feedback above the approved bound; p95
latency or crash rate outside the release SLO.

**Smart Sampling Strategy:** Review all safety-gate bypass attempts and user
disagreements, then stratify successful traffic by crop, region, device,
confidence band, OOD score, and runtime. Image review requires consent.

---

## Checklist

- [x] System type classified
- [x] Critical failure modes identified
- [x] Domain context researched
- [x] Regulatory/compliance boundary stated
- [x] Domain expert roles defined
- [x] Framework selected with rationale
- [x] Alternatives considered
- [x] Framework quick reference written
- [x] Structured output, async, prompt, context, and budget practices written
- [x] Evaluation dimensions grounded in domain evidence
- [x] Reference dataset and labeling strategy specified
- [x] CI commands specified
- [x] Online/offline guardrails defined
- [x] Monitoring and sampling strategy defined
- [ ] Exact runtime version and real model release approved in Plan 07-02
