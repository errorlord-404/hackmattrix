# KisanSathi product requirements

Version: proposed 1.0
Date: 5 September 2026
Basis: supplied SIH26180 brief, inspected working tree and [research findings](RESEARCH.md)
Delivery plan: [Implementation plan](IMPLEMENTATION_PLAN.md)

## Product outcome

Help a farmer recognize supported crop problems, understand water and climate risks, choose an appropriate action and record what happened, even with intermittent internet. Over time, connect that operational history to crop planning, procurement, harvest, sale and financial decisions.

For the SIH demonstrator, success means a verified local observation-to-action workflow for a declared crop and test environment. Higher yield, lower cost and better water efficiency are outcomes to evaluate. They must not be advertised as established before a comparative field trial.

The supplied Qualcomm statement is the provisional alignment target. Organizer category, exact wording, supported hardware requirements and submission rules remain to be verified. This PRD does not invent a mandatory board, accuracy threshold or SIH judging weight.

## Users and operating context

| User | Primary need | Product responsibility |
|---|---|---|
| Farmer or farm manager | See what needs attention and act without technical expertise | Simple local-language action, reason, timing and missing information |
| Field operator/family member | Carry out irrigation, scouting and tasks | Assigned task, clear scope, confirmation and outcome record |
| Agronomist/KVK/FPO partner | Review ambiguous problems and improve guidance | Evidence bundle, correction history and reviewed crop knowledge |
| Device installer/maintainer | Keep observations/control dependable | Enrollment, placement, calibration, diagnostics and replacement history |
| Vendor/buyer | Provide a comparable quote or purchase specification | Scoped listing/quote with expiry; no implied booking |
| Team/admin | Operate providers and evaluate quality | Source freshness, model version, failures, consent and audit records |

Assume a smallholder pilot, Android farmer device, one water-control node and inconsistent WAN access. Confirm actual crop, locality, electrical installation, water source and phone/SoC during the first implementation gate. Do not assume all farms have reliable Wi-Fi, paid data plans, drones or homogeneous soil.

## Delivery scope

D0 is the foundation milestone. D1 is the SIH field demonstrator. D2 is a supervised local pilot. D3 is the broader commercial lifecycle.

| Delivery | Included | Explicit boundary |
|---|---|---|
| D0 foundation | Farm identity, typed units, crop stage, source/freshness, action and model contracts | No claim of production field performance |
| D1 demonstrator | Supported offline crop screening, pest evidence, nutrient-stress screening, calibrated water sensing, irrigation recommendation and bounded low-voltage control, weather/heat/waterlogging alerts, history/tasks, offline UI | One crop/region/target device; other crops return unsupported; physical mains deployment separately engineered |
| D2 pilot | Real installation, farmer/expert review, lab soil reports, robust sync, inventory/ledger, harvest tasks, dated vendor quotes, net market comparison and disaster evidence | Quotes and public prices are not guaranteed fulfillment |
| D3 lifecycle | Multi-season crop/variety economics, validated forecasting, advanced digital twin, storage/grade optimization, export/organic workflows and buyer integration | Each model/integration needs independent data and acceptance gates |

Keep existing market, scheme, machinery and finance interfaces available as supporting features. Do not make broad marketplace completion a prerequisite for the crop-health/water demonstration.

## Core journeys

### Establish a field and crop cycle

The farmer draws or confirms a boundary, records area and units, previous crop, planting date, water access and current crop. The app asks for missing information only when it changes a decision. The farmer can say “I do not know.” The field shows which values are measured, reported, estimated or missing.

The calendar suggests the expected stage but distinguishes it from an observed stage. Replanting, crop failure, termination and multiple harvests are supported events. Actions and reports remain attached to the original cycle.

### Inspect a crop problem

The farmer selects a field and captures guided views. The app checks capture quality, runs the supported model locally, and returns possible findings with evidence and scope. Ambiguous symptoms trigger an additional observation or expert review. Nutrient findings are “possible stress” unless suitable evidence supports a more specific conclusion.

