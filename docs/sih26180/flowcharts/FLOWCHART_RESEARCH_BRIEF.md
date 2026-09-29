# KisanSathi SIH26180 Flowchart Research Brief

## Executive conclusion

KisanSathi should be presented as a field decision system that maintains one longitudinal farm record and connects sensing, crop-stage logic, market evidence and human-confirmed action. The strongest claim supported by the repository is an integrated software prototype: a React farmer application, a FastAPI domain layer, per-farmer SQLite state, MongoDB reference data, source-attributed public-data ingestion and a Python MCP tool layer for Codex. The hardware, crop-health model and pump controller require different levels of validation and should not be presented as equally mature.

The architecture is credible for an SIH prototype because its components already share stable API contracts. Its main innovation is orchestration across the complete crop cycle rather than a new individual model. The farmer may navigate the app directly or speak in a local language; the agent resolves the request, fetches persistent field context, calls a typed service and explains the evidence. Consequential writes require confirmation, while physical actuation remains outside the present agent authority.

The flowcharts use three visual states:

- Green: implemented software prototype.
- Amber: implemented scaffold or demo that needs field evidence.
- Brown: physical or agronomic action that remains safety gated.

## 1. Problem and solution lifecycle

The crop cycle should be shown as a loop because the end of one season becomes the evidence for the next. A linear “diagnose and recommend” story understates the product and loses the farm-memory advantage. The eight lifecycle groups in the circular diagram are:

1. Field reset: residue, crop rotation and soil history.
2. Crop choice: soil, season, forecast, seed and market trade-offs.
3. Inputs and preparation: seeds, fertilizer, machinery, labour and landed cost.
4. Crop growth: stage-specific irrigation, nutrition, pests and disease.
5. Climate shock: warnings, preparation, evidence and recovery.
6. Harvest: readiness, machinery, labour and weather timing.
7. Sell or store: quality, mandi prices, MSP context, freight, storage and spoilage.
8. Finance and recovery: ledger, schemes, insurance and the next crop baseline.

The repository already represents most of this lifecycle through fields, crop cycles, stage events, tasks, soil tests, observations, irrigation plans, ledger entries, alerts, reports, market prices, MSP, government schemes and marketplace listings. Harvest readiness, grading, storage optimisation and automatic pump control remain product extensions rather than complete implementations.

The weather-aware irrigation assumption is directionally correct, but a moisture threshold alone is insufficient. FAO crop-water guidance estimates crop evapotranspiration from reference evapotranspiration and a crop coefficient, with crop stage affecting water demand.^1 A safe recommendation should combine fresh root-zone evidence, crop stage, recent irrigation, forecast rainfall amount and timing, and a confidence/freshness gate. Rain forecast can justify delaying irrigation only when expected effective rainfall and available soil water cover the crop need. A future controller also needs flow feedback, a time limit and manual override.

## 2. Distinctive product claims

### One agent across one domain API

The web application and the agent do not implement separate agronomic logic. Both call the same FastAPI routes. The MCP server exposes typed tools for field history, soil state, weather, irrigation advice, crop options, crop-stage tasks, ledger, market prices, MSP, schemes, marketplace discovery, quote comparison, diagnosis, translation and speech. This makes the language model replaceable while the authoritative calculations and stored evidence remain in services.

### Local-language voice interaction

The repository includes provider adapters for speech-to-text, translation and speech synthesis. The intended flow matches India’s public multilingual architecture pattern: speech becomes text, the system translates or reasons in a canonical language, and the response returns in the preferred language.^2 The slide should claim native-language voice orchestration, not universal offline speech. The current Sarvam path still depends on provider configuration and connectivity.

### Field memory and offline continuity

The backend deliberately separates shared reference data from farmer-specific state. MongoDB contains crop, disease, seed, fertilizer, mandi, MSP, scheme and directory records. A separate SQLite database per farmer contains profile, fields, GPS boundaries, crop stages, observations, device telemetry, tasks, ledger, diagnoses and reports. This separation supports offline history, privacy boundaries and later synchronization. Public reference data can refresh when connectivity returns without blocking access to the farm record.

