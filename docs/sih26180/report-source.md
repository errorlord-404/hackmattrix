# KisanSathi Smart Farming Assistant research source record

Date: 6 September 2026
Audience: KisanSathi engineering team, SIH proposal authors and a future AI session
Scope: India-focused field-deployable farming assistant; repository at `C:\Users\prana\Desktop\sih mvp`; supplied SIH26180 brief
Canonical role: This is the internal Deep Research source record. The expanded evidence report is [RESEARCH.md](RESEARCH.md); claim-to-source provenance is [SOURCE_LEDGER.md](SOURCE_LEDGER.md).

## Direct answer

KisanSathi is technically feasible and potentially competitive as a focused field-deployable demonstrator. It should begin as a bounded crop-health and irrigation system for one crop, one pilot region and one verified device configuration. The current codebase is a credible web/desktop/agent foundation, but it does not yet contain the local ML artifact, calibrated sensing, controller firmware, Android offline runtime, safe actuation loop or field validation demanded by the supplied brief.

The correct architecture is:

1. An independent local sensing/controller loop for measurement, safety limits, manual override and feedback.
2. A farmer device for camera inference, local state, local-language workflow and deferred synchronization.
3. Connected services for fresh forecasts, official alerts, markets, reference content, model distribution and richer agent explanations.

This preserves core use when connectivity or the language model fails. The language agent explains decisions and performs constrained software workflows; it does not own irrigation actuation or raw sensor interpretation.

## Scope assumptions

- India is the intended operating jurisdiction.
- Hindi, Marathi and English are the initial language assumption.
- The team has not yet chosen the pilot crop, district, farm partner or Qualcomm target hardware.
- The user supplied the wording attributed to SIH26180 and Qualcomm. On 6 September 2026, searches limited to `sih.gov.in`, `smartindia.gov.in` and `mic.gov.in` did not surface an official SIH26180 page. Community reproductions are supporting discovery sources only. Verify the official brief before competition-specific claims.
- No secrets, provider entitlements or paid API accounts were inspected or used.
- No field trial, device benchmark or electrical installation was performed.

## Evidence-backed conclusions

### Crop health and ML