The farmer sees the next step, timing and rationale. A treatment suggestion references reviewed crop-specific content and relevant restrictions. The app records the task and asks for a follow-up observation. It does not treat the language model's free-form answer as a treatment authority.

### Decide and perform irrigation

The app combines valid root-zone observations, crop stage, soil parameters, recent applications and the available forecast. It shows an amount/range, why the decision is timely and when to reassess. Forecast rain can reduce or defer water only if the selected conservative scenario avoids unacceptable stress before expected rain.

In manual mode, the farmer authorizes a bounded run. In automatic mode, the farmer has already authorized a limited policy for a field/zone/time period; the local controller can execute within those limits. A language-agent conversation cannot silently expand the policy.

The UI distinguishes recommended, authorized, sent, acknowledged, running, completed and faulted. Flow or other physical feedback establishes that water was delivered. A communication acknowledgement alone does not.

### Work without WAN

The app retains field history, approved guidance, the current model, tasks and local observations. Camera inference works locally. Missing fresh remote weather and market updates are visible. New records enter an outbox and synchronize later without duplicate tasks, money entries or irrigation events.

Sensor/controller operation does not require an LLM, speech API or cloud broker. A phone absent from the farm must not disable the controller's stop limits and manual control.

### Prepare for and recover from a hazard

The system receives official warnings when connected and detects supported local conditions from current sensors. It associates the warning with relevant fields and practical preparation tasks. It tracks acknowledgement and expiry/update status.

After damage, the farmer captures location/time/evidence, records damage and seeks appropriate inspection or testing. The product helps prepare insurance/scheme information with source and deadline. It does not promise claim acceptance or infer whole-field contamination from one probe.

### Plan buy harvest and sell

The farmer compares eligible crops/varieties using expected ranges, required cash/water and quality priorities. Selected choices create tasks and input requirements. Existing inventory reduces purchases.

The service compares current offers including delivery and overhead. At harvest, lot quality, quantity, timing and buyer acceptance define sale options. The ledger separates cash flow, sale proceeds and season profit. A market or storage recommendation shows assumptions and sensitivity.

## Functional requirements and acceptance