### On-device crop health with abstention

The ML work selects lightweight transfer-learning candidates rather than training a large CNN from scratch. TensorFlow Hub backbones and TFLite export are implemented, and Qualcomm AI Hub can compile, profile and validate custom models on hosted Qualcomm devices for LiteRT, ONNX Runtime or Qualcomm AI Runtime targets.^3 The current controlled-image artifacts are demo-only. They failed the repository’s field-release gates, so the correct prototype claim is “versioned on-device candidate with unknown and expert-review paths.”

PlantVillage remains useful for pretraining because it includes more than 54,000 labelled leaf images across 14 crops, but controlled backgrounds do not represent farmer-phone conditions.^4 Recent cross-domain work reports large drops when PlantVillage-trained classifiers meet field images and attributes the gap to clutter, lighting, occlusion and symptom overlap.^5 KisanSathi therefore needs field/date-disjoint local evaluation, unknown examples, calibration and per-class recall before any treatment claim.

### Sensor-to-action with a safety boundary

The proposed field node uses an ESP32-S3 and RS485/Modbus probes. DFRobot documents SEN0604 readings for moisture, temperature, EC and pH and a 5–30 V sensor supply range.^6 The SEN0605 protocol exposes NPK reference values over Modbus RTU.^7 These measurements should support trends and screening. They do not replace laboratory soil testing, and NPK values should not directly produce a fertilizer dose.

The first deployable loop should stop at an advisory task. Automatic pump control belongs to a later controller with electrical isolation, manual override, maximum runtime, flow confirmation and local fail-safe logic. The agent may explain or request a task, but it should never directly energize the pump.

## 3. Technical architecture represented in the diagram

### Farmer channels

- React 19 and Vite provide the web interface.
- Tailwind supplies styling, Leaflet provides farm mapping, Recharts provides history views, and i18next supplies interface localisation.
- Electron hosts the Codex desktop experience.
- Voice uses configured speech, translation and TTS services.

### Orchestration

- Codex app-server hosts the conversation and tool loop.
- The KisanSathi MCP plugin runs in Python through FastMCP.
- Typed tools call backend routes through HTTP and return bounded, provenance-aware results.
- Human confirmation protects writes and high-impact actions.

### Domain API

- FastAPI and Pydantic expose routes and schemas.
- Farm state covers profile, GPS fields, crop cycles, observations, tasks, alerts, ledger and reports.
- Soil and irrigation services combine field readings, freshness and weather.
- Crop health persists provider, model and limitation metadata.
- Market services cover AGMARKNET prices, trends, mandi comparison and MSP context.
- Marketplace services cover discovery and explicit quote arithmetic, not booking.

### Data

- Per-farmer SQLite preserves operational history and idempotency.
- MongoDB and Beanie hold common reference records.
- Device packets retain device identity, boot ID, sequence, observation time and quality metadata.

### Edge and external evidence

- ESP32-S3 polls RS485 probes and queues signed telemetry.
- TFLite is the current edge-model target; Qualcomm AI Hub profiling is a planned validation step.
- Open-Meteo supplies forecast context.
- India’s Open Government Data portal exposes an API-backed AGMARKNET dataset with minimum, maximum and modal wholesale prices.^8
- PIB/MSP, APEDA and explicitly approved public directories provide source-attributed records.

## 4. Feasibility assessment

### Technical feasibility: strong for an advice-first pilot

The software path is already broad enough for a complete demonstration. The highest-value next work is not another screen. It is proof of the narrow vertical slice:

`sensor or photo input -> validated API record -> recommendation -> farmer confirmation -> task or ledger entry -> visible history`

