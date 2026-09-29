# AI-SPEC — Crop Model Registry and Training Lifecycle

> Design contract for the model work that must precede Phase 7 Plan 07-10. The release gate remains fail-closed until genuine evidence is registered.

## 1. System Classification

**System type:** Hybrid hierarchical computer-vision classification and governed MLOps lifecycle.

The system trains and evaluates one crop router plus crop-specific disease specialists, exports portable artifacts, and registers immutable releases for browser ONNX Runtime Web and lightweight server inference. Registry inspection must not import an ML framework. Training backends are optional adapters.

**Critical failure modes:**

1. A placeholder, demo, or unreviewed model is activated as diagnostic.
2. Wrong-crop routing produces an authoritative disease result.
3. Unknown, low-quality, or out-of-distribution images receive confident diagnoses.
4. Quantized/browser output diverges materially from the evaluated server candidate.
5. Artifact, label, preprocessing, license, or approval evidence is missing or substituted.

## 1b. Domain Context

**Industry Vertical:** Indian agriculture; farmer-facing crop-health screening for a 15-crop router and crop-specific disease specialists.

**User Population:** Farmers and agricultural/extension advisors submitting variable-quality phone photographs from Indian field conditions.

**Stakes Level:** High. A wrong accepted result can delay field inspection, route the image to the wrong specialist, cause avoidable crop loss, or prompt unnecessary or unsafe input use.

**Output Consequence:** The system may return a non-authoritative crop or disease-screening candidate, or abstain. It must not convert an image classification into a confirmed diagnosis or treatment instruction. Accepted outputs can inform the next observation or expert referral only; ungradable, ambiguous, mixed-symptom, low-confidence, or out-of-scope cases go to recapture or qualified human review.

### What Domain Experts Evaluate Against

**Dimension: Independent field validity**  
**Good (domain expert would accept):** The frozen release is evaluated end to end on farmer-phone images not used for training, tuning, calibration, or threshold selection. Source image/burst, plant, plot/field/farm, collector, and collection date groups do not cross splits; augmented or synthetic descendants remain in the training group. At least one declared external holdout represents unseen farms and relevant agro-climatic zones, seasons, crop stages, varieties, devices, lighting, backgrounds, and disease severities. Report router top-1/top-3 and per-crop recall, routed specialist per-class recall and confusion, confidence intervals, and end-to-end failures; controlled-leaf benchmarks are supporting evidence only.  
**Bad (domain expert would flag):** Random image splits, near-duplicate leaves across folds, tuning on the field test set, a test set dominated by one farm/device, or release claims based on aggregate accuracy from PlantVillage-like controlled imagery.  
**Stakes:** Critical  
**Source:** Project release evidence requirements; Mohanty et al. reported 31.4% accuracy when a controlled-image model was tested on differently sourced images; recent controlled-to-field studies continue to document a substantial reliability gap.

**Dimension: Agronomic label and differential-diagnosis integrity**  
**Good (domain expert would accept):** A versioned taxonomy for all 15 crops is signed off crop by crop by a qualified agronomist or plant pathologist. It distinguishes causal disease labels from symptom-only labels, names synonyms, valid crop organs and growth stages, explicit lookalikes, and exclusions such as nutrient/water stress, herbicide injury, insect damage, and unlisted diseases. Mixed symptoms may be multi-label or marked `mixed_or_ambiguous`; visually inseparable cases require field/laboratory evidence or remain unresolved. The release set is independently reviewed, disagreements are recorded, and a named senior expert adjudicates them before scoring.  
**Bad (domain expert would flag):** Labels copied from folder names without review; incompatible disease and symptom concepts in one class list; bell pepper used as chilli evidence; a single label forced onto mixed symptoms; or a visual label presented as pathogen confirmation when the image cannot establish the differential.  
**Stakes:** Critical  
**Source:** The project taxonomy and research inventory; published PlantDoc analysis documents images with multiple symptoms assigned one label, while rice-disease research shows that one pathogen can produce different symptoms across plant parts.

**Dimension: Safe rejection and escalation**  
**Good (domain expert would accept):** Before release, experts approve separate reject rules and challenge sets for wrong/non-target crops, unlisted disease, healthy-but-ungradable tissue, mixed symptoms, pests and abiotic stress, non-plant content, wrong organ, blur, glare, occlusion, compression, and too-little symptomatic area. Thresholds are fixed without the final test set and evaluated per crop using false acceptance of unknowns, accepted-case error, abstention/coverage, and router-to-specialist cascade errors. Crop disagreement, poor quality, low score/margin, or known-versus-unknown uncertainty produces a neutral abstention with a recapture or expert-review path—not a forced argmax.  
**Bad (domain expert would flag):** Every upload receives one of the known diseases; one global confidence cutoff is assumed safe for all crops/classes; top-3 display substitutes for rejection; or high abstention is hidden to improve accepted-case accuracy.  
**Stakes:** Critical  
**Source:** Plant-disease field-deployment research and the project's unknown/OOD release gate; GSD evaluation guidance treats high-consequence escalation as an online guardrail.

**Dimension: Farmer-safe claim and treatment boundary**  
**Good (domain expert would accept):** The result is phrased as a possible visual match with crop, visible evidence limits, alternative explanations, model/release identity, and a concrete next step. The classifier itself never selects a pesticide, dose, mixture, schedule, fertilizer, or machinery action. Any later treatment workflow is separately governed and must verify the current Indian registration and label for the exact crop-target-product combination, applicable local restrictions, crop stage, precautions, and qualified-human approval.  
**Bad (domain expert would flag):** “Confirmed” disease language from one photograph; reassurance that rules out disease; treatment generated directly from class probability; or an off-label chemical/product/dose recommendation.  
**Stakes:** Critical  
**Source:** PPQS/CIBRC pesticide labels restrict use to specified crops and directions; project policy defines model results as screening candidates without treatment authority.

