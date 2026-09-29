# KisanSathi feasibility and architecture research

Research date: 5 September 2026
Audience: KisanSathi student engineering team and SIH proposal authors
Decision: what to build, reuse, validate and defer for the supplied SIH26180 brief
Companions: [Product requirements](PRD.md) and [Implementation plan](IMPLEMENTATION_PLAN.md)

## Executive assessment

The full farming lifecycle is a credible product direction. Most individual capabilities are technically possible. The difficult part is producing dependable local decisions from incomplete observations, operating without internet, and demonstrating that the resulting actions improve outcomes. Adding more neural networks does not solve missing measurements, unavailable vendor quotes, uncertain weather or unverified agronomic labels.

Prioritize a deployable crop-health and water-management system for one locally accessible crop and one pilot area. Use calibrated sensors, a compact image model, crop-stage rules, a local action controller and an understandable explanation. Keep crop planning, market comparisons, ledger and directories as supporting workflows. Build broader commerce, export operations and multi-season optimization after the field core works.

The three most consequential corrections are:

1. GPS and satellite images cannot deliver an exact daily weather forecast for an individual farm throughout its next growing season.
2. Low-cost NPK probes and leaf photos cannot be assumed to measure plant-available nutrients well enough to prescribe fertilizer.
3. A rain forecast four days away is not sufficient reason to withhold irrigation today. The crop may experience water stress before rain arrives.

These are scope corrections, not reasons to abandon the project. The recommended architecture combines observations, transparent agronomic calculations, specialist models and an agent that explains results and carries out bounded tasks.

## Scope and evidence boundaries

This research covers India, with Hindi/Marathi/English treated as an initial language assumption based on the existing repository. The pilot district, crop, farm partner, hardware model, budget and submission date are not confirmed. Tomato is used only as a possible development crop because relevant public image data exists; actual pilot selection must follow access to farms and expert labels.

The supplied problem statement is the working specification. Two community archives reproduce SIH26180 under Qualcomm and describe a hardware system with local intelligence, but their theme labels differ. The official SIH site/problem page could not be retrieved during this research. Therefore hardware category, exact wording, judging rules and deadlines require confirmation against the organizer's current statement. Do not treat an unofficial architecture or budget as an organizer requirement. [Community archive, explicitly unofficial](https://sih2026.vuce.in/orgs/qualcomm-inc), [independent community listing](https://github.com/jeevansai-hub/SIH-2026-/blob/main/ps_2026/README.md)

Repository findings describe working tree HEAD 3e5dfbc plus existing uncommitted changes, inspected on 5 September 2026. Source review covered application-owned frontend, desktop integration, Python MCP adapter, FastAPI services, schemas, storage and ingestion. The upstream Codex tree was mapped through its integration boundary; it was not exhaustively reread or compiled. No production feature was implemented in this research task.

Recommendations and acceptance targets below are engineering proposals. They are not measured project performance, quoted supplier prices or agronomic prescriptions. Official/API documentation establishes availability of an interface, not access by your account or successful integration.

## What is missing from the farming lifecycle

| Lifecycle point | Missing or under-specified capability | Why it changes the decision | Priority |
|---|---|---|---|
| Farm onboarding | Ownership/tenancy, consent, field boundary, management zones, area uncertainty, water source, soil texture/depth and access constraints | A crop suitable for a district may be impossible with this farm's water, labor or cash | Core |
| End of previous crop | Actual yield/grade, residue treatment, disease carryover, prior input applications, unpaid liabilities | Rotation must learn from outcomes and residual conditions | Core history; advanced optimization later |
| Pre-sowing | Water budget, seed lot authenticity/germination, land preparation, drainage, sowing window and contingency crop | Crop selection is a constrained decision, not a soil-to-label classifier | Core records |
| Rotation | Crop family, legumes, residue, pests, labor calendar and multi-year soil effects | Alternation alone does not guarantee better soil or income | Advisory first |
| Crop calendar | Phenology, observed stage, uncertainty, replanting and multiple harvests | Days after sowing are not an infallible crop-stage clock | Core |
| Establishment | Germination/stand counts, gaps, weeds, mortality, reseeding window | Problems arise before visible leaf disease | Core scouting tasks |
| Nutrition | Lab report ingestion, test method/units, organic matter, water quality, previous applications | NPK readings alone cannot define a safe dose | Core screening |
| Crop protection | Pest counting, weeds, mixed symptoms, beneficial insects, escalation and treatment follow-up | Detection must connect to appropriate action and outcome | Core supported scope |
| Water | Root-zone balance, flow, drainage, waterlogging, source availability, irrigation uniformity | Moisture thresholds alone omit crop stress and actual water use | Core |
| Equipment | Enrollment, calibration, power, offline range, maintenance, faults and replacement | A field deployment has recurring physical operating costs | Core |
| Tasks and labor | Owner, timing, dependencies, completion, evidence, cost and rescheduling | A recommendation does not prove an action occurred | Core |
| Inventory | Seed/fertilizer/pesticide lots, units, expiry, purchases and consumption | Avoids recommending inputs already owned; supports traceability | Pilot |
| Harvest | Maturity, weather window, pre-harvest intervals, worker/machine availability | Best sale price is irrelevant if quality or harvest readiness is wrong | Pilot |
| Post-harvest | Sorting, grading, assaying, packaging, storage humidity/temperature, spoilage | Quality, quantity and timing determine saleable value | Pilot |
| Selling | Buyer quote validity, acceptance grade, minimum lot, transport, payment delay/default | Reported mandi price is not a guaranteed price for this lot | Pilot |
| Finance | Cash flow versus accounting profit; credit, debt repayments, receivables and inventory valuation | A profitable season can still cause a cash shortage | Pilot |
| Disaster | Before/during/after tasks, official alerts, local detection, evidence, insurance and recovery testing | A risk score alone does not deliver recovery support | Core alerts; pilot recovery |
| Learning | Expert correction, farmer feedback, measured water/input/yield outcomes | Needed to establish that the system helps | Core |
| Accessibility | Offline manual workflow, local units, code-switching, speech confirmation, shared-device privacy | Farmers must still act when cloud speech or connectivity fails | Core |