The hardware feasibility depends on verifying the exact transceiver module and power domain. The supplied circuit labels a MAX3485 while appearing to power it from 5 V. A genuine MAX3485 is a 3.3 V transceiver, so the team must confirm the module before power-up. Wokwi can validate firmware state and message flow, but it cannot establish outdoor surge protection, water ingress resistance, cable behaviour, calibration or RF reliability.

### Operational viability: strongest through institutions

A six-person student team can pilot one crop in one district with a local agronomy reviewer. A direct-to-every-farmer launch would create an unsustainable support burden because onboarding, probe placement, calibration, crop label review and language support all require field operations. FPOs, cooperatives, Krishi Vigyan Kendras or extension partners can consolidate onboarding and provide trusted escalation.

The farmer value should be measured through task completion and decision quality rather than model accuracy alone. Suggested pilot measures include irrigation events avoided or delayed safely, hours saved searching for inputs, difference between quoted and selected landed cost, diagnosis abstention rate, expert-review turnaround, gross-margin record completeness and farmer comprehension in the preferred language.

### Financial viability: requires full-cost measurement

The farmer-facing price cannot be inferred before the pilot establishes the cost of the sensor kit, enclosure, installation, calibration, replacement, connectivity, provider usage, agronomy review and field support. A viable route may combine an institution-paid deployment with a small service subscription. Referral or marketplace revenue should be secondary and transparent because it could bias recommendations.

The financial decision engine must compare net outcomes. A mandi with a higher headline price may lose after transport, loading, unloading, commission, spoilage and quality deductions. The current repository safely totals explicit quote components and does not invent missing costs. The same conservative rule should govern storage and export decisions.

## 5. Risk register and controls

| Risk | Consequence | Required control | Slide status |
|---|---|---|---|
| Sensor drift, placement error or stale data | False confidence in soil and irrigation state | Calibration record, freshness display, raw provenance, unknown state | Amber |
| Controlled-image ML domain shift | False disease or nutrient claim | Field-held-out data, unknown set, confidence calibration, expert review | Amber |
| Symptom overlap | Disease, pest, nutrient and water stress look similar | Fuse crop stage, weather, soil and symptom history; avoid photo-only treatment | Amber |
| API or connectivity loss | Missing weather, speech or market context | SQLite continuity, queued telemetry, provider-unavailable state | Green/amber |
| Unsafe irrigation automation | Crop or equipment damage | Advice first; later flow feedback, time limit, manual override and physical isolation | Brown |
| Marketplace freshness | Outdated availability or price | Source URL, retrieval time, direct contact and explicit quote confirmation | Green |
| Scheme or insurance policy change | Incorrect eligibility guidance | Use official sources, preserve effective date, treat results as pre-screening | Amber |
| Privacy and image sharing | Farmer data exposure | Consent, data minimisation, local inference preference and retention controls | Amber |
| Agent hallucination | Unsupported action | Typed tools, provenance, bounded outputs, human confirmation and authority separation | Green |

Government recovery support belongs in the lifecycle, but the application should direct farmers to official workflows rather than imply automatic eligibility. PMFBY’s official portal currently supports farmer enrolment, premium calculation, policy status and loss-reporting support.^9 The official scheme describes coverage from pre-sowing through specified post-harvest risks, which supports keeping disaster preparation, evidence capture and recovery in the same farm record.^10

## 6. Recommended SIH slide placement

The supplied SIH template uses a 16:9 layout at 12192000 by 6858000 EMU. Its working slides use a white canvas, a blue footer and large Times New Roman titles. The diagrams are authored at 1920 by 1080 with a white/neutral ground and blue-green accents so they can be inserted without cropping.

- Proposed approach slide: `01_problem_solution_lifecycle.svg` or its PNG. It combines the problem/solution circle and the uniqueness arrows.
- Technical approach slide: `02_technical_architecture.svg` or its PNG.
- Working and usage slide: `03_farmer_usage_journey.svg` or its PNG.
- Feasibility and viability slide: `04_feasibility_viability_risk.svg` or its PNG.