| ID | Requirement | Delivery | Acceptance evidence |
|---|---|---|---|
| FARM-01 | Farm, field and zone identity with boundary/area provenance | D0 | Two fields retain independent histories; invalid polygon/area rejected or flagged |
| FARM-02 | Previous crops, inputs, yield/grade and residue history | D1 records, D2 completeness | Prior cycle remains queryable after new planting |
| CROP-01 | Crop-specific stages and dated stage events | D0 | Invalid transition handled; estimated stage cannot overwrite farmer-confirmed stage silently |
| CROP-02 | Calendar-generated tasks and explicit farmer correction | D1 | Changed sowing date recalculates pending tasks with visible changes |
| OBS-01 | Typed observations with depth, method, source and quality | D0 | Unit mismatch, stale, impossible and duplicate readings tested |
| OBS-02 | Sensor registry, pairing and calibration lifecycle | D1 | Unpaired device cannot write to another field; expired calibration visible |
| HEALTH-01 | Guided capture and local supported-crop inference | D1 | WAN-disabled test produces versioned result from local artifact |
| HEALTH-02 | Pest detection/count evidence for a declared supported set | D1 | Boxes/counts tested on independent field images; unsupported species not confidently relabeled |
| HEALTH-03 | Nutrient-stress screening with alternative explanations | D1 | Same yellow-leaf photo with differing water/lab context does not force one nutrient dose |
| HEALTH-04 | Expert review, correction and follow-up | D2 | Correction preserves original model output and review provenance |
| WATER-01 | Root-zone water balance and bounded schedule | D1 | Dry-soil/rain-day-four case does not blindly defer irrigation |
| WATER-02 | Independent local control with time/volume bounds and feedback | D1 bench, D2 farm | Duplicate/expired command, sensor fault, dry run and manual stop cases pass |
| WATER-03 | Water use and irrigation outcome records | D1 | Applied volume agrees with validated flow measurement within declared tolerance |
| RISK-01 | Source-aware weather and official alerts | D1 | Wrong-field forecast test, stale data, cancellation and expired alerts handled |
| RISK-02 | Local heat/waterlogging/water-stress detection | D1 | Thresholds belong to crop policy; replay clearly marked simulation |
| TASK-01 | Recommendation becomes tracked work | D1 | Owner/date/dependency/status/evidence retained; completion not inferred from advice |
| OFFLINE-01 | Local state, cached guidance and durable outbox | D1 | Airplane-mode journey and crash/restart retain records |
| OFFLINE-02 | Reconciliation and conflicts | D2 | Duplicate/out-of-order sync does not repeat actions or corrupt history |
| VOICE-01 | Local language with preserved numbers and units | D1 | Critical slots read back; misunderstood negation/quantity requires correction |
| VOICE-02 | Offline usable fallback | D1 | Farmer can inspect status and stop/record work without remote speech |
| SOIL-01 | Lab report import with reviewed extraction | D2 | OCR output cannot become a trusted lab value before confirmation |
| INPUT-01 | Inventory and consumption by product/lot | D2 | Purchase and application update stock with compatible units |
| BUY-01 | Vendor search and delivered quote comparison | D2 | Expired/incomplete quotes excluded from definitive lowest-cost ranking |
| FIN-01 | Ledger, receivables, liabilities and crop attribution | D2 | Loan principal does not count as income; corrections preserve audit history |
| HARVEST-01 | Readiness tasks, harvest lot, grade and loss | D2 | Partial harvests and assay/image grade distinction supported |
| SELL-01 | Latest comparable market data and net proceeds | D2 | Old prices do not outrank fresh records as if live; costs counted once |
| PLAN-01 | Constraint-based crop/variety options and scenarios | D2 |
| PLAN-02 | Validated multi-season yield/price/rotation estimates | D3 | Rolling backtest or local calibration beats declared baseline before release |
| STORAGE-01 | Sell/store alternative with loss, cost and cash needs | D3 | Scenario sensitivity and liquidity constraints visible |
| CERT-01 | Organic/export requirements and traceability | D3 | Crop/destination/source effective date and verified status recorded |
| RECOVERY-01 | Disaster evidence and policy-specific assistance | D2 | Document checklist generated without asserting eligibility not established |
| AGENT-01 | Farmer-scoped tool access and shared service behavior | D0/D1 | UI and agent produce the same calculation for identical inputs |
| AGENT-02 | Durable action authorization and execution audit | D1 | Wrong field, changed payload, expired authority and replay blocked |
| OPS-01 | Versioned model/content/config and rollback | D1 | Interrupted update leaves prior valid package usable |

PLAN-01 acceptance: infeasible candidates are excluded with reasons; every remaining option shows missing inputs and low/base/high economic assumptions. No unsupported crop receives a fabricated optimized recommendation.

## Product behavior rules

Every recommendation must answer what, why, when, for which field/cycle, based on which observations, and what uncertainty remains. Include cost/water implications when supported. Avoid numerical confidence if it has not been calibrated; use evidence-quality and missing-data explanations.

Use local farmer units in presentation with explicit conversions. Store canonical quantities. Preserve field name, amount, unit, date, negation and action target through the speech pipeline.

No-image, stale-sensor, unavailable-provider and unsupported-crop states are ordinary workflows. They must not display a healthy crop, safe soil, no hazard or zero cost by default.

User confirmation applies to the specific payload/version. Selecting a quote or authorizing an irrigation policy is not consent to future unrelated purchases or broader control. Routine actions within an already authorized automation policy should not demand repeated conversational approval.

Expose provenance and technical metadata in details, not in the main farmer instruction. A farmer-facing message can say “The soil reading is old; check moisture before watering.” It need not mention MQTT, schema versions or QNN.

## Proposed quality targets

These are initial engineering release targets, not organizer thresholds or measured results. Freeze them after hardware selection and agronomist review; report actual values and uncertainty.