The earlier vision also mentioned “neighbors”; this report interprets that as local labor, cooperative services and shared equipment. Social networking and autonomous outreach are not necessary for the field demonstrator.

## What is possible and what cannot be promised

| Proposed feature | Verdict | Defensible implementation or limit |
|---|---|---|
| Digital field map and history | Feasible now | Farmer-confirmed GeoJSON boundary, GPS accuracy, dated observations |
| Farm digital twin | Incremental | Start with a time-indexed field state; add calibrated crop/water simulation later |
| Best next crop | Feasible decision support | Filter constraints, then compare uncertain margins and rotation effects |
| Exact next-season micro-weather | Unsupported promise | Climate/seasonal scenarios for planning; short-range forecasts for operations |
| Local weather correction | Feasible with data | Bias correction and local risk estimates evaluated against station observations |
| Disease/pest diagnosis | Feasible for a bounded taxonomy | Field-tested model with unknown/poor-image outcomes and expert escalation |
| Nutrient concentration from a leaf photo | Not established | Screen possible causes; require appropriate soil/tissue evidence for dose decisions |
| Cheap universal NPK sensor | Not established | Validate the exact device against a laboratory across soils and moisture levels |
| Irrigation automation | Feasible | Independent controller, calibrated model, feedback, stop limits and manual override |
| Rain-aware irrigation | Correct with conditions | Compare likely rain timing with projected root-zone stress |
| Seasonal price forecasting | Feasible probabilistically | Backtested intervals and scenarios; no guaranteed future mandi price |
| Cheapest local procurement | Partly feasible | Lowest verified delivered quote among covered suppliers, with quote age/availability |
| Guaranteed highest profit | Unsupported | Uncertain yield, prices, rejection, weather, costs and payment risks remain |
| MSP support | Feasible navigation | Check crop/state/season/registration/procurement conditions |
| Organic/export support | Feasible workflow | Certification, residues, traceability and buyer specifications across the cycle |
| Crop yield guarantees from seed companies | Unverified generally | Check a named company's actual written guarantee and exclusions |
| End-to-end voice control | Feasible for bounded tools | Preserve numbers/units, authenticate actions and provide offline fallbacks |
| Disaster prediction and compensation | Limited | Distribute official warnings, detect local conditions, prepare evidence; do not guarantee either |

## Current codebase capability map

The repository already has a meaningful application foundation. A page, schema or tool name does not imply the underlying prediction or physical capability exists.

| Area | Current evidence | Remaining work |
|---|---|---|
| Manual interface | 17 React routes in src/routes/index.jsx: dashboard, fields/detail, map, crop guide, soil, weather, irrigation, pest, market, schemes, finance, machinery, AI, voice, reports, settings | Mobile offline storage, notification behavior, broader lifecycle workflows |
| Farm state | backend/app/farm_state/store.py has SQLite profile, fields, cycles/stage events, tests/readings, observations, irrigation history, reminders, alerts, diagnoses and reports | Device-local deployment/sync contract, migrations, transactional actions, tasks API, inventory/harvest/ledger |
| Crop stage | Start cycle, update stage and timeline endpoints/tools | Controlled crop-specific stages, transitions, estimated versus observed stage and task scheduling |
| Weather | Open-Meteo adapter with source timestamps, cache and explicit fixture mode | Issued/valid time distinction, model/grid identity, archive, official risk alerts, water-balance features |
| Irrigation | rules.py uses 35% or 40% target moisture and a 60% rain-probability deferral | Calibration, physical water balance, depth/units, constrained scheduling, flow feedback and actual control |
| Soil | Records tests/readings and simple pH/nitrogen screening | Valid units/methods, deficient versus missing state, paired lab validation and nutrient plans |
| Vision | assistants.py validates/stores diagnosis uploads but explicitly returns provider-unavailable/inconclusive | Training data, model artifact, local inference, crop-specific validation, review workflow |
| Market data | AGMARKNET/data.gov.in ingestion; price history/trends; net-realization formula | Historical coverage audit, latest comparable lot prices, routing/quotes, uncertainty, forecast evaluation |
| Machinery | Reference listings and contact interface | Supplier onboarding, availability, dated delivered quotes, logistics and fulfillment |
| Seeds/fertilizer/schemes | Catalog filtering/ranking and reference CRUD | Validated agronomy, eligibility rules, source versions, product lots and commercial terms |
| Finance | src/features/financeStore.js stores transactions in browser localStorage; stateless profit MCP tool | Shared durable ledger, liabilities/receivables, crop attribution, offline export and sync |
| Agent | agent/src/kisansathi_agent/server.py registers 47 tools; Python adapter calls REST and normalizes results | Strong authorization, intent-specific idempotency, bounded media references, more complete action handling |
| Desktop harness | Electron invokes installed codex app-server via desktop/codex-harness.cjs and local MCP plugin | Packaged runtime verification, request deadlines, production app identity and separate Android execution |
| Speech | Sarvam transcription/translation/synthesis adapters; local-language conversation integration | Actual provider tests, agriculture vocabulary, numeric slot checks, offline speech/recorded templates |
| IoT | Database representation and manual reading ingestion | No application-owned firmware, telemetry enrollment, MQTT/BLE protocol or pump control found |
| Model deployment | No application-owned .onnx/.tflite/.pt model artifacts found in the scoped search | Model registry, train/eval/export pipeline, target-device profiling and rollback |
| Satellite/rotation/yield/storage | Map/history and reference structures offer starting points | No validated satellite pipeline, rotation optimizer, yield/price model or storage optimizer found |

