# Quarantined model candidates

This directory contains reproducible research candidates, not deployable
releases. A candidate can contain real trained weights and still be unsuitable
for farmer-facing diagnosis because source-dataset performance is not field
evidence.

## Validation

Run from the standalone service root:

```powershell
python scripts/validate_model_candidates.py
```

The validator checks every indexed candidate's manifest, file size, SHA-256,
path containment, and ONNX graph integrity when the `onnx` package is
installed. It also rejects any candidate that claims activation or diagnostic
use. It does not alter the release approval record.

## Promotion requirements

Promotion requires a new, versioned release bundle under `models/releases/`
with independently reproduced hashes and all evidence required by
`docs/APPROVED_RELEASES.json`: licensed training data, held-out Indian field
evaluation, unknown/OOD evaluation, calibrated thresholds, agronomist review,
redistribution approval, browser/server golden parity, and rollback identity.

The candidate index and source manifests must remain unchanged while that
review is pending. Do not copy candidate files into `models/releases/` as a
shortcut, and do not add them to the approved release record without the
corresponding evidence.