| Dimension | Initial target | Measurement |
|---|---|---|
| Crop-health quality | Macro-F1 at least 0.85 and recall at least 0.85 for each released actionable class | Independent local test set; class support and confidence intervals reported; otherwise narrow scope |
| Unknown handling | At least 90% rejection of the defined unsupported/poor-input challenge set | Also report false rejection on supported inputs; adversarial set is not universal coverage |
| Quantization | No more than 2 percentage points macro-F1 loss against selected float baseline | Same fixed local test set |
| Local response | Camera-to-result p95 at most 2 seconds for chosen capture protocol | Exact phone/SoC/OS, cold/warm cases and thermal conditions recorded |
| Sensor validity | Meet declared reference/calibration tolerance over operating range | Lab/gravimetric/reference comparison; tolerance selected for the actual sensor and soil |
| Actuation correctness | All enumerated control-fault acceptance cases pass; no unbounded execution | Hardware-in-loop evidence, controller logs and physical feedback |
| Stop response | Bench target within 2 seconds of local stop/fault detection | Field installation must establish an appropriate independently reviewed response bound |
| Offline operation | Core journey usable during a 24-hour WAN outage | Device-local records, inference, guidance and controller policy tested |
| Data integrity | No duplicated physical actions or ledger entries in replay/crash tests | Event and command reconciliation evidence |
| Voice slots | 100% exact critical values in released action payloads after user correction/confirmation | At least 100 scripted and farmer-recorded command cases, reported separately |
| Usability | At least 80% independent completion of core journeys in formative study | At least 5–10 consenting pilot users; report small-sample limitations |
| Impact | Measure water/input/cost and crop outcomes against defined baseline | No fixed savings/yield percentage promised before trial |

A pooled score must not hide an unusable critical disease class. Passing a small pilot is a release decision within the stated scope, not proof of all-India performance.

## Impact and economics measurement

Measure applied water in liters and equivalent depth for a known area, time below/above agronomic water limits, energy where metered, input amount/cost, crop damage, marketable yield/grade and realized sale proceeds. Record weather and differences in management.

Use a paired-plot or otherwise agronomist-designed comparison where practical. Predefine the baseline and outcome period. A tabletop tank demonstration can validate flow accounting and control behavior but cannot demonstrate seasonal yield improvement. Simulated disasters and historical replay must be visibly labeled.

Measure recurring operating costs: connectivity, speech/LLM/provider calls, storage, model training, expert review, sensor maintenance, calibration, replacements, installation and support. Hardware purchase price alone is not total cost of ownership.

## Dependencies and release gates

| Gate | Required evidence | If absent |
|---|---|---|
| Brief and pilot | Official statement plus crop/site/hardware owner | Continue reusable software; keep competition claims provisional |
| Agronomy | Reviewed crop-stage/water/treatment scope | Screening/manual workflows only |
| Data rights and quality | Chosen releases, licenses, local labels/test split | No production diagnostic claim |
| Hardware | Target profile, calibrated sensors and controller fault tests | Bench/manual demonstration only |
| Connectivity | Offline journey and sync recovery | Do not claim field-deployable offline workflow |
| Economics | Dated comparable quote/price and costs | Scenario calculation with missing-data disclosure |
| Real-world outcomes | Controlled or carefully documented field measurements | Demonstrate functionality; label impact as hypothesis |

## Product risks and decisions

The major risk is breadth displacing the evidence needed for the core. Maintain a visible supported-crop/device matrix and a per-feature maturity state: implemented, tested locally, field-validated or planned.

Use a phone for camera diagnosis and local UI, with a microcontroller for continuous sensing and bounded control. If continuous unattended image analysis is a hard organizer or deployment requirement, add a powered fixed edge camera/gateway and separately validate its image distribution and runtime. A farmer phone cannot supply continuous field images while away.

Maintain the cloud/desktop agent as an optional richer interface. The critical local loop must continue when the model subscription, server, WAN or speech provider is unavailable.

The farmer remains the decision maker for crop choice, tradeoffs, purchases and authorized automation scope. KisanSathi is decision support with observable actions and outcomes, rather than a promise of guaranteed profit.