Current application route and tool counts were checked from source; FastAPI OpenAPI generation reports 61 paths. The Codex integration currently launches the executable named by CODEX_BINARY or codex on PATH. Keeping a fork in the repository does not mean that fork is the running binary.

### Priority correctness findings

1. backend/app/routers/farm_state.py:548 selects the latest weather snapshot without filtering to the requested field or coordinates. Another field's forecast can influence irrigation.
2. backend/app/farm_state/rules.py uses fixed moisture percentages and hand-assigned confidence values. Those numbers are not validated probabilities and must not authorize a pump.
3. soil_interpretation can return within_screening_ranges with no usable measurements. Nitrogen is compared against 280 without a unit/method-aware interpretation. Missing evidence needs its own state.
4. backend/app/routers/market_price.py compares all matching historical records; it does not first select the latest comparable record per market/variety/grade. Default transport fees are not route-based quotes.
5. backend/app/services/gov_scheme_mutator.py accepts but does not implement substantive eligibility criteria. State matching should be labeled scheme discovery.
6. X-Farmer-ID is explicitly a temporary local identity boundary, not authentication; the backend defaults to demo. Public reference mutations and broad CORS need review before network deployment.
7. MCP descriptions request confirmation, but descriptions/annotations do not enforce backend authorization. New physical or commercial actions need an application-owned authorization record.
8. tools.py derives idempotency from path and payload. Independent identical intentions may be conflated. store.py commits each statement, so action persistence and deduplication are not yet atomic.
9. Server-local SQLite is not automatically offline storage on the farmer's phone. Browser finance and server farm history are separate stores.
10. Source ingestion can discover a portal-rendered API key when none is configured. Prefer an issued project credential and explicit provider onboarding; HTML key discovery is a fragile production dependency.

The current .gitignore does exclude backend/data and SQLite databases. The earlier August audit's concern about those paths being unignored is superseded by HEAD 3e5dfbc.

### Verification performed

On 5 September 2026, the existing UI test passed (1), desktop tests passed (6), backend tests passed (14), and MCP adapter tests passed (10): 31 tests in total. Lint and Vite production build passed. The generated main JavaScript bundle is 639.50 kB before gzip and triggers the build's size warning. Python suites report dependency/deprecation warnings.

These checks do not verify crop-model accuracy, NPU execution, physical safety, offline synchronization, live Mongo/provider behavior, or a complete signed-in model-to-MCP-to-backend session. No Rust build, field trial or hardware test was performed.

## Model and data choices

### Choose the smallest model that passes the real task

| Task | Recommended first baseline | Alternatives worth comparing | Inputs and training evidence | Deployment |
|---|---|---|---|---|
| Next crop/rotation | Agronomic eligibility rules plus scenario ranking | Gradient-boosted yield/risk estimates; DSSAT/APSIM simulation | History, soil, irrigation, labor, finance, local trial/field outcomes | Rules local; training/simulation optional server |
| Sowing window | Crop calendar plus weather/soil constraints | Probabilistic risk model after local labels exist | Soil temperature/moisture, near-term forecasts, cultivar/window | Local rules with cached forecast |
| Leaf disease | Fine-tuned MobileNetV3-Small | EfficientNet-B0 on same split | Expert-labeled local photos plus suitable public pretraining data | On-device |
| Visible pests | YOLOX Nano/Tiny; compare supported YOLOX-Small | Licensed Ultralytics nano detector | Bounding boxes, species/life stage, crop context; IP102 if permitted | On-device |
| Lesion severity | Human ordinal severity first | Small U-Net-style segmentation model | Validated masks or severity labels | On-device if useful |
| Nutrient stress | Rules and possible-cause classification | Image encoder plus tabular fusion after paired measurements | Photos, stage, soil/tissue reports, water, recent applications | Local screening |
| Irrigation | FAO56 water balance with sensor correction | Constrained model predictive control; residual regression | Calibrated moisture/depth, ET inputs, rain, flow and soil parameters | Local controller/gateway |
| Sensor anomalies | Bounds, rate-of-change, flatline and disagreement rules | Isolation Forest/robust residual models | Device-calibrated time series and known faults | MCU/gateway |
| Local weather correction | Official/provider forecast baseline | Quantile regression/boosting; spatiotemporal models only with enough local history | Archived forecasts as issued and local observations | Server training; local inference possible |
| Price forecasting | Last value, seasonal naive, rolling seasonal median | SARIMAX/gradient boosting; TFT; Chronos as challenger | Clean mandi/crop/grade history and covariates available at issue time | Batch server job |
| Yield forecasting | Local agronomic estimate with ranges | Crop simulator; boosted regression; remote-sensing temporal model | Harvest weights/area/grade and management history | Later |
| Harvest readiness | Crop-specific maturity checklist | Vision stage/quality classifier | Maturity labels, moisture, weather, planting date | Local |
| Produce grading | Recorded manual/assay grade | Detection/segmentation with controlled imaging | Commodity-specific size/color/damage/grade labels | Local or packhouse |
| Speech | Existing Sarvam cloud path plus manual/recorded offline prompts | Benchmark deployable ASR/TTS on chosen phone | Actual dialect, noisy-field, unit and crop vocabulary evaluation | Hybrid |
| Farm explanation | One tool-using language agent | Provider-neutral adapter for Claude/OpenAI or local model | Curated evidence, structured state and permission-scoped tools | Cloud optional; local templates essential |