SVG should be preferred while authoring because it scales without loss and PowerPoint can convert SVG graphics to shapes when editing is needed. The 4K PNG files are suitable when preserving exact layout matters more than editability.

## 7. Claims suitable for judges

### Supported now

- One farm record across GPS fields, crop stages, soil, tasks, finance, market and reports.
- React app and Codex/MCP agent use the same FastAPI services.
- Local-language voice adapter exists and can be configured.
- Public mandi data, weather, MSP context and approved directory records retain provenance.
- Per-farmer SQLite plus shared MongoDB architecture is implemented.
- Crop-health orchestration preserves model metadata, unsupported and expert-review states.
- Device ingestion schema stores raw evidence, ordering and freshness metadata.

### Demonstration or validation claim only

- Controlled-image crop router and specialist models.
- TensorFlow Hub fine-tuning and TFLite export pipeline.
- ESP32-S3/Modbus field node until firmware and bench evidence enter source control.
- Hyperlocal weather beyond the resolution and limits of the selected provider.
- Predictive irrigation until agronomic thresholds and field outcomes are validated.

### Do not claim yet

- Fully autonomous irrigation.
- Laboratory-grade NPK measurement.
- Accurate diagnosis across all crops and diseases.
- Guaranteed yield or profit.
- Real-time booking, stock or verified vendor availability.
- Automatic scheme approval, insurance claim settlement or export compliance.

## Sources

1. FAO. [Crop evapotranspiration: Guidelines for computing crop water requirements, Irrigation and Drainage Paper 56](https://www.fao.org/4/X0490E/X0490E00.htm). 1998.
2. Digital India BHASHINI. [Industry consultation for multilingual voice and text services](https://bhashini.gov.in/static/media/Industry%20Consultation%20for%20RFE%20for%20BHASHINI%20System%20Integrators%20for%20VoiceText%20Multilingual%20Solution%20for%20the%20BHASHINI%20project.861d93eece0c5ffac947.pdf).
3. Qualcomm. [Qualcomm AI Hub documentation](https://app.aihub.qualcomm.com/docs/index.html) and [Get Started](https://aihub.qualcomm.com/get-started).
4. Mohanty et al. [PlantVillage Dataset](https://github.com/spMohanty/PlantVillage-Dataset) and “Using Deep Learning for Image-Based Plant Disease Detection.” 2016.
5. Xu, Sun and Zhang. [Quantifying the reliability gap in cross-domain plant disease classification](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2026.1826962/full). Frontiers in Plant Science, 2026.
6. DFRobot. [SEN0604 RS485 four-in-one soil sensor](https://wiki.dfrobot.com/sen0604/).
7. DFRobot. [SEN0605 Modbus RTU reference](https://wiki.dfrobot.com/sen0605/docs/21024).
8. Government of India Open Government Data Platform. [Current daily price of commodities from markets (mandi)](https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi). Updated 22 May 2026.
9. Ministry of Agriculture and Farmers Welfare. [Pradhan Mantri Fasal Bima Yojana portal](https://pmfby.gov.in/).
10. Ministry of Agriculture and Farmers Welfare. [PMFBY operational guidelines](https://pmfby.gov.in/pdf/Revamped%20OGs_Final.pdf).

## Repository evidence used

- `src/routes/index.jsx`
- `package.json`
- `backend/app/main.py`
- `backend/app/core/database.py`
- `backend/app/farm_state/store.py`
- `backend/app/routers/farm_state.py`
- `backend/app/routers/device_ingestion.py`
- `backend/app/services/crop_health.py`
- `backend/app/services/weather.py`
- `agent/src/kisansathi_agent/server.py`
- `agent/src/kisansathi_agent/tools.py`
- `ml/MODEL_DECISION_RECORD.md`
- `docs/sih26180/TEAM_IMPLEMENTATION_PLAN.md`
- `docs/sih26180/AMAN_FUNCTION_MATRIX.md`
- `docs/sih26180/PRANAV_CODEX_INTEGRATION_STATUS.md`
