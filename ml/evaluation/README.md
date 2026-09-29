# Crop-health evaluation protocol

This protocol is mandatory for a `crop-health-v0.1` release. A notebook accuracy
number on PlantVillage is not release evidence.

## Required partitions

| Partition | Purpose | Rule |
|---|---|---|
| Development train | Fit weights | Images may include licensed public warm-start data and local captures. |
| Validation | Tune model, threshold, margin and quantization choices | No image/near-duplicate/field-date group may appear in training. |
| Final field test | Release report | Held out by farm/plot and capture date; not consulted until a candidate is frozen. |
| Challenge / unknown | Rejection measurement | Other crops, unlisted diseases/pests, healthy look-alikes, soil/hands/tools, blurred/dark/overexposed photos. |

## Report every release

- dataset manifest revision; class counts; field/date/device distribution; label-review method; consent/license;
- macro-F1 and per-class precision/recall with confusion matrix on the final field set;
- unknown true-rejection and supported-input false-rejection on the challenge set;
- supported-input rejection must count as a false negative in per-class recall
  and macro-F1, with coverage reported separately;
- calibration method and reliability figure, if a score is displayed;
- float versus INT8 metrics on the same fixed test set;
- model package size, SHA-256, cold/warm p50 and p95 latency, peak memory, thermal/battery observation on the target phone;
- failure examples and a written decision: release, narrow scope, or do not release.

## Minimum test fixture shape

`fixtures/crop_health/<case_id>/`

- `image.jpg` (or a non-sensitive synthetic/test asset)
- `expected.json` conforming to `../contracts/crop-health-result.schema.json`
- `metadata.json`: crop, stage, field group, capture date, source/license and label-review status

Test fixtures must include at least one valid supported case, unsupported crop,
blurred/poor capture, unknown disease/look-alike and provider-unavailable case.