These are experiment candidates, not proof that every alternative fits the chosen hardware.

Qualcomm publishes MobileNetV3-Small (2.54M parameters) and EfficientNet-B0 (5.27M) deployment assets. These are general image backbones and require task adaptation. Its YOLOX card provides a useful supported detector comparison. The smaller parameter count motivates testing MobileNet first; it does not establish its agricultural accuracy. [Qualcomm MobileNetV3 card](https://huggingface.co/qualcomm/MobileNet-v3-Small), [EfficientNet-B0 card](https://aihub.qualcomm.com/mobile/models/efficientnet_b0), [YOLOX card](https://aihub.qualcomm.com/mobile/models/yolox)

YOLOX's author repository uses Apache-2.0. Ultralytics offers AGPL-3.0 and enterprise terms. Code, pretrained weights, training data and redistributed artifacts need separate license records; commercial use is not universally prohibited by open-source licensing. [YOLOX author repository](https://github.com/Megvii-BaseDetection/YOLOX), [Ultralytics terms](https://www.ultralytics.com/license)

### Available datasets and their actual limits

| Data | Available source | Suitable use | Material limitation |
|---|---|---|---|
| Controlled leaf disease | PlantVillage author dataset/paper | Pretraining and reproducible baseline | Clean backgrounds, selected crops; exact chosen release license must be established |
| More varied disease images | PlantDoc, 2,598 images, author repository CC BY 4.0 | Supplementary classification/detection experiments | Internet-derived, small; classification/detection labels differ by release |
| Pest classification/detection | IP102, >75,000 images, 102 categories, about 19,000 boxed images | Pest pretraining and taxonomy mapping | Academic-use permission; commercial permission requires contact; local species gaps |
| Coffee nutrient symptoms | CoLeaf, 1,006 images, CC BY 4.0 | Research on coffee symptom classification | Does not directly support wheat/rice/tomato; lab-confirmed concentration labels not established |
| Banana nutrient symptoms | Karnataka banana dataset, CC BY 4.0 | Crop-specific experiment | 7,000+ includes augmentations; background processing changes field appearance |
| Regional crop yield | Government DES area/production/yield query | Regional baseline and context | District-level statistics are not field-level counterfactual labels |
| Mandi prices | AGMARKNET through data.gov.in | Daily observed prices and future data collection | Missing dates/grades/markets, modal price not executable bid; archive coverage must be audited |
| Satellite | Copernicus Sentinel-2; Sentinel-1 as later radar option | Vegetation/anomaly history and mapping | Resolution, cloud/revisit, mixed pixels, no direct leaf diagnosis |
| Soil geography | SoilGrids prediction layers | Weak prior where no local measurement exists | Predictions with uncertainty; not a soil test for this farm |
| Sensor/action/yield pairs | Must collect locally | Irrigation calibration, diagnosis fusion and impact measurement | No universal public dataset captures your farm, sensor and decisions |
| Vendor availability and delivered rates | Supplier/FPO/CHC quotes | Procurement and logistics ranking | Usually fragmented; no verified universal live API found |

Dataset references: [PlantVillage paper](https://arxiv.org/abs/1604.03169), [PlantVillage author repository](https://github.com/spMohanty/PlantVillage-Dataset), [PlantDoc paper](https://arxiv.org/abs/1911.10317), [PlantDoc dataset](https://github.com/pratikkayal/PlantDoc-Dataset), [IP102](https://github.com/xpwu95/IP102), [CoLeaf](https://data.mendeley.com/datasets/brfgw46wzb/1), [banana nutrient dataset](https://data.mendeley.com/datasets/7vpdrbdkd4/1), [DES query](https://data.desagri.gov.in/website/apy-query-report-web), [SoilGrids uncertainty documentation](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html).

The original PlantVillage study reported 99.35% on a held-out controlled-image set but 31.4% on differently sourced online images. This is a historical illustration of domain shift, not a forecast of your eventual model's performance. [Mohanty et al., 2016](https://arxiv.org/abs/1604.03169)

A field study of offline PlantVillage Nuru in cassava reported better results when multiple leaves were assessed. That supports testing guided multi-view capture rather than assuming a single photograph is sufficient. It does not establish an identical protocol for other crops. [Mrisho et al., 2020 publication record](https://pure.psu.edu/en/publications/accuracy-of-a-smartphone-based-object-detection-model-plantvillag/)

### Training and evaluation recipe

Define a narrow crop and label contract first. Include healthy, supported disease/pest labels, poor capture, unsupported crop and unresolved/mixed symptoms. Use separate outputs for disease probability, observed severity and recommended action; they are different quantities.

Collect consented images with farm, plant/session, date, device, organ and stage metadata. Keep original images and labels; record expert disagreement. Collect healthy plants, look-alike stress, unknown diseases and difficult light/background conditions. Augment only training data. Group splits by farm and capture session; all versions of the same plant/image must stay in one partition. Reserve an untouched local-farm test set.

Train a transfer-learning baseline, then compare a second architecture using the same split. Tune thresholds and probability calibration on validation data. Evaluate per-class precision/recall, macro-F1, confusion matrix, calibration, unknown rejection, subgroup behavior and confidence intervals. Select according to the cost of a missed problem and a false intervention, not aggregate accuracy alone.

Export fixed-shape models, quantize with representative training/calibration inputs, compare with float results and record degradation. Benchmark camera-to-result latency, initialization, preprocessing, inference, postprocessing, memory, battery and heat on the actual device. A hosted model benchmark is not a product latency measurement.

Qualcomm AI Hub supports compile, profile and inference workflows. ONNX Runtime's documented QNN HTP path requires quantized models, fixed shapes and supported operators; CPU fallback can be disabled for placement verification. Other GPU/runtime paths differ. Freeze the device, OS, SDK and model export combination before claiming NPU acceleration. [Qualcomm development workflow](https://workbench.aihub.qualcomm.com/docs/hub/getting_started.html), [ONNX Runtime QNN](https://onnxruntime.ai/docs/execution-providers/QNN-ExecutionProvider.html)

Do not promise a dataset size that guarantees accuracy. As a collection budget, plan an initial few hundred independent local capture sessions and a class-specific expansion driven by errors. A rare class without sufficient independent examples remains outside the validated scope.

## Soil and nutrient intelligence

Separate rapidly sampled physical measurements from chemical fertility tests. Moisture, temperature and some EC measurements can support continuous monitoring when calibrated. Nutrient concentration/availability requires knowing the sensor method, extraction basis, soil moisture dependence, depth and reference laboratory method.

A 2025 CGIAR study of three low-cost NPK sensor models found poor precision and strong moisture dependence and did not recommend those tested devices for precision fertilization. This does not condemn every specialized sensor, but it invalidates assuming that a low-cost multi-parameter probe is a laboratory replacement. [Estrada et al., CGIAR, 2025](https://cgspace.cgiar.org/items/66e9e012-8409-46dc-918e-af0883333d74)

India's Soil Health Card framework covers N, P, K, S, micronutrients, pH, EC and organic carbon. Ingest a lab report with its date, sampling depth, method and units; preserve the report image for correction. [Official Soil Health Card testing FAQ](https://support.soilhealth.dac.gov.in/kb/faq.php?id=44)

“Crop requirement minus soil availability” is a useful explanation of a deficit, not a complete fertilizer prescription. A local soil-test crop-response method also needs target yield and nutrient contributions/recovery from fertilizer, manure and soil. Do not transfer a numerical prescription equation across unrelated crops or test methods. [Primary STCR study, 2024](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2024.1439523/full)

Proposed nutrient service: normalize units and elemental/oxide conventions; inventory prior additions; calculate a budget using a locally reviewed method; produce staged options; record what was actually applied. Missing critical inputs produce “test/review needed.” Atmospheric N2, nitrate, ammonium, total nitrogen and plant-available nitrogen must not be treated as interchangeable values. P versus P2O5 and K versus K2O must remain explicit.

Leaf yellowing can justify investigation, not an automatic fertilizer purchase. Use crop stage, distribution of symptoms, recent weather, root damage, water status and soil/tissue evidence to distinguish possible causes.

## Weather and forecast-aware irrigation

### Use the right forecast for the decision

| Horizon | Appropriate use | What to display |
|---|---|---|
| Minutes to hours | Local hazards and nowcasting where feeds exist | Issue/expiry time, affected geography and uncertainty |
| Next few days | Sowing work, spraying conditions, harvest planning and irrigation | Forecast amount/timing, ensembles when available, update time |
| Extended range | Workload and contingency preparation | Broad probabilities/anomalies, not precise field rain appointments |
| Next season | Crop/variety/water-risk scenarios | Climate normals and seasonal outlooks; scenario ranges |
| Several years | Rotation and investment resilience | Multiple plausible climate/economic trajectories |

IMD documents city seven-day and district five-day forecast products, observations, warnings and agromet services. Its API access page includes onboarding/whitelisting considerations. Record the exact product rather than assigning all IMD data a single resolution or horizon. [IMD API reference](https://api.imd.gov.in/public/api_reference.html), [API access guidance](https://mausam.imd.gov.in/responsive/apis.php), [extended-range products](https://mausam.imd.gov.in/imd_latest/contents/extendedrangeforecast.php)

BharatFS was announced at 6 km resolution in May 2025, replacing a 12 km model. That is still not individual-field forecast resolution; a coordinate-specific response can be interpolated from a shared grid. Local bias correction needs measured local observations and archived issued forecasts, with evaluation by lead time. [Ministry of Earth Sciences announcement](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2131392&lang=2&reg=48)

Do not start by training a weather foundation model or extrapolating a single satellite image to next season. Start with provider forecasts, characterize local errors, then test statistical corrections only where they outperform the uncorrected provider.

### The four-day rain assumption

It is correct to consider forecast rain. It is incorrect to always stop irrigation because rain may arrive in four days.

A transparent starting point is reference evapotranspiration and crop coefficients, plus a root-zone water balance. FAO56 defines available water using field capacity, wilting point and rooting depth, and a crop-dependent readily available fraction. Rain, irrigation, runoff, drainage and crop demand change depletion. [FAO56 reference ET](https://www.fao.org/4/X0490E/x0490e06.htm), [crop coefficients](https://www.fao.org/4/x0490E/x0490e0a.htm), [root-zone balance](https://www.fao.org/4/X0490E/x0490e0e.htm)

For illustration only: if 10 mm remains before the chosen stress threshold and estimated demand is 5 mm/day, stress may start in roughly two days under a simplified no-rain balance. A forecast of rain on day four does not remove that intervening risk. A bounded bridging irrigation followed by reassessment may be preferable. These numbers are invented to explain timing, not a recommendation for a crop.

Engineering decision procedure: validate sensors and water availability; project root-zone state across weather scenarios; prevent critical stress and waterlogging; choose a bounded irrigation quantity; re-evaluate when rain/flow/soil observations arrive. Rain probability alone is insufficient: expected amount, timing, infiltration and forecast uncertainty also matter.

Use measured flow to quantify applied water. A pump runtime multiplied by a nominal rate is an estimate because actual flow changes. Irrigation duration must have independent maximum-time/volume limits and feedback.

## Crop planning and farm economics

A classifier trained on soil/weather rows labeled “recommended crop” can reproduce that dataset's labels. It cannot establish the counterfactual question: what would this farmer have earned with each alternative crop under the same conditions?

Use two stages. First exclude infeasible candidates based on season, water, crop family/history, soil constraints, labor, budget, legal variety availability and buyer requirements. Then compare scenario distributions for yield, grade, input costs, water, sale price and payment timing. Let the farmer select priorities: downside protection, water use, cash needed, quality/export readiness or expected margin.

DSSAT requires weather, soil, cultivar, management and initial conditions and needs local evaluation. APSIM supports rotation scenarios, but its current General Use license has obligations/restrictions that require version-specific review. AquaCrop is useful for water–yield response with a simpler field representation; it is not a complete erosion or exact nutrient-prescription engine. [DSSAT ecosystem, 2025](https://dssat.net/wp-content/uploads/2025/04/The-DSSAT-Crop-Modeling-Ecosystem.pdf), [APSIM rotation tutorial](https://apsim-rotationtraining.readthedocs.io/en/latest/basic%20crop%20rotations.html), [APSIM license](https://github.com/APSIMInitiative/ApsimX/blob/master/LICENSE.md), [AquaCrop overview](https://www.fao.org/aquacrop/overview/en)

For an MVP, implement explicit constraints and low/base/high economic scenarios. Later, calibrate one crop simulator or a yield model; do not integrate all three simulators.

### Prices and market selection

AGMARKNET's public dataset describes daily wholesale minimum, maximum and modal prices. It is not an intraday exchange order book or a commitment to buy the farmer's produce. [Government dataset description](https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi)

Preserve crop, variety, grade, mandi, unit, observation date, retrieval time, source and revision identity. Missing data is not zero. Audit accessible historical coverage before committing to a seasonal model; begin collecting immutable daily snapshots now.

Backtest against last-observed and seasonal naive baselines with rolling forecast origins. Features can include lagged prices/arrivals, season, holidays, nearby markets and weather, but only if known at the forecast issue time. Separate observed history from forecast values. Evaluate MAE/MASE, quantile loss, interval coverage and simulated decision regret after costs. Long-horizon forecasts should widen uncertainty.

TFT is designed for multi-horizon forecasts with static, known-future and historical variables. Chronos offers pretrained forecasting models and a practical challenger. Neither source establishes superiority for this project's Indian mandi data. Test them after simple baselines and a data audit. [TFT original research](https://research.google/pubs/temporal-fusion-transformers-for-interpretable-multi-horizon-time-series-forecasting/), [Chronos author repository](https://github.com/amazon-science/chronos-forecasting)

Rank a sale option using comparable quality and quantity:

Net sale proceeds = accepted quantity × accepted price − transport − loading/unloading − commissions/fees − storage/packing − expected losses.

Season profit additionally subtracts production costs. Keep these two quantities separate. If rejected/spoiled quantity already reduces revenue, do not deduct the same loss a second time. Payment delay, rejection risk, available vehicles and road access can change the best choice.

Illustration only: 20 quintals at INR 2,000/q with INR 3,000 selling costs yields INR 37,000 proceeds. A farther market at INR 2,200/q with INR 6,000 costs yields INR 38,000. Its apparent advantage is only INR 1,000; a 3% reduction of the farther market's INR 44,000 gross revenue would erase that advantage if all other assumptions stayed fixed. Display that sensitivity instead of declaring “farther is best.”

Storage decisions compare discounted expected future proceeds after storage, financing, quality loss and logistics with available proceeds today. Include liquidity needs and storage capacity. Never assume rising historical prices imply that storing will pay.

e-NAM describes commodity-specific assaying, including physical and sometimes chemical tests. A camera-estimated grade should not be represented as an official assay certificate. [e-NAM assaying](https://enam.gov.in/web/commodity/assaying)

## APIs and provider aggregation

An API key authorizes access; it does not import a scientifically validated agricultural model. Open model weights and cloud APIs are different integration options.

| Need | Candidate and access | Cost/access implication | Boundary and next step |
|---|---|---|---|
| Coordinates | Phone GPS and farmer-drawn polygon | No external location API required for GPS itself | Store accuracy, permission and verified boundary |
| Maps/routes/places | Google Maps Platform Places and Routes | Billing-enabled restricted key; per-SKU pricing/India eligibility | Discover businesses and travel estimates, not inventory or freight quotes |
| Offline map | Licensed downloadable tiles/vector data or own OSM-derived service | Hosting/provider terms | Standard public OSM tiles prohibit bulk download/offline prefetch |
| Satellite | Copernicus Data Space Sentinel Hub/STAC | Account/OAuth for relevant APIs; quotas depend on service | Cache derived field statistics with attribution/access rules |
| Soil prior | SoilGrids | Public prediction products; service limits | Use uncertainty and provenance, not field-test claims |
| Weather prototype | Existing Open-Meteo adapter | Free tier for noncommercial prototype within limits; commercial service uses paid access | Verify licensing for later business deployment |
| Official weather | IMD | Documented endpoints; onboarding/whitelisting may apply | Validate access and schema; preserve product identity |
| Disaster alerts | SACHET CAP/RSS | Public documented dissemination feed | Respect update/cancellation and expiry |
| Daily mandi prices | data.gov.in / AGMARKNET | Issued project API credential for authenticated API access | Already scaffolded; validate pagination/history/units |
| MSP/procurement | Official government notifications and designated agency portals | Public documents; no universal procurement API verified | Maintain crop/state/season-specific eligibility records |
| Machinery | FARMS app/CHCs plus onboarded local vendors | No public reusable live rental-quote API verified | Directory/deep-link/partnership, then supplier-entered quotes |
| Disease breadth | Plantix API Toolkit | Provider onboarding/quote; no price or account access tested | Optional online comparison/escalation; core stays local |
| Speech | Existing Sarvam API | Account key and metered provider service | Test actual dialect/latency; manual and offline templates remain |
| Edge compilation | Qualcomm AI Hub | Qualcomm account/API token for development jobs | Export models/runtime; deployed inference must work without token/network |
| Agent | Existing Codex app-server; optional Claude/provider adapter | Account/runtime-specific authorization and costs | Cloud agent optional; no model credentials on sensor nodes |
| Buyers/transport/input stock | Supplier/FPO/logistics partnerships, quote forms | Commercial agreements/operational effort | No universal complete feed found; record coverage and freshness |

Provider references: [Google Places policy](https://developers.google.com/maps/documentation/places/web-service/policies), [Google India pricing](https://developers.google.com/maps/billing-and-pricing/pricing-india), [OSM tile policy](https://operations.osmfoundation.org/policies/tiles/), [Copernicus OAuth](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html), [Open-Meteo pricing](https://open-meteo.com/en/pricing), [FARMS official service](https://agrimachinery.nic.in/Index/farmsapp), [Sarvam API documentation](https://docs.sarvam.ai/api-reference/introduction), [Plantix API](https://www.plantix.net/en/plantix-intelligence/api-toolkit/).

Existing configuration names include SARVAM_API_KEY and DATA_GOV_IN_API_KEY. Proposed providers need project-owned credentials such as a restricted maps key and Copernicus OAuth client. This audit inspected configuration names/defaults and examples, not secret values, paid entitlements or live account balances. It does not assert which keys you personally possess.

### How to build the vendor search service

Start with one pilot radius, product taxonomy and a consented supplier directory. Combine partner feeds, supplier-entered listings, public directories with permitted reuse, and approved search APIs. Scrape only sources whose access and reuse terms support the use; do not bypass logins, CAPTCHAs or technical restrictions. A search result is a discovery record, not a verified offer.

Normalize vendor identity, contact consent, location/service radius, equipment specification, rental unit, operator/fuel inclusion, minimum hours/area, availability, taxes, deposit, cancellation and quote expiry. Seed offers require crop/variety/lot/pack size; fertilizers require formulation and nutrient analysis. Store source URLs and last verification.

Request a dated total quote for the farmer's exact quantity/date/location. Calculate acquisition cost plus delivery, loading, operator/fuel, deposits or financing where applicable. Show the cheapest comparable verified offer, coverage limits and missing charges. Treat refundable deposits as cash required, not automatically as final expense.

Google Places restricts storage/caching of returned content, with exceptions such as place IDs; map display and attribution conditions also apply. Do not build an unrestricted permanent scraped business database from Google responses. Separate supplier-owned records from licensed discovery content. [Current Places policy](https://developers.google.com/maps/documentation/places/web-service/policies)

Keep discovery/ranking in a backend domain service. The web page and agent call that same service. Purchases, bookings or outreach require the farmer's explicit chosen offer and an action record. The initial product can provide contact/deep-link and quote comparison without claiming booking fulfillment.

## Seeds organic farming exports and disaster recovery

Seed selection must compare locally appropriate varieties, maturity, stress resistance, quality traits, input demand, availability and verified trial evidence. Hybrids, conventional varieties, transgenic GM and genome-edited varieties are distinct categories. Government announced genome-edited rice varieties in May 2025; an old “only Bt cotton” statement cannot by itself settle the complete September 2026 landscape. Check the exact variety's current status and availability. [Government rice announcement](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2126802&lang=2&reg=3), [GEAC information](https://geacindia.gov.in/biosafety-data.aspx)

Seed certification/labeling addresses identity, purity and germination; it does not establish a guarantee of realized field yield. No universal company yield guarantee was verified. Store the actual seed lot label, invoice and any written warranty, including conditions and claims process. [Seeds Act, sections 6–9](https://www.indiacode.nic.in/bitstream/123456789/13686/1/the_seeds_act%2C_1966.pdf)

Organic production requires applicable certification, input history and traceability; farmer preference alone does not create certified organic produce. Export readiness should begin before sowing because residues, field registration, testing, packhouse and buyer/destination specifications affect management. The agent can explain and organize evidence; it cannot issue certification. [APEDA NPOP](https://npop.apeda.gov.in/), [APEDA HortiNet protocols](https://apeda.gov.in/hortinet-static)

MSP support must check the relevant crop, season, state, procurement mechanism, registration, quality and center. Do not implement an unconditional “sell to government at MSP” option. [PIB procurement explanation](https://www.pib.gov.in/PressNoteDetails.aspx?ModuleId=3&NoteId=155448&lang=2&reg=48)

Disaster management needs three workflows: prepare from risk/official warnings; respond with local observations and practical instructions; recover through evidence, inspection, appropriate testing, finance and reseeding decisions. Soil probes cannot establish the extent of landslide damage or contamination of an entire flooded field.

SACHET disseminates authoritative CAP alerts and provides RSS. Preserve source authority, location, severity, issue/expiry times and update/cancellation identifiers. Loss of internet means new remote warnings may not arrive; local threshold detection can continue but must not be presented as full official warning coverage. [SACHET](https://sachet.ndma.gov.in/), [WMO registered feed](https://alertingauthority.wmo.int/authorities.php?recId=331)

Insurance assistance should preserve enrollment, insured crop/area, event date, photos and applicable notification deadlines. Coverage and claim rules depend on policy and current notification; the app can assemble evidence, not promise compensation. [PMFBY official FAQ](https://www.pmfby.gov.in/faq)

## Recommended architecture and agent harness

Use three cooperating execution layers:

1. Sensor/controller node: measurement, calibration metadata, bounded local water-control policy, physical feedback, manual override and fault handling.
2. Farmer device: camera inference, cached crop guidance, field state, task/ledger capture and local-language interaction that remains useful offline.
3. Optional connected services: reference data, weather/market ingestion, model/content distribution, synchronization and richer language-agent explanations.

Use the existing React/FastAPI/MCP architecture for domain workflows. Add Android local inference through a native bridge and explicit offline storage; Electron is useful for development/admin, but is not an Android runtime. Preserve the Codex integration behind an adapter. Do not require every farmer to use a desktop CLI, developer account or cloud model to receive core advice.

The official Codex app-server exposes a programmatic integration surface. Its presence is a reasonable reuse point, but it does not supply the local agronomic models or deterministic equipment controller. [OpenAI app-server documentation](https://learn.chatgpt.com/docs/app-server)

The agent should fetch bounded field context, call specialist services, explain assumptions and present an action. Domain services own calculations and records. The controller owns actuation. A broad coding-agent shell/tool inventory is unnecessary in the farmer interface; expose only registered farming capabilities.

Store language-independent IDs and numerical quantities. Keep original speech/text alongside transcription, translation and extracted slots. For an irrigation or purchase instruction, read back field, amount/unit and selected action in the farmer's language. Translation into English can be reused initially, but the extra layer must be tested for number, negation, crop and unit errors. Offline buttons, templates and locally available audio remain usable when speech APIs fail.

Detailed state contracts, synchronization, proposed tools and control states are in the implementation plan. MQTT QoS is a transport delivery property, not an application guarantee that a pump action occurs exactly once; commands still need durable IDs and acknowledgement/reconciliation. [OASIS MQTT 5.0 standard](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html)

### What the digital twin should mean

Start with a confirmed boundary plus dated crop, sensor, task, health, weather and financial events. Add management zones, uncertainty and map-linked reports. A simulation-ready twin additionally requires calibrated crop/soil state and parameterized processes. A satellite basemap alone is a map, not a validated simulator.

Sentinel-2 supplies multispectral observations with bands at different spatial resolutions, including 10 m bands. Cloud, observation timing, mixed boundary pixels and small fields limit usable information. NDVI or related vegetation anomalies indicate change, not a specific disease or exact nutrient deficit. Pair satellite anomalies with ground observations. [Copernicus Sentinel-2 documentation](https://documentation.dataspace.copernicus.eu/Data/SentinelMissions/Sentinel2.html)

## Innovation and SIH competitiveness

The problem is valuable, but the feature list is not unique. Plantix offers image diagnosis APIs; Fasal advertises sensor and irrigation/crop guidance; Cropin offers conversational interaction over mapped farms. These are examples of overlap, not independent evidence of their accuracy or business outcomes. [Plantix](https://www.plantix.net/en/plantix-intelligence/api-toolkit/), [Fasal soil unit](https://www.fasal.co/soil-moisture-unit), [Fasal platform](https://i.fasal.co/), [Cropin OrbitAI](https://ai.cropin.com/)

My subjective assessment, not an official SIH score:

| Dimension | Rating | Reason |
|---|---:|---|
| Social relevance | 9/10 | Directly addresses water, inputs, crop risk and farmer access |
| Full lifecycle product potential | 8/10 | Coherent long-term value if decisions and transactions are dependable |
| Novelty of feature list alone | 5/10 | Many individual features and combinations already exist |
| Current readiness for supplied edge/hardware brief | 4/10 | Useful software foundation; no validated local vision or physical loop |
| Potential of a focused, measured demonstrator | 8/10 | Strong if offline behavior, field accuracy and water accounting are shown |

A credible SIH case is: “For a declared crop and region, the system detects supported visible problems, incorporates soil/crop state, recommends and verifies bounded irrigation, and remains useful without WAN connectivity.” Support it with independent field images, target-device traces, flow measurements, fault tests, farmer usability results and a realistic cost/maintenance plan.

Do not claim “first,” 99% field accuracy, guaranteed yield uplift, exact hyperlocal forecasts or a probability of winning. No evidence here can establish winning odds, current competitor quality or the organizer's scoring weights. The scope becomes less competitive if marketplace breadth consumes the time needed for field validation.

## Unresolved evidence and next decisions

The official SIH source, chosen Qualcomm hardware, pilot crop/district, farm/expert partner and budget remain open. Provider credentials, commercial quotes, current supplier availability, crop-specific prescription tables, model licenses for the exact selected release, local field data and seasonal impact are not verified.

Research stopped after primary evidence covered each consequential technical choice or bounded its limitation. Further broad model lists would not change the recommended first architecture. The next useful work is targeted: obtain the official brief, secure local labels and a test plot, compile the candidate model on the exact device, calibrate sensors, and measure a complete offline decision-to-action sequence.
