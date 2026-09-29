# Model training, candidate packaging, and registration

This workflow creates reviewable model **candidates**. Packaging and registration never approve, activate, or promote a model. The only release authority is `docs/APPROVED_RELEASES.json`, updated after the automated and named-human gates below are independently verified.

## 1. Prepare and verify the dataset manifest

Create a manifest conforming to `models/pipeline/dataset-manifest.schema.json`. Do not discover images implicitly and do not use a random image-level split.

Before training, verify all of the following:

1. Every image has a SHA-256 hash, traceable source, immutable source revision, rights holder, collector, and acquisition date.
2. The license or written permission explicitly covers the actual training and evaluation use. Record redistribution permission separately; a public URL is not permission.
3. Consent or another lawful basis is recorded where applicable, with purpose, retention, deletion, access, and removal or access control of direct identifiers and precise location.
4. `group_split.strategy` is `grouped`. Source image/burst, plant, plot/field/farm, collector, collection date, near-duplicate cluster, synthetic parent, and device groups used by the dataset are recorded. No group crosses train, validation, calibration, internal test, external holdout, OOD challenge, or golden splits.
5. Exact and perceptual duplicate scans have run, human dispositions are complete, and `overlap_count` is zero.
6. Crop, organ, stage, variety where available, disease status/severity, coarse district or agro-climatic context, device family, capture conditions, reviewer IDs, and adjudication are present for each record.
7. Calibration and final-test records are disjoint. The final field holdout remains unopened until the model, preprocessing, calibration method, and threshold profile are frozen.

Validate with the core environment:

```powershell
python -c "import json; from pathlib import Path; from jsonschema import Draft202012Validator; root=Path('models/pipeline'); schema=json.loads((root/'dataset-manifest.schema.json').read_text()); doc=json.loads(Path('<dataset-manifest.json>').read_text()); Draft202012Validator(schema).validate(doc); print('dataset manifest: valid')"
```

Schema validity checks structure only. A data-rights/privacy steward must verify provenance, permission, consent, minimisation, retention, and redistribution facts; qualified agronomists or plant pathologists must verify labels and ambiguity handling.

## 2. Train, export, quantize, and evaluate

Install only the backend needed for the run. For ONNX export and quantization, use the exact environment in `models/pipeline/requirements-onnx.txt`; this workflow does not download weights.

Record the recipe, immutable dataset-manifest hash, source and training-code revisions, framework/version, pretrained-weight identity if applicable, seed, preprocessing, optimizer/schedule, epochs, and run ID. Export a fixed-contract ONNX model with declared input/output names and only the intended dynamic batch axis.

CNN release candidates must use static INT8 quantization with a versioned representative calibration set:

```python
from pathlib import Path
from model_pipeline.quantization import ArrayCalibrationReader, quantize_onnx

reader = ArrayCalibrationReader("input", representative_tensors)
quantize_onnx(
    Path("build/model-fp32.onnx"),
    Path("build/model-int8.onnx"),
    mode="static-int8",
    calibration_reader=reader,
)
```

Dynamic INT8 is experimentation-only and cannot satisfy the release bundle schema. Evaluate the exact quantized ONNX bytes that will be packaged. Verify aggregate and per-class precision/recall/F1, confusion, accepted-case error and coverage, calibration/Brier, OOD and unknown false acceptance, group-bootstrap confidence intervals, FP32-to-INT8 deltas and every decision flip, browser/server/provider parity from original bytes through final decision, latency/memory/fallback behavior, and all declared subgroups. Missing or empty cohorts fail; aggregate accuracy cannot hide them.

## 3. Assemble the seven required artifacts

Place these non-empty files beneath a clean build directory. None may be a placeholder, demo, structural stub, or untrained artifact.

| Role | Required content |
|---|---|
| `onnx` | The evaluated static-INT8 ONNX bytes |
| `labels` | Ordered class IDs/names, taxonomy version, unknown/abstention behavior |
| `preprocess` | Input name, dtype, shape/layout, RGB conversion, resize/crop, scale, mean/std |
| `evaluation` | Immutable metrics, cohorts, CIs, thresholds, hashes, parity/performance, gate outcomes |
| `model_card` | Intended screening use, exclusions, limitations, subgroup/OOD behavior, non-diagnostic claim boundary |
| `license` | Model/code/weight/dataset license identities and reviewed permissions |
| `golden` | Original inputs or bounded fixtures, expected tensors/scores/routes/decisions, runtime identities and tolerances |