**Dimension: Lawful, auditable data and release authority**  
**Good (domain expert would accept):** Every training, calibration, and evaluation image has traceable source, parent/duplicate group, collection context, rights holder, license or written permission, allowed training/redistribution scope, and integrity hash. Farmer submissions document purpose, retention/deletion, access, and consent or other valid basis where the image or metadata is personal data; unnecessary faces, vehicle plates, account identifiers, and precise location are removed or access-controlled. Automated checks may verify required fields, hashes, split isolation, metric calculations, thresholds, runtime parity, and presence of approvals. Only named human reviewers may validate rights/consent, taxonomy, field representativeness, ambiguous ground truth, treatment claims, and final release approval.  
**Bad (domain expert would flag):** “Publicly available” treated as permission; Kaggle/GitHub provenance standing in for the original license; one consent reused for an undisclosed purpose; personal metadata retained by default; or a passing script/LLM judge creating or implying agronomic approval.  
**Stakes:** Critical  
**Source:** Project release policy; India's Digital Personal Data Protection Act, 2023 and phased Digital Personal Data Protection Rules, 2025 where digital personal data is processed; GSD human-evaluation guidance.

### Known Failure Modes in This Domain

- **Shortcut success that collapses in fields:** uniform backgrounds, detached leaves, source watermarks, or acquisition style become class cues; random splits leak the same plant, burst, farm, or augmented parent and inflate performance.
- **Cascade amplification:** a plausible wrong-crop route invokes the wrong specialist, whose closed label set can still emit a confident disease; per-model scores hide the end-to-end harm.
- **Non-unique or mixed symptom expression:** cultivar, crop stage, plant organ, severity, co-infection, pest damage, nutrient/water stress, and chemical injury can share visual signs or produce several signs in one frame; forced single labels corrupt both training and evaluation.
- **Unknown and capture shift forced into known classes:** unlisted diseases, asymptomatic/early disease, wrong organs, regional or seasonal shift, new phone processing, blur, glare, shadows, occlusion, and compression can produce unsafe high-confidence matches unless explicitly rejected.

### Regulatory / Compliance Context

- The Digital Personal Data Protection Act, 2023 and the phased Digital Personal Data Protection Rules, 2025 are relevant when uploads or associated metadata identify a person. Release review must track which provisions are in force on the release date and verify purpose-specific notice/consent or another lawful basis, data minimisation, safeguards, retention/deletion, rights handling, and processor controls. A crop image without identifiable people or linked personal metadata is not automatically personal data.
- Copyright, database terms, model-weight licenses, and collector agreements must permit the actual training, evaluation, deployment, and artifact-redistribution uses. A URL, citation, or downloadable file is provenance—not proof of permission.
- PPQS/CIBRC registration and the approved product label govern pesticide use claims for specified crops, targets, directions, precautions, and restrictions. This vision system has no treatment authority; a disease candidate does not establish that a chemical is registered, appropriate, or safe.
- `docs/APPROVED_RELEASES.json` is the project authority. Its current `release-cv` scope is unapproved and records missing field evidence, unknown/OOD evaluation, redistribution approval, agronomist review, and rollback release; no placeholder may satisfy those gates.

### Evidence Automation Boundary

| Evidence | Automation may establish | Required human decision |
|---|---|---|
| Artifact identity and reproducibility | Schema checks, hashes, byte sizes, immutable IDs, dependency/runtime parity, and rerun reports | Whether the reproduced artifact is agronomically fit for release |
| Dataset structure | Required provenance fields, exact/near-duplicate candidates, group overlap, class/region/device coverage counts, and missing-license flags | Whether provenance and permissions are genuine, consent is valid, and the sample represents intended Indian use |
| Performance | Deterministic metric computation, confidence intervals, fixed-threshold pass/fail, subgroup tables, and browser/server parity | Whether error costs, residual failure patterns, and abstention trade-offs are acceptable crop by crop |
| Labels and edge cases | Surface inconsistent IDs, synonym mappings, reviewer disagreement, and unresolved cases | Establish ground truth, resolve mixed/ambiguous symptoms, approve taxonomy, and decide when lab or field examination is required |
| Claims and approval | Detect prohibited treatment fields/phrases and verify that named approvals are present and signed | Approve farmer-facing wording, treatment boundaries, limitations, and the release itself |

Automation produces evidence and blocks incomplete candidates; it never manufactures missing evidence or substitutes for the accountable expert.

### Domain Expert Roles for Evaluation

| Role | Responsibility in Eval |
|------|----------------------|
| Crop agronomist / plant pathologist | Define and calibrate the crop-specific taxonomy and visual differentials; label reference cases; adjudicate ambiguous, mixed, and lookalike cases; review critical errors; sign the agronomic release decision |
| Independent field/extension agronomist | Approve farm/season/region/crop-stage sampling and external holdouts; verify operational capture realism; review abstentions and false acceptances; sample post-release farmer cases |
| Pesticide regulatory specialist or qualified crop-protection officer | Review every farmer-facing management boundary and verify that no output implies off-label or model-authorized treatment |
| Data-rights and privacy steward | Verify original-source permissions, collector/farmer consent where applicable, DPDP scope, minimisation, retention/deletion, and access controls; approve dataset use and redistribution evidence |
| Model validation and release reviewer | Freeze split/threshold protocol, independently reproduce per-class/OOD/calibration/parity results, document automation limits, and block activation until all named human gates are complete |

### Research Sources

