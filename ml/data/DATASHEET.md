# Crop-health field-data datasheet and capture protocol

Use this before collecting any image intended for KisanSathi model improvement.
It is a **data-governance and quality record**, not permission to upload images
or a claim of agronomic validity. Keep real images and identifying data outside
Git.

## Scope record (complete before collection)

| Item | Required decision |
|---|---|
| Pilot crop and variety | One named crop/variety for this dataset version. |
| District/state and season | Target locality and capture window; never publish precise farmer locations. |
| Supported labels | Agronomist-approved classes, healthy class and explicit exclusions. |
| Target device | Phone/SoC/camera model(s) for final TFLite evaluation. |
| Agronomy reviewer | Organisation, review protocol and date. |
| Data steward | Owner of consent, protected storage, access and deletion handling. |

Do not mix crop-specialist taxonomies in one run. Put unlisted disease, pest,
nutrient deficiency, soil/background, hand/tool, blurred and ambiguous images
in a separately labelled unknown/OOD challenge collection; never relabel them
as a supported disease merely to grow a class.

## Per-capture metadata (private JSON/CSV; one record per image)

```json
{
  "image_id": "random-uuid",
  "sha256": "image-file-checksum",
  "consent_for_model_improvement": true,
  "consent_record_id": "protected-consent-reference",
  "capture_time_local": "2026-09-09T10:30:00+05:30",
  "field_group": "one-way-anonymized-field-id",
  "capture_session_group": "same-visit-group",
  "district_state": "coarse-pilot-location",
  "device_model": "phone/camera model",
  "crop": "tomato",
  "variety": "farmer-reported-or-unknown",
  "growth_stage": "vegetative|flowering|fruiting|maturity|unknown",
  "candidate_label": "unreviewed-farmer-observation",
  "agronomist_label": null,
  "label_evidence": "visual|lab|extension-visit|unknown",
  "severity_band": "none|mild|moderate|severe|unknown",
  "capture_condition": "daylight|shade|flash|rain|unknown",
  "quality_notes": "blur/glare/occlusion/multiple-leaves or empty",
  "storage_uri": "protected-local-path-or-object-reference"
}
```

`field_group` must be stable for a plot/farm but non-reversible in exported
queues. Keep GPS, farmer identity and consent documents only in the authorised
private store. A `candidate_label` is never ground truth; only an agronomist
label from documented expert review can enter a training split.

## Capture, review and split procedure

1. Obtain revocable informed consent before capture; explain model-improvement
   use, storage, reviewer access and withdrawal.
2. Capture whole-plant context plus 2–3 close leaf/fruit views per visit. Give
   all visit images one `capture_session_group`; never scatter that group across
   training and test partitions.
3. Prefer daylight, avoid glare, record crop/stage/device and write `unknown`
   when uncertain. Do not digitally change lesion morphology.
4. An agronomist reviews candidate labels independently. Retain rejected or
   ambiguous items in protected audit storage as potential unknown/OOD evidence.
5. Run `build_diagnosis_review_queue.py` only on authorised stores; it copies
   no images. Then run `build_reviewed_field_split.py`, which keeps every field
   in exactly one of `train`, `validation` or `field_test`.
6. Keep `field_test` and unknown/OOD data untouched until model, threshold and
   TFLite choice are frozen. `materialize_reviewed_split.py` checks checksums
   before creating protected folders.

## Reject from supervised training

Do not train on an image if consent is absent/withdrawn, its source checksum is
missing, field/session grouping is missing, crop is out of scope, image quality
is unusable, or agronomist review is incomplete. Never use a model prediction
alone to manufacture a label.