The packager accepts only safe relative source paths, copies exactly these artifacts, hashes every copied file, embeds a canonical manifest-payload hash, and refuses an existing destination. Use a new candidate ID for any model, label, preprocessing, threshold, quantization, provider, dataset, evidence, license, or rollback change.

```python
from pathlib import Path
from model_pipeline.packaging import package_candidate

manifest_path = package_candidate(
    Path("build/rice-router"),
    Path("build/candidate-rice-router-2026-09-18.1"),
    candidate=candidate_metadata,
    artifacts={
        "onnx": "model-int8.onnx",
        "labels": "labels.json",
        "preprocess": "preprocess.json",
        "evaluation": "eval-report.json",
        "model_card": "MODEL_CARD.md",
        "license": "LICENSE.txt",
        "golden": "golden.json",
    },
)
print(manifest_path)
```

`candidate_metadata` must satisfy `models/pipeline/release-bundle.schema.json` after the packager adds reserved status, artifact, gate-default, approval-denial, and integrity fields. In particular it records trained model identity; run provenance; grouped dataset identity/hash; static calibration identity/hash/count; dataset license and consent; agronomist-review and redistribution status; rollback identity/reason/validation; and any evidence-backed gate results. Never put secrets, raw personal data, precise location, or an approval claim in it.

## 4. Register a candidate

Registration verifies schema, manifest payload hash, path containment, every artifact hash/size, and absence of unhashed files. It then makes a non-overwriting copy under `models/candidates/<candidate-id>` and returns missing/failed automated gates plus pending/rejected human gates.

```python
from pathlib import Path
from model_pipeline.packaging import register_candidate

report = register_candidate(
    Path("build/candidate-rice-router-2026-09-18.1/manifest.json"),
    Path("models"),
)
print(report)
```

Expected invariants are `registration_status == "staged_candidate"`, `approved == false`, `activation_allowed == false`, and `promotion_performed == false`. Registration does not edit the model catalog, `models/releases`, or `docs/APPROVED_RELEASES.json`.

## 5. Gates to complete before promotion

Automated evidence must pass for artifact integrity, dataset contract and group isolation, representative static-INT8 calibration, frozen evaluation thresholds, quantization regression, runtime/provider parity, and rollback validation. Re-run from a clean checkout and compare every evidence hash to the staged candidate.

Named humans must complete, with identity/date/scope/evidence:

- two crop-qualified agronomists or plant pathologists plus senior adjudication for taxonomy, labels, lookalikes, ambiguity, errors, abstention, and each in-scope crop;
- an independent field/extension agronomist for farm/region/season/stage/device representativeness;
- a data-rights/privacy steward for provenance, licenses, consent, retention/deletion, and redistribution;
- a crop-protection reviewer for non-diagnostic language and absence of pesticide, dose, mixture, schedule, fertilizer, or machinery authority;
- an independent model-validation reviewer who reproduces the full gate;
- the accountable release owner for exact artifact/evidence hashes, limitations, expiry, supported runtimes, and a previously approved, tested rollback release.

Any missing evidence, failed cohort, unresolved disagreement, absent redistribution permission, absent rollback release, stale hash, or `N/A` critical gate blocks promotion.

## 6. Promote only through the release authority

After every gate above is complete, the accountable release owner—not the packager or registration code—adds a reviewed entry to `docs/APPROVED_RELEASES.json` naming the exact candidate manifest and artifact/evidence hashes, approval scope, reviewer records, limitations, expiry/revocation rules, supported runtimes/providers, and validated rollback release. Run the project approval validator and runtime parity/integration suites from a clean checkout. Only that governed record may allow a separate deployment step to copy bytes into `models/releases` or activate a catalog entry.

If validation fails, leave the candidate in `models/candidates`, record the failed gate, and create a new candidate ID after remediation. Never modify or overwrite a staged bundle.
