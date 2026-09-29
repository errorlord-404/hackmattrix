# Local CNN training scaffold

This is a local, vendor-neutral starting point for two classifiers:

1. **Crop router:** labels are crops, for example `tomato`, `rice`, `cotton`,
   `wheat`, plus an intentionally collected `other_or_unknown` label.
2. **Specialist classifier:** train a separate model for one confirmed crop, for
   example `healthy`, `early_blight`, `late_blight`, `leaf_mold`,
   `other_or_unknown` for tomato.

The directory shape is deliberately simple:

```text
private-data/crop-router/
  train/tomato/*.jpg
  train/rice/*.jpg
  val/tomato/*.jpg
  val/rice/*.jpg
```

For a controlled-image **demo only**, `prepare_plantvillage_crop_router.py`
creates a four-crop split from a local checkout of PlantVillage:

```powershell
python ml/training/prepare_plantvillage_crop_router.py `
  --plantvillage-color C:\path\to\PlantVillage-Dataset\raw\color `
  --output private-data/crop-router-demo --per-crop 500
```

It must never be used as release evidence: PlantVillage's controlled backgrounds
do not represent farmer-phone field images.

If a full checkout is unreliable, a local metadata clone can be used to fetch a
bounded demo sample only:

```powershell
python ml/training/download_plantvillage_demo_subset.py `
  --repository C:\path\to\PlantVillage-Dataset `
  --output private-data/plantvillage-router-source --per-crop 80
```

Then split the images with `prepare_plantvillage_crop_router.py`. The downloader
is deliberately limited to named supported crops and retains no raw result in
Git; record the upstream revision and license in the dataset datasheet.

The same bounded approach is available for the first **tomato specialist**
demo. It covers only healthy, early blight, late blight and leaf mold; it is not
an all-disease tomato model:

```powershell
python ml/training/download_plantvillage_tomato_specialist_demo.py `
  --repository C:\path\to\PlantVillage-Dataset `
  --output private-data/tomato-specialist-source --per-label 20
```

For the Kaggle PlantVillage archive used in the local demonstration, extract
only the four selected tomato folders and split up to 500 images per label:

```powershell
python ml/training/prepare_tomato_specialist_split.py `
  --source C:\path\to\PlantVillage `
  --output private-data/tomato-specialist --per-label 500
```

Install only in a training environment:

```powershell
python -m pip install -r ml/training/requirements-training.txt
python ml/training/train_classifier.py --dataset private-data/crop-router --output private-artifacts/crop-router-v0.1.pt --architecture mobilenet_v3_small
```

Repeat with `private-data/tomato-health` for the specialist. This script's
validation accuracy is only an iteration signal. Follow `../evaluation/README.md`
before calling any checkpoint a release. Do not commit farmer images or trained
weights without written consent/license and an artifact manifest.

## TensorFlow Hub / TensorFlow Lite deployment benchmark

The PyTorch scripts remain useful for the server-demo path. For Android and
Qualcomm-target deployment, benchmark TensorFlow Hub **MobileNetV3-Small** for
the crop router, **MobileNetV3-Large** as the low-latency fine-tunable
specialist, **EfficientNetV2-B0** as the accuracy-versus-latency specialist
comparison, and **EfficientNet-Lite0** as the frozen feature-extractor
alternative. All start from ImageNet pretrained features, then learn only the
approved crop labels. Select the release candidate from field-held-out quality,
unknown rejection and target-device latency—not from the backbone name.

```powershell
python -m pip install -r ml/training/requirements-tfhub.txt
python ml/training/train_tfhub_classifier.py `
  --dataset C:\path\to\tomato-specialist `
  --output ml\private-artifacts\tomato-efficientnet-lite0 `
  --backbone efficientnet_lite0 --freeze-backbone --epochs 8
python ml/training/export_tfhub_tflite.py `
  --saved-model ml\private-artifacts\tomato-efficientnet-lite0 `
  --representative-data C:\path\to\tomato-specialist\train `
  --output-dir ml\private-artifacts\tomato-efficientnet-lite0-tflite
```

For a fine-tunable backbone such as `mobilenet_v3_small`, `mobilenet_v3_large`
or `efficientnet_v2_b0`, the trainer performs
transfer learning in two deliberate phases: it first trains the new disease
head with the ImageNet backbone frozen, then unfreezes it at the lower
`--fine-tune-learning-rate` (default `3e-5`). This is the recommended starting
point for the specialist model; it reduces catastrophic forgetting on small
datasets. For example:

```powershell
python ml/training/train_tfhub_classifier.py `
  --dataset C:\approved-field-data\tomato-health `
  --output ml\private-artifacts\tomato-mobilenetv3-large `
  --backbone mobilenet_v3_large --epochs 12 --head-epochs 3 `
  --learning-rate 3e-4 --fine-tune-learning-rate 3e-5
```