- Project evidence: `models/placeholders/top-15-india.json`, `models/RESEARCH.md`, and `docs/APPROVED_RELEASES.json`.
- Mohanty, Hughes, and Salathé, [Using Deep Learning for Image-Based Plant Disease Detection](https://arxiv.org/abs/1604.03169) (controlled-to-external-image generalisation result).
- [Plant disease classification in the wild using vision transformers and mixture of experts](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2025.1522985/full) (redundancy, imbalance, composite images, and mixed-label ambiguity).
- [Effects of Image Dataset Configuration on the Accuracy of Rice Disease Recognition](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2022.910878/full) (symptom, plant-part, and taxonomy design effects).
- [Quantifying the reliability gap in cross-domain plant disease classification](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2026.1826962/full) (controlled-to-field shift and parent-image isolation).
- Government of India, MeitY: [Digital Personal Data Protection Act, 2023](https://www.meity.gov.in/static/uploads/2024/02/Digital-Personal-Data-Protection-Act-2023.pdf) and [Digital Personal Data Protection Rules, 2025](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf).
- Government of India, PPQS/CIBRC: [registered pesticide label example](https://ppqs.gov.in/sites/default/files/dimethoate_30_ec93frallis_india_limited_1.pdf) showing crop-specific directions and the prohibition on use outside the label/leaflet.

## 2. Framework Decision

**Selected architecture:** KisanSathi CV Lifecycle Core v1 — framework-neutral, manifest-first contracts with optional PyTorch/TorchVision, TensorFlow/Keras/Hub, ONNX Runtime quantization and TFLite adapters.

**Canonical deployable artifact:** One immutable ONNX model and label/preprocessing contract per release. ONNX Runtime Web executes that artifact in the browser and ONNX Runtime CPU executes the same bytes on the server. TFLite is an optional separately evaluated export; it is not a second source of truth.

**Version authority:** `docs/APPROVED_RELEASES.json`, not this prose. The current record approves `onnxruntime-web==1.30.0` for development only. Its `release-cv` scope is `deferred_unapproved`, `approved_artifacts` is `null`, and activation/diagnostic use are false. No model in `models/catalog.json` is currently approved.

**Rationale:** The dependency-free validation boundary can inspect catalog and approval records before importing an ML framework or loading executable model bytes. Training backends remain replaceable; promotion depends on immutable artifacts, preprocessing, evidence and human gates rather than the framework that produced the checkpoint.

| Alternative | Decision |
|---|---|
| MLflow | Optional experiment mirror only; not authoritative for approval |
| PyTorch-only or TensorFlow-only core | Rejected because it privileges one training backend |
| BentoML | Rejected because FastAPI already owns serving and authorization |
| Pickle deployment | Rejected because deserialization executes code and browsers cannot consume it |
| Separate browser and server models | Rejected; parity and rollback become ambiguous. Both runtimes consume the release's exact ONNX bytes |

**Vendor lock-in accepted:** No. Backbone providers are adapter inputs; release contracts are portable.

## 3. Framework Quick Reference

### Approved development dependency gate

```powershell
# Read-only: validates the current approval record and exact approved package identities.
python scripts/validate_approved_releases.py `
  --record docs/APPROVED_RELEASES.json `
  --scope development-dependencies `
  --require onnxruntime-web

# Install only the version returned by that successful gate.
npm --prefix packages/browser-vision install --save-exact onnxruntime-web@1.30.0
```

Do not run `--require-all` as an installation precondition today: it is expected to fail because `release-cv` is deliberately unapproved. PyTorch, TorchVision, TensorFlow, TensorFlow Hub, ONNX, ONNX Runtime Python and TFLite tooling must be optional lock groups with exact versions and license evidence before use; this document does not invent unapproved versions.

### Current runnable entry points

```bash
# These commands exist now and remain fail-closed.
python scripts/validate_model_catalog.py
python scripts/validate_approved_releases.py --record docs/APPROVED_RELEASES.json --scope development-dependencies
npm --prefix packages/browser-vision test

# This must fail until a real release is approved; CI should assert the failure state.
python scripts/validate_approved_releases.py --record docs/APPROVED_RELEASES.json --require-all
```

The former `python -m model_pipeline.cli ...` examples were removed because that package and its requirements files do not exist. When the lifecycle CLI is implemented, expose equivalent `train`, `export`, `quantize`, `verify`, `package` and `register` commands under `models/pipeline/`, but keep `register` unable to synthesize approval.

### Runtime and adapter imports

```python
# Optional server/runtime adapter; import only inside the adapter.
import onnxruntime as ort

# Optional ONNX CNN quantization adapter: use representative calibration data.
from onnxruntime.quantization import CalibrationDataReader, QuantFormat, QuantType, quantize_static

# Optional PyTorch adapter; current exporter uses the dynamo path.
import torch
from torchvision.models import mobilenet_v3_small

# Optional TensorFlow/Keras/TFLite adapter.
import tensorflow as tf
import tensorflow_hub as hub
```

```javascript
// Browser worker entry: this import supports WebGPU with WASM fallback.
import * as ort from 'onnxruntime-web/webgpu';

const session = await ort.InferenceSession.create(modelBytes, {
  executionProviders: ['webgpu', 'wasm'],
});
```

### Core abstractions

| Concept | Purpose |
|---|---|
| Catalog slot | Declares routing role and research state; it never grants execution authority |
| Approval record/scope | Separates exact development dependencies from production model approval |
| Recipe and run record | Pin dataset manifest, split groups, backend/version, seed, preprocessing and metrics |
| Backend adapter | Lazy-imported implementation for training/export/quantization; never used by registry inspection |
| Candidate release bundle | ONNX, labels, preprocessing, gates, hashes, license, golden fixtures and rollback identity awaiting review |
| Approved release descriptor | Server-issued, signed and expiring projection of one approved bundle for browser/server loading |

### Pitfalls

1. **Development approval is not release approval.** `onnxruntime-web==1.30.0` may be installed for development, but the current record authorizes no diagnostic model.
2. **Catalog `status: approved` is insufficient by itself.** Activation also requires the approved release scope, exact hashes/sizes, field/OOD/agronomist evidence, server golden fixture and rollback identity.
3. **Do not duplicate preprocessing constants.** Generate browser and server preprocessing from the release manifest; silent RGB/layout/resize/normalization differences invalidate parity.
4. **Use static, calibrated quantization for these CNNs.** Dynamic quantization is generally recommended for RNNs/transformers; quantization can regress individual classes even when aggregate accuracy looks stable.
5. **WebGPU is opportunistic.** Import the WebGPU build, request `['webgpu', 'wasm']`, and treat unsupported operators/devices, load errors and timeouts as typed fallback—not diagnosis.

### Target folder boundary

```text
models/
  catalog.json                 # discovery only; no framework imports
  pipeline/                    # proposed dependency-free core + lazy adapters
    contracts.py
    adapters/{pytorch,tensorflow,onnx,tflite}.py
  candidates/<release-id>/     # disabled evidence bundle
  releases/<release-id>/       # mounted only after approval
packages/browser-vision/       # manifest/preprocess/runtime shared by the worker
apps/web/src/workers/          # browser inference isolation
services/api/app/routers/      # signed descriptor + authoritative finalization
```

### Sources

- Project authority: `models/catalog.json`, `docs/APPROVED_RELEASES.json`, and Phase 07 Plan 07-10.
- ONNX Runtime Web install/import/support: https://onnxruntime.ai/docs/get-started/with-javascript/web.html
- ONNX Runtime quantization: https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html
- PyTorch ONNX exporter (`dynamo=True`): https://docs.pytorch.org/tutorials/beginner/onnx/export_simple_model_to_onnx_tutorial.html
- TensorFlow Lite converter: https://www.tensorflow.org/api_docs/python/tf/lite/TFLiteConverter

## 4. Implementation Guidance

- **Baseline, not approval:** use the catalog's `mobilenet_v3_small` candidate for the router and most specialists (and `efficientnet_v2_b0` only where declared) as a training baseline. A recipe must pin pretrained-weight identity, source revision, input shape, optimizer, learning-rate schedule, batch size, epochs, seed and augmentation; there is no production model choice until evidence passes.
- Use deterministic dataset manifests and farm/date/season/device group splits. Never discover unlabeled files implicitly or random-split near duplicates.
- Export PyTorch through `torch.onnx.export(..., dynamo=True)` or convert the TensorFlow candidate through a tested adapter. Preserve the source checkpoint for reproducibility, but make the ONNX artifact the deployable contract.
- For CNN INT8 candidates, run ONNX shape/preprocessing first and `quantize_static` with a versioned representative calibration set. Reject promotion on any per-class recall, OOD, calibration or browser/server parity regression beyond manifest thresholds.
- A TFLite export uses `tf.lite.TFLiteConverter.from_keras_model()` or `from_saved_model()` and its own representative dataset. It is optional and cannot inherit ONNX approval.
- The release manifest owns input/output names, dtype, shape/layout, RGB conversion, resize/crop, scaling, mean/std, labels, thresholds, limitations and supported execution providers. Code consumes these fields; it does not restate them.
- Browser flow: fetch the authenticated signed descriptor, verify signature/expiry and artifact hashes, then create a worker session with WebGPU→WASM fallback. Bound input bytes, worker message size and inference timeout; transfer image/tensor buffers rather than copy them.
- Server flow: load the exact same ONNX hash with the CPU provider, bind the candidate to actor/upload checksum, re-run every gate, and persist only the authoritative result. Browser scores are attacker-controlled evidence.
- Keep candidates disabled and outside `models/releases/` until the release record names their exact artifacts. Missing runtime/artifact, stale descriptor, hash mismatch, wrong crop, low quality/score/margin or OOD always produces server fallback or expert review.

### Core release-loading pattern

```python
from pathlib import Path
import hashlib
import onnxruntime as ort  # optional runtime adapter import

def open_release(model_path: Path, expected_sha256: str) -> ort.InferenceSession:
    # The caller must already have validated approval, descriptor expiry and safe path containment.
    digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
    if digest != expected_sha256:
        raise ValueError("release artifact hash mismatch")
    return ort.InferenceSession(
        str(model_path),
        providers=["CPUExecutionProvider"],
    )
```

Production code should hash in chunks rather than `read_bytes()` for large files. The compact example emphasizes the non-negotiable order: validate authority and identity before constructing a runtime session.

## 4b. AI Systems Best Practices

### 4b.1 Structured outputs with Pydantic

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class ArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)

class ReleaseDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    release_id: str
    model_id: str
    status: Literal["candidate", "approved", "revoked"]
    artifacts: dict[str, ArtifactRef]
    missing_gates: list[str] = Field(default_factory=list)
    activation_allowed: bool = False

    @model_validator(mode="after")
    def approval_is_fail_closed(self) -> "ReleaseDecision":
        if self.status == "approved" and (self.missing_gates or not self.activation_allowed):
            raise ValueError("approved release has unresolved gates")
        if self.status != "approved" and self.activation_allowed:
            raise ValueError("only an approved release may activate")
        return self
```

Use Pydantic v2 at API/config boundaries and JSON Schema for repository records. This CV lifecycle has no LLM structured-output integration: validation is deterministic and free-form model-generated text can never approve a release. Retry a transient descriptor/artifact read at most once with bounded backoff; do not retry schema, signature, expiry, hash, license or safety-gate failures. Log release ID, expected/actual hash, gate code, runtime and correlation ID—never raw farmer images. Surface persistent transient failures as server fallback; surface integrity or safety failures as expert review/security telemetry.

### 4b.2 Async-first design

Browser inference is promise-based and belongs in a Web Worker; stream only progress states such as download/verify/load/infer, never partial class scores. Await the completed, schema-validated candidate before display or finalization. FastAPI endpoints may be `async`, but CPU ONNX inference and hashing must run in a bounded worker thread/process (for example `starlette.concurrency.run_in_threadpool`) so the event loop remains responsive. Do not call `asyncio.run()` inside FastAPI or another running loop. Bound concurrency per loaded model and enforce cancellation/timeouts at the request and worker boundaries.

### 4b.3 Prompt engineering discipline

No generative prompt is in this lifecycle. The equivalent discipline is contract separation: immutable system policy (approval and safety gates) stays server-side; user claims such as crop confirmation remain untrusted input. Examples/fixtures are versioned golden tensors and expected candidates, not few-shot prompts. `max_tokens` is not applicable. If an LLM later explains a screened result, it must be a separate non-authoritative subsystem with explicit system/user separation, retrieved agronomy sources, structured output validation and an explicit output-token cap.

### 4b.4 Context and memory management

There is no LLM context window. Bound the analogous resources: decoded image dimensions/bytes, tensor shape, worker message size, model download size, resident sessions and audit payload. Load the router once, lazy-load only the routed specialist, maintain a small LRU keyed by immutable release ID/hash, and dispose sessions on revocation or memory pressure. Persist release/hash/gate summaries rather than raw tensors or images by default. Never truncate labels, preprocessing, limitations or gate evidence to fit a payload; fail closed if the signed descriptor is incomplete.

### 4b.5 Cost and latency budget

This path has compute/bandwidth cost, not token cost. Every approved manifest must declare and CI must measure: artifact bytes, cold download, session initialization, preprocess p50/p95, inference p50/p95, peak memory, server CPU time and fallback rate on the supported device/browser matrix. Use immutable browser/CDN caching keyed by release hash and server session reuse; never cache by mutable URL or reuse a result across actor/upload checksums. Prefer MobileNetV3 Small and calibrated INT8 only when per-class, OOD and parity gates still pass. Route unsupported devices to the server and low-confidence/OOD cases to review rather than spending repeated inference attempts.

## 5. Evaluation Strategy

### 5.1 Release decision rule

Evaluation is performed on the complete cascade: image quality and OOD gates → 15-crop-plus-`unknown` router → the selected crop specialist → calibrated accept/abstain decision → browser/server finalization. Router and specialist metrics are also reported separately for diagnosis, but they cannot substitute for end-to-end evidence.

A candidate is eligible for human review only when **every Critical rubric passes**, every required cohort has enough independently grouped examples to compute its declared confidence interval, no hard invariant is violated, and the candidate is no worse than the named approved rollback release on any Critical metric. Missing data, an empty crop/class cohort, an unresolved reviewer disagreement, or an inapplicable threshold is a failure, not `N/A`. Aggregate accuracy cannot hide a failing crop, class, field subgroup, OOD category, or runtime.

Numeric values in Section 5.3 are **default candidate threshold templates only** (`candidate-default-v0`). They are neither measured evidence nor agronomic/release approval. Before the final test set is opened, the model validation reviewer and crop agronomists must replace or explicitly confirm them crop by crop from the disjoint calibration set, document error costs and intended scope, and freeze the resulting threshold profile by hash in the candidate manifest. Changing a model, labels, preprocessing, calibration method, threshold, quantization, execution provider, or dataset manifest creates a new candidate and requires a fresh evaluation. `docs/APPROVED_RELEASES.json` remains authoritative and currently makes `release-cv` unapproved and non-activatable.

### 5.2 Domain rubrics

| Dimension | PASS | FAIL | Measurement | Priority |
|---|---|---|---|---|
| Release authority and task completion | One immutable candidate routes or abstains, invokes only the matching specialist, returns the frozen non-diagnostic schema, and is named with exact hashes, threshold-profile hash, evidence bundle, approvals, and rollback release in `APPROVED_RELEASES.json`. | Any placeholder/demo activates; a known crop is sent to the wrong specialist; a browser candidate is persisted as authoritative without server revalidation; evidence or rollback identity is missing. | Code + Human release review | Critical |
| Known-crop router | On the untouched field holdout, top-1/top-3, macro recall, every crop's recall, confusion matrix, and group-bootstrap 95% confidence intervals pass the frozen crop-specific profile. | Only aggregate accuracy passes; any crop misses its bound; near-duplicate plant/burst/farm groups cross splits; or final-test results influenced model or threshold selection. | Code + Human review of split/coverage | Critical |
| Routed specialist correctness | For every crop and every disease/healthy class, end-to-end routed recall, precision, macro-F1, accepted-case error, coverage, and confusion pass; crop-specific agronomists accept the residual errors and differentials. | Specialist-only scores hide router errors; a visually inseparable, mixed, or unsupported case is forced into one disease; a rare or safety-critical class is averaged away; or a visual match is represented as pathogen confirmation. | Code + two agronomists with adjudication | Critical |
| Unknown/OOD, quality, abstention and escalation safety | Wrong/non-target crops, unlisted disease, abiotic/pest injury, mixed symptoms, wrong organ, non-plant content, and unusable captures remain below the frozen false-acceptance bound; rejected cases receive neutral recapture or expert-review outcomes. | Any upload is forced to a known class; top-3 is used as rejection; one global cutoff is assumed safe for all crops/classes; or high abstention is hidden while reporting accepted-case accuracy. | Code + Human review of false accepts | Critical |
| Independent field validity | The final holdout contains unseen farms/plots and relevant regions, seasons, stages, varieties, devices, lighting, backgrounds, and severities; controlled imagery is reported separately and field/subgroup bounds pass. | Random image splits, augmented-parent leakage, one-farm/device dominance, tuning on the field holdout, or controlled-leaf results are used as release evidence. | Code + independent field agronomist | Critical |
| Calibration and selective prediction | Per-model/per-class calibration and rejection thresholds are fit only on the calibration split; ECE, Brier score, reliability plots, risk-coverage curves, and threshold stability pass on the untouched field holdout. | Raw softmax is called confidence without calibration; test labels tune thresholds; a nominal confidence is well calibrated overall but unsafe for a crop/class/subgroup; or coverage is omitted. | Code + Human approval of risk/coverage trade-off | High |
| Quantization robustness | The final INT8 artifact meets frozen aggregate and per-class delta limits against the source FP32 candidate on the same cases; OOD, calibration, and accept/abstain decisions do not regress beyond profile limits. | Artifact size improves while a crop/class, OOD category, calibration, or gate decision regresses; calibration data overlaps final test data; or a different quantized artifact is deployed than evaluated. | Code | Critical |
| Browser/server and provider parity | The exact approved ONNX bytes, labels, preprocessing, and thresholds produce equivalent tensors, ordered scores, route, specialist, and accept/abstain decision on CPU server, WASM, and supported WebGPU matrix within the frozen numeric tolerance. | Only top-1 labels are compared; preprocessing differs; WebGPU error is silently accepted; runtime fallback changes the decision; or golden fixtures do not identify artifact/runtime versions. | Code on real browser/device matrix | Critical |
| Performance and bounded resource use | Cold/warm latency, model bytes, download/init/preprocess/inference p50/p95/p99, peak memory, timeout, cancellation, concurrency, and fallback behavior pass on each declared lowest-supported browser/device and server tier. | Mean latency alone is reported; low-end devices are absent; a timeout retries inference indefinitely; the main thread blocks; or memory/load failure is shown as a diagnosis. | Code + browser/load tests | High |
| Governance, claim boundary and human approval | Dataset/image rights, consent where applicable, provenance, split lineage, licenses, taxonomy, limitations, privacy handling, exact hashes, reviewer identities, dates, conflicts, and crop-by-crop agronomist decisions are complete; UI/API language remains a possible visual match and contains no treatment authority. | Automation or an LLM implies approval; provenance is treated as permission; a missing crop sign-off is covered by a global sign-off; raw personal data is logged; or output confirms disease or recommends a pesticide, dose, mixture, schedule, fertilizer, or machinery action. | Code for completeness/prohibited fields + accountable Human sign-off | Critical |

LLM judges are not used to establish image ground truth, metric pass/fail, rights, or release approval. If a future generative explanation layer is evaluated, its judge must first achieve at least 0.70 agreement/correlation with a blinded human calibration set and remains advisory; it cannot change the CV release decision.

### 5.3 Default candidate threshold template — not approval

All rates use pre-registered denominators. Recall, accepted-case error, false acceptance, and subgroup rates use two-sided 95% Wilson intervals; model-difference metrics use a farm/plant-group-stratified paired bootstrap with at least 2,000 resamples. A template passes only when the conservative bound passes (lower bound for beneficial metrics, upper bound for harmful metrics). A crop/class with fewer cases than Section 5.4 is evidence-insufficient even if its point estimate passes.

| Gate | `candidate-default-v0` template | Required report |
|---|---|---|
| Router, known crops | Macro top-1 ≥ 0.90; macro top-3 ≥ 0.97; each crop top-1 recall 95% LCB ≥ 0.80 | Per-crop support/confusion, top-1/top-3, macro/micro values, CIs |
| Router unknown rejection | Overall unknown false-acceptance 95% UCB ≤ 0.05 and each declared unknown category UCB ≤ 0.10 | False accepts by category, predicted crop, device/region and score/margin bins |
| End-to-end specialists | Macro-F1 ≥ 0.80; each class recall 95% LCB ≥ 0.70; agronomist-designated critical classes LCB ≥ 0.85; accepted-case error UCB ≤ 0.10 at coverage ≥ 0.60 | Routed and oracle-router metrics, per-class confusion, risk-coverage curve, abstention reasons |
| Capture quality | Recall for agronomist-labeled unusable captures LCB ≥ 0.95; false rejection of gradable known cases UCB ≤ 0.10 | Blur/glare/occlusion/compression/symptom-area cohorts separately |
| Calibration | ECE ≤ 0.05 overall and ≤ 0.08 per crop; Brier score no worse than the pre-registered baseline; no subgroup ECE degradation > 0.03 versus internal field test | Equal-mass reliability diagram, Brier/ECE with binning definition, threshold sensitivity |
| Field/subgroup robustness | External-field macro-F1 drop versus internal field test ≤ 0.05 absolute; any adequately supported region/device/stage/severity recall drop ≤ 0.10 | Group supports, paired deltas/CIs, declared unsupported scope |
| INT8 quantization | Macro-F1 drop ≤ 0.01; any class recall drop ≤ 0.02; unknown false-acceptance increase ≤ 0.005; accept/abstain decision agreement ≥ 0.995 versus FP32 | Paired case-level deltas and all decision flips |
| Runtime parity | Route, final class and accept/abstain decision agreement = 1.000 on golden cases; max absolute probability delta ≤ 1e-4 for WASM/CPU and ≤ 1e-3 for supported WebGPU; preprocessed tensor delta ≤ 1e-6 | Case-level mismatches with runtime, browser, device, provider and hashes |
| Performance | On each lowest-supported client tier: combined router + one specialist ≤ 20 MiB, cold p95 ≤ 5 s, warm end-to-end p95 ≤ 2 s, peak worker memory ≤ 256 MiB; server warm p95 ≤ 1 s; timeout/failure fallback success = 1.000 | p50/p95/p99, sample size, network/device/server profile, timeout/cancel/fallback results |
| Hard governance invariants | 100% required fields/hashes/licenses/split checks/signatures present; zero unapproved activations, cross-crop specialist calls, authoritative browser-only persists, prohibited treatment fields, or missing required human approvals | Machine-readable gate report plus signed reviewer checklist |

These values are starting hypotheses. The release evidence must contain the frozen approved threshold profile and its rationale, not a statement that these defaults were copied.

### 5.4 Reference datasets and labeling

Dataset construction starts with implementation, before training and threshold tuning. A 20-case set is the minimum contract/evaluator smoke set only and is never production-release evidence.

| Dataset | Minimum composition | Use and isolation |
|---|---|---|
| Router calibration | At least 50 independently grouped known-crop cases per crop plus 300 unknown/OOD cases spanning all declared categories | Fit calibration and crop-specific score/margin/OOD thresholds; never used for final reporting |
| Router final field test | At least 100 independently grouped cases per known crop (≥1,500 total) plus at least 600 OOD/unknown cases; each crop covers at least 3 unseen farms, 2 districts/agro-climatic contexts, 2 device families, and relevant stages/severities | Open once after candidate and threshold-profile hashes are frozen; report internal-independent and external-holdout strata separately |
| Specialist calibration | At least 50 independently grouped cases per disease/healthy class, including labeled lookalikes and mixed/ambiguous cases for rejection | Fit class calibration and accept/abstain thresholds only |
| Specialist final field test | At least 100 independently grouped cases per disease/healthy class: at least 50 internal-independent and 50 external-field cases; include critical lookalikes for each class | End-to-end and oracle-router scoring; a class shortage blocks broad release or requires a narrower, explicitly approved scope |
| Quality/OOD challenge | At least 100 cases in each of: wrong/non-target crop, unlisted disease, pest/abiotic injury, mixed/ambiguous symptoms, wrong organ/non-plant, and unusable capture; include near-OOD lookalikes, not only obvious negatives | Measures false acceptance and escalation; categories remain disjoint from calibration |
| Quantization/parity golden set | At least 25 representative and boundary cases per model plus every known decision-flip candidate and synthetic preprocessing edge vectors | Run from original bytes through server CPU, browser WASM and supported WebGPU; store expected tensors/scores/decisions and hashes |
| Performance matrix | At least 100 warm and 30 cold runs per declared browser/device/runtime/network tier, plus concurrency, timeout, crash, corruption and fallback injections | Performance only; cannot substitute for accuracy/field evidence |

Source image/burst, plant, plot/field/farm, collector, collection date, near-duplicate cluster, and every augmented/synthetic parent are immutable grouping keys. No group may cross train, calibration, internal test, or external holdout. Exact and perceptual duplicate scans are mandatory, with human disposition of candidates. Dataset manifests include source, rights holder, license/permission scope, consent/lawful basis where applicable, checksum, crop/organ/stage/variety, disease status/severity, district or coarse agro-climatic context, device family, capture conditions, reviewer IDs, and split/group IDs; precise location and direct identifiers are excluded or access-controlled.

Two qualified crop agronomists or plant pathologists independently label final-test cases while blinded to model output and split metrics. A named senior expert adjudicates disagreements, mixed symptoms, lookalikes, and visually inseparable cases; unresolved cases remain an explicit rejection cohort rather than being forced into accuracy labels. Report raw agreement and classwise agreement before adjudication. An independent field/extension agronomist approves sampling realism, and the data-rights steward verifies permissions. Automated labels or an LLM may assist triage but cannot be final ground truth.

### 5.5 Tooling and CI/CD gate

No Langfuse, LangSmith, Arize/Phoenix, Braintrust, Promptfoo, or RAGAS integration is currently detected in the standalone code. Use deterministic Python metric code plus JSON/CSV/HTML evidence as the release authority; use Playwright/Node tests for real browser parity and failure injection. RAGAS and Promptfoo are not applicable to this non-generative CV lifecycle. Arize Phoenix is the default observability UI via OpenTelemetry, but it is not an approval system and its installation requires exact-version dependency/license approval first.

Proposed observability install command (planning template only; do not install or treat as approved until exact versions are added to the approved development scope):

```bash
python -m pip install arize-phoenix opentelemetry-sdk
```

The lifecycle implementation must add an `evaluate-release` subcommand that emits an immutable `eval-report.json`, case-level decisions, confusion/calibration/risk-coverage artifacts, group-bootstrap CIs, parity/performance reports, dataset/threshold/artifact hashes, and a boolean result per rubric. CI runs the following fail-closed gate from `Kisan Sathi Web/`; the new evaluation command being absent, any report/hash being stale, or the final `--require-all` remaining unapproved fails the release job:

```bash
python scripts/validate_model_catalog.py
python -m models.pipeline.model_pipeline registry-validate
python -m models.pipeline.model_pipeline evaluate-release \
  --candidate models/candidates/<release-id>/manifest.json \
  --reference-manifest models/evaluation/<dataset-id>/manifest.json \
  --threshold-profile models/candidates/<release-id>/thresholds.json \
  --output models/candidates/<release-id>/evidence/eval-report.json \
  --fail-on-missing --require-all-critical
npm --prefix packages/browser-vision test
python -m pytest services/api/tests/test_vision_persistence.py -q
python scripts/validate_approved_releases.py --record docs/APPROVED_RELEASES.json --require-all
```

The evaluator may calculate evidence and block a candidate; it must never write human approval fields or promote a release. A model validation reviewer independently reruns the gate from a clean checkout before sign-off.

## 6. Guardrails

Guardrails are limited to failures that can cause immediate farmer harm, integrity loss, or unauthorized activation. They run before a result is shown or persisted; quality-improvement signals remain offline to avoid adding avoidable request latency.

### 6.1 Online guardrails — every request or release load

| Critical failure blocked | Trigger/check | Immediate intervention | Verification |
|---|---|---|---|
| Unapproved, stale, substituted, or revoked release | Approval scope/status, activation flag, descriptor signature/expiry, safe path, exact model/labels/manifest hashes and sizes, runtime allowlist, and rollback identity do not all match | Do not construct/use the session; emit typed integrity/unavailable state; page security/release owner for hash/signature mismatch; use only the separately validated rollback release | 100% mutation tests for each missing/changed field; zero bypasses |
| Unsafe or abusive input | MIME/magic bytes, decoded dimensions, byte/tensor/message limits, ownership/checksum binding, and quality precheck fail | Reject or request recapture; do not decode/infer repeatedly; do not log raw bytes | Boundary/fuzz/decompression-bomb tests and bounded resource assertions |
| Wrong-crop cascade | Router returns `unknown`, misses crop-specific score/margin/OOD gates, conflicts with trusted user crop context, or selected specialist crop differs from route | Do not invoke a mismatched specialist; ask for crop confirmation/recapture or use server/expert review | Cross-product tests over all 15 routes + unknown; expected wrong-specialist calls = 0 |
| Confident known-class output for OOD/ambiguous content | Quality, known-vs-unknown, score, margin, calibration, mixed/ambiguous, wrong-organ, or specialist gate fails | Return neutral abstention with reason code and recapture/expert-review path; never force argmax | Challenge-set false-acceptance gate plus tests for every reason code |
| Browser candidate treated as authority | Candidate lacks owned upload checksum, release/preprocessing/threshold identity, valid descriptor, or server revalidation; any browser-supplied gate differs from server recomputation | Discard candidate and run validated server fallback; if unavailable, persist only `needs_expert_review`/`unavailable`, never a diagnosis | Tamper/replay/cross-tenant/idempotency tests; authoritative browser-only persists = 0 |
| Diagnostic/treatment overclaim | Output schema or presentation contains confirmed-diagnosis language, omits limitations/release identity, or contains pesticide, dose, mixture, schedule, fertilizer, or machinery action | Block response/persistence and return the approved screening/limitation template; route claim defect to release owner | Schema/prohibited-field checks and agronomist-approved UI snapshots |
| Runtime failure or parity uncertainty | Unsupported provider/operator/device, model load error, timeout/cancel, worker crash, non-finite score, shape mismatch, or parity canary failure | Terminate local inference, evict the session, and use server fallback or expert review; no automatic repeated inference loop | Failure injection on WASM/WebGPU/server; fallback completion = 100% |

Cryptographic artifact hashing may occur once at verified load and be bound to an immutable cached release identity; signature/expiry, request ownership, and decision gates still run per request. No extra generative safety model is placed in the hot path.

### 6.2 Offline evaluation flywheel

| Signal | Sample/cohort | Batch decision and owner |
|---|---|---|
| Accepted-case corrections or agronomist disagreement | 100% of corrections, complaints, adverse outcomes, and expert overrides | Quarantine related cases, inspect same release/crop/class/device cohort, and have the crop agronomist decide label defect, threshold defect, drift, or misuse |
| Abstention/coverage shift | All metadata; stratify by crop, reason, device family, coarse region, season/stage when lawfully available | Weekly risk-coverage and reason analysis; model validation reviewer proposes threshold/model work but cannot self-update production |
| OOD and emerging lookalikes | 100% OOD/unknown events plus consented low-margin sample | Monthly challenge-set expansion after human labeling; keep new cases out of training until a new versioned split is assigned |
| Field/subgroup drift | Weighted sample from new device/region/stage/severity groups and embedding/score-distribution drift | Investigate signal-metric divergence; require targeted field collection and a new candidate when reference-set coverage is inadequate |
| Calibration drift | Human-labeled production sample, by crop/class and accepted/abstained outcome | Recompute reliability/Brier/risk-coverage; recalibration is a new candidate, not an online parameter edit |
| Quantization/runtime parity | Scheduled golden suite on every supported browser/runtime update and a canary sample after deployment | Disable affected browser provider/artifact on any decision mismatch; require fresh parity evidence before re-enable |
| Governance expiry or revocation | 100% of releases, datasets, dependencies, licenses, signatures, reviewer terms, and rollback readiness | Data-rights/release owner blocks or revokes use; remove affected artifact from descriptors; preserve audit evidence |

Production images enter this flywheel only under the approved notice/consent, retention, access, and deletion policy. Raw images are never copied into Phoenix traces. A model, label, calibration update, or threshold change always re-enters Section 5 and never self-approves from production telemetry.

## 7. Production Monitoring

### 7.1 Tracing and event contract

Use OpenTelemetry spans with self-hosted Arize Phoenix as the default trace viewer. Phoenix is for observability only: immutable evaluation reports and `APPROVED_RELEASES.json` remain the release authority. Before installation, exact package versions and licenses must pass the development-dependency gate.

```python
# pip install arize-phoenix opentelemetry-sdk  # only after exact-version approval
import phoenix as px
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

px.launch_app()  # http://localhost:6006
provider = TracerProvider()
trace.set_tracer_provider(provider)
# Instrument manual spans around descriptor verify, preprocess, route, specialist,
# gate, fallback and authoritative finalization; configure the approved exporter.
```

Emit structured events for 100% of requests with: correlation/request ID; coarse consented tenant/region/device cohorts; release/model/labels/preprocessing/threshold-profile IDs and hashes; descriptor version/expiry; router and specialist IDs; quality/OOD/score/margin gate outcomes; accepted/abstained/fallback reason; browser provider/version and server provider/version; download/init/preprocess/inference/finalization latency; artifact bytes and bounded memory measurement; server revalidation outcome; and final authoritative state. Do not emit raw images, tensors, precise location, names, account IDs, free-text farmer content, or full score vectors. Keep security/audit retention separate from short-lived performance traces and apply role-based access.

### 7.2 Alerts and automatic response

The numeric alert values below are operational templates, not release evidence. At approval time they must be replaced by control limits derived from the frozen release baseline, expected traffic, and agronomist-approved error budget. Rate alerts require at least 100 eligible events per monitored window unless an integrity invariant fires.

| Signal | Default alert template | Automatic safe response | Owner |
|---|---|---|---|
| Unapproved/revoked release, signature/expiry failure, hash/size mismatch, missing limitations, or browser-only authoritative persist | Any event | P0: block/disable release immediately; validate named rollback; page security and release owner | Release owner + security |
| Wrong specialist invocation or prohibited treatment/confirmed-diagnosis field | Any event | P0: block output, disable affected path/release, preserve non-image audit evidence | Release owner + crop-protection reviewer |
| Browser/server route, class, or accept/abstain mismatch on a parity canary | Any decision mismatch; probability tolerance breach in 2 consecutive canary runs | Disable affected browser provider and force server/review; open parity incident | Runtime owner |
| Unknown/OOD false acceptance from adjudicated production sample | 95% UCB exceeds approved release limit, or 2 confirmed false accepts in the same crop/category within 24 h | Suspend affected crop/class acceptance; route to expert review; start incident evaluation | Model validation + agronomist |
| Accepted-case error/correction | 95% UCB exceeds approved selective-risk limit, or ≥2× approved baseline for 2 windows | Suspend affected crop/class or release based on blast radius; expand human review | Model validation + agronomist |
| Abstention, OOD, fallback, or crop acceptance distribution | Absolute shift ≥10 percentage points and ≥2× baseline for 2 consecutive 1 h windows | Keep abstention/fallback safe path; investigate device/region/release shift; do not lower thresholds online | Operations + model validation |
| Calibration drift | ECE exceeds approved limit by >0.02 on the monthly labeled sample, or reliability-bin error exceeds its approved CI | Stop broadening coverage; create recalibration candidate through Section 5 | Model validation |
| Latency/resource regression | p95 exceeds approved tier budget or 2× baseline for 15 min; timeout/fallback failure >0 | Disable affected local provider when needed; preserve server/review path; page operations | Runtime/operations |
| Agronomist/data-rights/license/rollback evidence expires or is revoked | Any event | Block new descriptors and activation; rollback or withdraw the affected scope | Governance owner |

### 7.3 Sampling, review cadence and release governance

- Keep 100% low-cardinality metadata for integrity, gate, abstention, fallback, latency, release identity, and authoritative-state events; retain 100% of security failures, corrections, complaints, expert overrides, and parity failures.
- For the first 30 days of a release, conduct agronomist review of every reported adverse/incorrect result and a consented stratified sample of at least 20 accepted and 20 abstained cases per crop. After stability is demonstrated, review monthly at the same minimum, oversampling low-margin, new device/region/stage, rare classes, OOD, and signal-metric divergence. If lawful/consented images are unavailable, mark outcome-quality monitoring unavailable; telemetry alone cannot prove accuracy.
- Re-run the full frozen reference suite on every artifact, label, preprocessing, calibration, threshold, quantization, ONNX Runtime/browser, supported execution-provider, or browser-matrix change. Run parity golden tests nightly and governance/expiry checks daily. Recompute human-labeled calibration/accepted-risk monthly and complete a quarterly crop-by-crop agronomic review during active deployment.
- Dashboards show denominators and confidence intervals, not bare percentages. Slice by release, crop, class, accepted/abstained state, OOD reason, device/browser/provider, coarse region, season/stage, and server fallback; suppress or aggregate privacy-sensitive small cells.

### 7.4 Approval and rollback authority

The release sequence is: deterministic evaluator passes → independent model validation reviewer reproduces the evidence → two crop-qualified reviewers and a senior adjudicator sign each in-scope taxonomy/specialist and the router/abstention behavior → independent field agronomist signs representativeness → data-rights/privacy steward signs permitted use and redistribution → crop-protection reviewer signs the claim/treatment boundary → accountable release owner records exact artifacts, evidence hashes, limitations, expiry and an already-approved rollback release in `docs/APPROVED_RELEASES.json`.

Only the final recorded human decision may set `release-cv.approved`, `release_ready`, `activation_allowed`, and `diagnostic_use_allowed` according to project policy. Automation and Phoenix cannot create, infer, copy forward, or broaden approval. Until that record changes through the governed review, all existing research/structural placeholders remain quarantined, non-diagnostic, and non-activatable.

## Checklist

- [x] System and failure modes classified
- [x] Domain stakes, rubric and expert roles defined
- [x] Framework-neutral architecture selected
- [x] Training/deployment formats separated
- [x] Evaluation dimensions and guardrails defined
- [x] Registry inspection remains dependency-free
- [x] Placeholders and demos remain non-activatable
- [x] Human approval cannot be synthesized by automation
