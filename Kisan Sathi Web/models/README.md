# Hierarchical crop model catalog

This directory is the model plug-in boundary for the standalone web service.
The checked-in catalog contains one crop-identifier slot followed by one lazy
disease-specialist slot for each crop in `india-common-crops-v1`.

No approved release bytes are committed here. Quarantined research candidates
and compatibility placeholders are excluded from deployable Docker contexts.
`missing`, `research_candidate`,
`pending_review`, and `revoked` entries are never executable. Only `approved`
entries with an existing release manifest, exact ONNX/labels hashes, field
evidence, and release evidence can be exposed to browser or server inference.

```text
photo
  -> approved crop identifier
  -> confidence + margin gate
  -> farmer confirmation when ambiguous
  -> lazy-load approved crop specialist
  -> quality + confidence + margin + OOD gates
  -> server revalidation/persistence or expert review
```

The same ONNX release should run through ONNX Runtime Web (WASM baseline,
optional WebGPU) and ONNX Runtime CPU on the server. This avoids maintaining a
different browser and server model. Specialists are loaded only after routing,
which keeps client download and memory use bounded as crop coverage grows.

## Files

- `catalog.json` — model slots, statuses, runtime policy, and India crop coverage.
- `catalog.schema.json` — machine-readable catalog contract.
- `research-sources.json` — source ledger; entries are research inputs, not approvals.
- `RESEARCH.md` — model-source findings and rollout recommendation.
- `placeholders/` — real pinned ONNX research artifacts, always disabled and excluded from release activation.
- `releases/<model-id>/<version>/` — mounted at deployment after approval; not committed.

## Real placeholder artifacts

`placeholders/index.json` is a separate quarantine registry. Its packages can
exercise hashing, ONNX loading, preprocessing, labels, and golden-output checks,
but they are never read by the production catalog. A placeholder must retain
`research_placeholder_unapproved`, `enabled: false`, and
`release_approved: false` until a distinct release bundle passes every gate.

Install or repair the pinned local bytes with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/download_placeholder_models.ps1
python scripts/validate_placeholder_models.py --require-installed
```

## Adding a real release

1. Train the identifier or one specialist from licensed data with field/date
   separation and an independent unknown/OOD challenge set.
2. Export an ONNX model compatible with both ORT Web WASM and ORT server CPU.
3. Record labels, preprocessing, score/margin/OOD gates, size, hashes, license,
   field metrics, agronomist review, golden parity fixtures, and rollback ID.
4. Mount the versioned files under `models/releases/` and keep the catalog entry
   `pending_review` until Phase 07 approval is recorded.
5. Set `approved` only after the release evidence and files match exactly.
6. Run:

```bash
python scripts/validate_model_catalog.py --require-approved --crop tomato
npm --prefix packages/browser-vision test
```

An unapproved public checkpoint must never be copied into `releases/` merely
because it reports high test accuracy. Most available results use controlled or
small web-scraped datasets and do not establish farmer-phone field performance.

## Validating an approved browser/server release

The Phase 07-10 consumer gate is available before any release is supplied:

```powershell
python models/validate_release_manifest.py `
  --manifest models/manifests/approved-release.yaml `
  --require-approved --verify-artifacts
```

It fails closed when the manifest is absent, expired, incomplete, hash-mismatched,
or not bound to an approved `release-cv` scope. It never promotes candidates or
edits `docs/APPROVED_RELEASES.json`.