Run the same approved, field-disjoint split with EfficientNetV2-B0 before
choosing an accuracy-first specialist:

```powershell
python ml/training/train_tfhub_classifier.py `
  --dataset C:\approved-field-data\tomato-health `
  --output ml\private-artifacts\tomato-efficientnetv2-b0 `
  --backbone efficientnet_v2_b0 --epochs 12 --head-epochs 3 `
  --learning-rate 3e-4 --fine-tune-learning-rate 3e-5
```

It is a benchmark candidate, not an automatic upgrade: record macro-F1,
per-disease recall, unknown rejection, quantized accuracy and latency/battery
on the target phone alongside MobileNetV3-Large.

`efficientnet_lite0` is a TF1 Hub feature-vector export in this pipeline, so
it is head-only unless replaced with a separately verified trainable source.
The trainer therefore defaults to fine-tunable `mobilenet_v3_large`; pass
`--freeze-backbone` explicitly for EfficientNet-Lite0.

The trainer defaults to `--class-weight balanced`: it derives inverse-frequency
weights from the training label folders and records both raw counts and weights
in `kisansathi_metadata.json`. This helps avoid a majority healthy class hiding
poor disease recall in an imbalanced field dataset. It does not alter the
validation split or turn controlled-image validation into field evidence. Use
`--class-weight none` only when a documented sampling strategy already balances
the approved training set.

The exporter makes FP32, dynamic-range, and calibrated INT8 `.tflite` candidates. Compare
class recall, unknown rejection and model-device latency before selecting one.
These TensorFlow Hub artifacts are still not release evidence without a
field-held-out evaluation.

Measure each exported candidate on the final **field-held-out** split, with a
separate non-target/unknown challenge set. The evaluator reports confusion,
macro-F1, per-class precision/recall, supported-input rejection and unknown
true-rejection at the exact configured score/margin gates:

```powershell
python ml/training/evaluate_tflite_classifier.py `
  --model ml/private-artifacts/tomato-efficientnet-lite0-tflite/model-int8.tflite `
  --labels ml/private-artifacts/tomato-efficientnet-lite0-tflite/labels.json `
  --dataset C:\approved-field-data\tomato-health\field-test `
  --unknown-dataset C:\approved-field-data\tomato-health\unknown-ood `
  --minimum-score 0.70 --minimum-margin 0.15 `
  --output ml\private-artifacts\tomato-efficientnet-lite0-tflite\field-report.json

The report is evidence, not a release decision. Copy its report IDs and the
exact artifact/label checksums into a reviewed manifest only after target-device
latency and agronomist review are complete.

Compare only reports created from the same field-held-out partition, ordered
labels, unknown/OOD challenge set and score/margin policy. The comparison tool
rejects mismatched evidence rather than calling a higher number “more accurate”:

```powershell
python ml/training/compare_tflite_candidates.py `
  --report mobilenet_v3_large=ml\private-artifacts\tomato-mobilenetv3-large\field-report.json `
  --report efficientnet_v2_b0=ml\private-artifacts\tomato-efficientnetv2-b0\field-report.json `
  --output ml\private-artifacts\tomato-specialist-comparison.json
```

This comparison is not a release decision. It has no target-device thermal,
battery or latency evidence and cannot change a manifest.

### External-domain check (PlantDoc, evaluation only)

`materialize_plantdoc_crop_router.py` similarly creates a bounded four-crop
PlantDoc train/test experiment without checking out Windows-incompatible
filenames. It is a data-materialization utility, not a claim that PlantDoc is
representative of Indian farmer-phone images. Keep the crop-router output in
suggestion/confirmation mode until field-held-out evidence exists:

```powershell
python ml/training/materialize_plantdoc_crop_router.py `
  --repository C:\approved\PlantDoc-Dataset `
  --revision 5467f6012d78d1c446145d5f582da6096f852ae8 `
  --output C:\approved\plantdoc-crop-router `
  --per-crop 100 --val-per-crop 16
```

The first bounded MobileNetV3-Small experiment is deliberately rejected: it
achieved 64.06% raw held-out accuracy and only 12.5% tomato recall. See
`../evaluation/PLANTDOC_CROP_ROUTER_CHECK_2026_09_09.md`. Do not configure its
artifact in the backend.

For a clearly scoped external-domain **tomato specialist** experiment,
PlantDoc's source `train/` folder is split into development train/validation
sets, while its source `test/` folder is reserved as `external_test`. This is
useful to measure whether an ImageNet-pretrained TF Hub model can adapt to more
varied web imagery; it cannot replace farmer-phone release evidence or be mixed
with the separate PlantDoc external check:

```powershell
python ml/training/materialize_plantdoc_tomato_specialist.py `
  --repository C:\approved\PlantDoc-Dataset `
  --revision 5467f6012d78d1c446145d5f582da6096f852ae8 `
  --output C:\approved\plantdoc-tomato-specialist `
  --train-per-label 45 --val-per-label 10 --field-test-per-label 6
```

`materialize_plantdoc_tomato_external_test.py` can fetch a **bounded** subset
from an immutable local PlantDoc Git revision without checking out its
Windows-incompatible source filenames. It writes only sanitized evaluation
copies and an upstream-source manifest. It must not be used for training or as
farmer-phone release evidence:

```powershell
python ml/training/materialize_plantdoc_tomato_external_test.py `
  --repository C:\approved\PlantDoc-Dataset `
  --revision 5467f6012d78d1c446145d5f582da6096f852ae8 `
  --output C:\approved\plantdoc-tomato-external `
  --unknown-output C:\approved\plantdoc-nontomato-ood `
  --per-label 6 `
  --unknown-source-label 'Bell_pepper leaf' `
  --unknown-source-label 'Corn leaf blight' `
  --unknown-source-label 'Apple leaf'
```

Then pass the known and OOD folders to `evaluate_tflite_classifier.py`. The
first check is documented in
[`../evaluation/PLANTDOC_EXTERNAL_CHECK_2026_09_09.md`](../evaluation/PLANTDOC_EXTERNAL_CHECK_2026_09_09.md):
the controlled demo fell from 97.75% to 45.83% raw accuracy on its tiny external
tomato subset. That is a warning against deployment, not a new release metric.

## Field-data review queue (no automatic export)

Read [`../data/DATASHEET.md`](../data/DATASHEET.md) before collection. It defines
the private per-capture metadata, consent boundary, capture groups and expert
review needed for the commands below.

The farmer app can record consented diagnosis feedback, but it is not a
training label. An authorised data steward may create a local reviewer queue
from explicitly named farmer SQLite files; the command copies no images and
omits local paths unless expressly requested:

```powershell
python ml/training/build_diagnosis_review_queue.py `
  --farm-db C:\authorised\farm-state\farmer-a.sqlite3 `
  --output ml\private-artifacts\crop-health-review-queue.json
```

An agronomist must review each queue item, and a steward must make
field/date-disjoint train, validation, final-test and unknown/OOD splits before
the images can enter any TF Hub fine-tuning run.

After expert review, build a metadata-only field-disjoint split manifest. The
expert review file must use `crop-health-expert-review-v1` and contain an
explicit `approved` decision plus `agronomist_label` for every selected queue
item. This command rejects a split if any label is absent from any partition:

```powershell
python ml/training/build_reviewed_field_split.py `
  --review-queue ml\private-artifacts\crop-health-review-queue.json `
  --expert-review C:\authorised\agronomist-review.json `
  --output ml\private-artifacts\crop-health-field-split.json
```

Keep `field_test` untouched while tuning; create unknown/OOD photos separately.

Only after approval, create image folders from the split manifest. It refuses a
non-empty output, verifies every source checksum and requires an explicit data
steward acknowledgement; it never uploads the data:

```powershell
python ml/training/materialize_reviewed_split.py `
  --split-manifest ml\private-artifacts\crop-health-field-split.json `
  --output C:\authorised\tomato-health-field-dataset `
  --confirm-authorised-data-steward
```

Use the resulting `train/`, `validation/` and `field_test/` folders only after
checking their field-group manifest. Do not include `field_test` in tuning.
`train_tfhub_classifier.py` accepts the reviewed `validation/` name as well as
legacy demo `val/` folders, but rejects a dataset containing both names.

Before any local demonstration or release review, validate the manifest against
the exact local model and labels. A rejected demo still validates integrity but
remains review-only:

```powershell
python ml/training/validate_release_manifest.py `
  --manifest ml/releases/crop-health-tfhub-tomato-controlled-demo-v0.2.yaml `
  --repo-root .
```
```

`ml/orchestration/crop_router.py` enforces the safe route: uncertain crop → ask
the farmer; unsupported confirmed crop → stop; confident supported crop → invoke
the matching specialist. The backend/agent integration must preserve this status.

Evaluate the saved checkpoint before showing any score in the product:

```powershell
python ml/training/evaluate_classifier.py `
  --checkpoint ml/demo_artifacts/plantvillage-tomato-specialist-demo-v0.1.pt `
  --dataset C:\path\to\tomato-specialist\val
```

## Prototype data note

`prepare_plantvillage_crop_router.py` gives the team a reproducible source for a
demo checkpoint. On 7 September 2026, an attempted sparse image checkout from
the public PlantVillage repository stalled before any image blob was received;
no dataset or weight was added to this project. Obtain the dataset through a
reliable approved mirror/checkout, log its revision/license, and run the script
locally rather than silently substituting arbitrary internet images.