A compact local image model is practical, but generic benchmark accuracy is insufficient evidence of field performance. The PlantVillage study reports 99.35% accuracy in its controlled test and 31.4% on differently sourced online images, illustrating strong domain shift. [Mohanty, Hughes and Salathe](https://arxiv.org/abs/1604.03169)

Start with a fine-tuned MobileNetV3-Small classifier for supported leaf-health classes and a small detector for visible pests. Compare against a higher-capacity baseline using the same local grouped test split. Qualcomm publishes deployable image backbone/model assets, but their generic benchmark metadata does not establish agricultural accuracy. [Qualcomm MobileNetV3-Small](https://huggingface.co/qualcomm/MobileNet-v3-Small), [Qualcomm YOLOX](https://aihub.qualcomm.com/mobile/models/yolox)

The model must return poor-capture, unsupported-crop and unresolved/mixed outcomes. Gather expert-labeled local field photos, preserve farm/session grouping, include look-alikes and evaluate macro-F1, per-class recall, calibration and rejection quality. Nuru field evidence supports guided multi-leaf capture rather than single-image certainty. [Mrisho et al.](https://pure.psu.edu/en/publications/accuracy-of-a-smartphone-based-object-detection-model-plantvillag/)

Nutrient deficiency from a photo is a possible-cause screening signal, not a fertilizer prescription. Symptoms overlap with disease, water stress, leaf age and root problems. Pair image observations with crop stage, irrigation history and appropriate soil/tissue evidence before producing any dosing guidance.

### Soil and irrigation

The four-day rain assumption needs a correction. Forecast rain is relevant, but irrigation should not always be deferred because rain may occur in four days. FAO56 root-zone water balance incorporates crop demand, soil water capacity, root depth, irrigation, rain and drainage. A crop can enter water stress before forecast rain arrives. [FAO56 Chapter 8](https://www.fao.org/4/X0490E/x0490e0e.htm)

Use FAO Penman-Monteith reference ET and crop/stage coefficients as the transparent first implementation. Sensor observations correct the estimated root-zone state. Machine learning may later provide a validated residual correction; it is not the baseline decision engine. [FAO56 Chapter 2](https://www.fao.org/4/X0490E/x0490e06.htm)

Do not treat low-cost NPK probes as substitutes for laboratory soil testing. A 2025 CGIAR evaluation of three portable devices found limited precision and strong moisture dependence. Structured laboratory/Soil Health Card results should anchor nutrient recommendations; live probes should carry method, depth, unit, calibration and quality metadata. [CGIAR sensor evaluation](https://cgspace.cgiar.org/items/66e9e012-8409-46dc-918e-af0883333d74), [Soil Health Card FAQ](https://support.soilhealth.dac.gov.in/kb/faq.php?id=44)

A physical irrigation system requires local hard limits, flow or volume feedback, maximum duration/volume, stale-sensor behavior, manual stop, replay protection and fault handling. A consumer smart plug is not a universal agricultural pump controller. Begin with a low-voltage bench demonstrator; obtain competent electrical design/review for a real pump interface.

### Weather, disasters and satellite

GPS coordinates identify the request location; they do not create individual-field forecast skill. IMD documents seven-day city and five-day district forecast services plus observations, warnings and agromet advisory. Use a source adapter that records issued time, valid period, product, grid/station identity and freshness. [IMD API reference](https://api.imd.gov.in/public/api_reference.html)

Use short-range forecasts for operational decisions, broader outlooks for scenarios and archived forecast-versus-observation data before trying local bias correction. Satellite imagery supports dated vegetation/anomaly trends and mapping, not direct leaf diagnosis or exact nutrient concentration. Sentinel-2 has 10 m bands, cloud/revisit limits and mixed pixels. [Copernicus Sentinel-2](https://documentation.dataspace.copernicus.eu/Data/SentinelMissions/Sentinel2.html)

For disaster resilience, consume official CAP/RSS alerts when connected and preserve alert source, area, severity, issue/expiry and update/cancellation identity. SACHET provides an India CAP RSS feed. Local sensors provide supplementary conditions, not complete disaster coverage. [SACHET](https://sachet.ndma.gov.in/)

### Crop choice, markets and lifecycle

Do not train a simple “best next crop” classifier from historical recommendations. Crop selection is a constrained, counterfactual choice. Filter infeasible options using season, soil, water, crop history, labor, cash and buyer constraints; then compare low/base/high scenarios for yield, costs, water, quality and price. Crop simulators such as DSSAT/AquaCrop/APSIM become useful only after crop/site inputs and licensing/calibration are addressed. [DSSAT ecosystem](https://dssat.net/wp-content/uploads/2025/04/The-DSSAT-Crop-Modeling-Ecosystem.pdf), [AquaCrop](https://www.fao.org/aquacrop/overview/en), [APSIM licence](https://github.com/APSIMInitiative/ApsimX/blob/master/LICENSE.md)

AGMARKNET/data.gov.in provides observed daily wholesale price indicators. They are not buyer commitments. Compare sale options with comparable lot quality, accepted quantity, dated transport/handling/fee/storage/spoilage assumptions and forecast uncertainty. Backtest any price model against seasonal-naive and last-value baselines before release. [Government market dataset](https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi)

Organic/export support must begin before sowing: certification/input history, traceability, residues, testing, packhouse and buyer/destination conditions affect the entire cycle. Seed certification deals with identity, purity and germination, not a universal realized-yield guarantee. MSP navigation requires season/state/crop/registration/quality validation. [APEDA NPOP](https://npop.apeda.gov.in/), [Seeds Act](https://www.indiacode.nic.in/bitstream/123456789/13686/1/the_seeds_act%2C_1966.pdf), [PIB procurement explainer](https://www.pib.gov.in/PressNoteDetails.aspx?ModuleId=3&NoteId=155448&lang=2&reg=48)

### Current software position

Verified current foundation:
- React/Vite manual interface with 17 routes.
- Electron desktop harness, FastAPI backend and Python MCP service.
- 47 registered MCP tools and 61 generated OpenAPI paths.
- Fields, crop stages, soil/sensor record structures, weather, market ingestion scaffolding, catalogs, voice configuration and reports.

Verified gaps:
- Diagnosis persists image metadata but returns provider-unavailable/inconclusive.
- No app-owned ONNX/TFLite/PyTorch model, model registry, firmware, device protocol, flow feedback or physical actuation.
- Irrigation is a fixed threshold rule and wrongly allows unscoped latest weather to influence a field.
- Soil screening can represent absent measurement as within range.
- Market comparison is not latest comparable lot selection and uses non-route default costs.
- Identity, CORS, authorization, atomic idempotency/outbox and device-local offline state need design before network/physical deployment.

The complete component audit and file references are in [RESEARCH.md](RESEARCH.md) and [SESSION_CHECKPOINT_2026_09_05.md](SESSION_CHECKPOINT_2026_09_05.md).

## Recommended delivery sequence

D0: verify official brief, select crop/site/hardware/expert, freeze units/IDs/action contracts and field protocol.

D1: correct current field/data correctness issues; create local health baseline, bench controller, offline Android path and a single end-to-end demonstrator.

D2: supervised farm deployment, calibration, expert review, local field test set, farmer usability evidence, flow measurement, inventory/ledger and dated quote/market comparisons.

D3: multi-season crop economics, validated forecasts, storage, organic/export and broader marketplace integration.

## Material uncertainty and stopping decision

The current evidence supports the scoped architecture and explicitly bounds its main risks. The unresolved evidence is not another generic model list: it is the official SIH brief, target device behavior, selected sensor calibration, local crop labels, expert-reviewed guidance and field outcomes. Further broad web research is unlikely to change the immediate engineering recommendation. Research stops here; the next useful work is Phase 0 selection and measured implementation.

## Source and search record

Primary and first-party sources were used where available: FAO, IMD, NDMA, CGIAR, APEDA, India Code, data.gov.in, Copernicus, Qualcomm and ONNX Runtime. Research papers and author repositories establish data/model limitations. Vendor pages establish advertised feature overlap only, not independent outcome claims.

Final official-source search on 6 September 2026:
- `site:sih.gov.in "SIH26180"`
- `site:smartindia.gov.in "SIH26180"`
- `site:mic.gov.in "SIH26180"`

No official result was returned. The documented SIH brief remains provisional until the organizer page or direct official document is supplied.
