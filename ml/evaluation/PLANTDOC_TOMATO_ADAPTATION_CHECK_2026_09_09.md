# PlantDoc tomato adaptation experiment — 9 September 2026

## Decision

**Rejected.** Do not replace the controlled-demo specialist, mount this model
in the backend, or tune the runtime confidence gate from this result.

## Protocol

- Source: [PlantDoc Dataset](https://github.com/pratikkayal/PlantDoc-Dataset),
  revision `5467f6012d78d1c446145d5f582da6096f852ae8`, CC BY 4.0 according to
  its repository README.
- Materializer: `training/materialize_plantdoc_tomato_specialist.py`.
- Labels: early blight, healthy, late blight and leaf mold.
- Development data: 45 source-`train` images per label for training (180) plus
  a disjoint 10 source-`train` images per label for validation (40).
- External check: six source-`test` images per label (24). It is deliberately
  named `external_test`, not a field test: these public web images are not
  consented Indian farmer-phone evidence.
- Candidate: ImageNet-pretrained TF Hub EfficientNetV2-B0, staged head warm-up
  and fine-tuning, seed 42; dynamic-range TFLite export.

## Results

| Scope | Acceptance policy | Coverage | Accepted accuracy | Macro-F1 |
|---|---:|---:|---:|---:|
| Development validation (40) | Trainer accuracy | n/a | 55.00% | not separately computed |
| Reserved PlantDoc external test (24) | 0.00 / 0.00 | 100% | 29.17% | 0.2530 |
| Reserved PlantDoc external test (24) | 0.70 / 0.15 | 0% | 0% | 0.0000 |

Leaf-mold recall was 0/6 on the reserved external subset. The model’s raw
accuracy is below chance-adjusted usefulness for the four supported labels, and
the normal safety gate rejects every image. This confirms that fine-tuning a
high-capacity TF Hub backbone on only 180 public source-train images is not a
viable route to better field performance.

## What this changes

The approved controlled-demo artifact remains unchanged and explicitly
demo-only. The next accuracy investment is consented, agronomist-reviewed
target-region farmer-phone data with a true field/date/device-disjoint split,
plus unknown/OOD images—not another public-data fine-tuning pass.
