# PlantDoc external tomato check — 9 September 2026

## Purpose and boundary

This is a deliberately small, exploratory cross-domain check of the selected
EfficientNetV2-B0 dynamic TFLite tomato specialist. It is **not** an
independent farmer-phone field evaluation and cannot satisfy any field-release
gate. Its value is showing that high controlled-image accuracy does not transfer
reliably to a separate image source.

## Reproducible source

- Dataset: [PlantDoc](https://github.com/pratikkayal/PlantDoc-Dataset), CC BY
  4.0 according to its repository README.
- Revision: `5467f6012d78d1c446145d5f582da6096f852ae8`.
- Materializer: `training/materialize_plantdoc_tomato_external_test.py`.
- Known tomato subset: six images each for `early_blight`, `healthy`,
  `late_blight`, and `leaf_mold` (24 total), mapped from four PlantDoc test
  directories.
- Non-tomato OOD subset: six each from `Bell_pepper leaf`, `Corn leaf blight`,
  and `Apple leaf` (18 total).
- Images remain ignored local evaluation data. `SOURCE_MANIFEST.tsv` binds each
  local copy to its upstream path.

## Dynamic TFLite result

The exact artifact in controlled-demo manifest v0.3 scored:

| Scope | Score/margin | Known coverage | Accepted accuracy | Macro-F1 | OOD rejection |
|---|---:|---:|---:|---:|---:|
| PlantVillage controlled validation (400 images) | 0.00 / 0.00 | 100% | 97.75% | 0.9775 | not measured |
| PlantDoc external tomato (24 images) | 0.00 / 0.00 | 100% | 45.83% | 0.3906 | not measured |
| PlantDoc known + non-tomato OOD | 0.70 / 0.15 | 54.17% | 53.85% | 0.2674 | 83.33% (15/18) |
| PlantDoc known + non-tomato OOD | 0.80 / 0.15 | 33.33% | 50.00% | 0.1875 | 94.44% (17/18) |

At the current runtime gate, leaf-mold recall was 0/6 and healthy recall was
0/6 on this small external set. Increasing the threshold did not recover
useful known-image performance. Therefore no threshold is promoted from this
experiment, and v0.3 stays review-only.

## Consequences

1. Do not cite the PlantVillage 97.75% figure as farmer-field accuracy.
2. Do not use PlantDoc’s 24-image subset to claim a field-release failure rate
   either; it is too small and sourced from web images rather than the target
   farmer/phone/region distribution.
3. The result does validate the existing fail-closed design: vision output must
   remain ranked screening evidence, never treatment or pump authority.
4. The next useful investment is consented, agronomist-reviewed local data with
   field/date/device-disjoint partitions—not another backbone or threshold
   sweep.
