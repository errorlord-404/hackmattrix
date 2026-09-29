# Top-20 India crop dual offline/online workflow plan

## Outcome

KisanSathi will provide the same farmer capability through two explicit paths:

1. **Offline:** farmer-local data plus a versioned, inspectable rule/knowledge
   catalogue. It always says that it is local and cannot claim live weather,
   prices, availability, or web research.
2. **Connected Electron:** the same user-initiated decision is queued to the
   farmer-scoped advisor. The advisor reads the permitted KisanSathi tools,
   obtains current evidence where available, and returns a contextual answer in
   chat. It does not bypass approval for writes or cause real-world actions.

The system must never silently substitute an offline answer for an online one,
or present a local catalogue value as a live recommendation.

## 1. Define the supported crop cohort and its governance

There is no official, single “top 20 crop” list that combines field crops and
horticulture. The v1 cohort is therefore a **published product coverage
decision**, refreshed annually from official DES area/production data and
reviewed by an agronomist—not an assertion of a universal production ranking.

| Group | v1 crops | Why included |
| --- | --- | --- |
| Cereals/millets | Rice/paddy, wheat, maize, pearl millet/bajra, sorghum/jowar | Broad national acreage, staple importance and varied monsoon exposure. |
| Pulses | Chickpea/gram, pigeon pea/tur, mung/moong, black gram/urad, lentil/masoor | Major Indian pulse systems with different seasons and pest/irrigation patterns. |
| Oilseeds | Soybean, groundnut, rapeseed-mustard, sesame | High-value seasonal systems with differing rainfall and drainage risks. |
| Commercial crops | Sugarcane, cotton | High area/value, longer crop cycles and machinery/logistics needs. |
| Horticulture | Potato, onion, tomato, banana, mango | Widely relevant produce with distinct quality, disease and post-harvest workflows. |

**Acceptance criteria**

- Each crop has a stable `crop_id`, local-language names, synonyms, category,
  season and state/agro-climatic applicability.
- A `coverage_score` is calculated from official area, production, farmer
  demand and available validated knowledge packs; the ranking inputs and date
  are retained.
- Crops with missing safety-critical packs are displayed as `partial_support`,
  not silently covered.
- The crop list is reviewable, versioned and can be expanded with regional
  crops such as chilli, cabbage, turmeric, grapes or coconut after evidence
  packs pass the same gate.

## 2. Create a versioned crop knowledge-pack schema

Create one signed/validated JSON or SQLite pack per `crop_id + region +
season + version`, rather than embedding thresholds inside React or prompts.

```text
CropKnowledgePack
  identity: crop_id, version, source_set, reviewed_at, valid_from/to
  scope: state/district/agro_climatic_zone, season, soil/drainage constraints
  phenology: canonical stages, stage transitions, expected observation types
  moisture: lower/target/upper bands, unit, sensor/calibration assumptions
  irrigation: rule inputs, rain/rainfall holds, drainage flags, confidence
  nutrient: evidence requirements, never a dose without verified source
  crop_health: symptom checklist, photo protocol, escalation/red-flag rules
  rotation: predecessor conflicts and missing-information questions
  harvest/post_harvest: readiness checklist, storage/quality record fields
  market: required price/MSP/grade/market freshness fields (no hard-coded price)
  citations: official/source URLs, geography, publication date, reviewer
```

Validation must reject packs with no provenance, invalid bands (`lower >
target`, `target > upper`), unrecognised stages, expired sources, or a
recommendation that names a chemical/dose without a reviewed source.

## 3. Implement the offline engine first

### 3.1 Inputs and storage

- Store farmer-local fields, field geometry, crop cycles, sensor observations,
  manual observations, tasks, irrigation records and the selected knowledge
  pack in the local SQLite state.
- Keep sensor source, unit, calibration state, observed time, device health and
  simulation marker on every reading.
- Treat NPK, EC and moisture as screening observations until calibration and
  units are verified; never substitute them for a laboratory soil test.

### 3.2 Generic offline decision contract

Every offline service returns:

```json
{
  "mode": "offline_catalog",
  "decision": "candidate | attention | defer | insufficient_data",
  "inputs_used": [],
  "catalog_version": "crop-pack/v1.2",
  "bounds_or_rules": [],
  "explanation": "",
  "missing_evidence": [],
  "next_farmer_action": "",
  "confidence": "low | medium",
  "does_not_do": ["live research", "actuation"]
}
```

### 3.3 Offline service matrix

| Service | Offline catalogue/rule | Required local inputs | Never claim offline |
| --- | --- | --- | --- |
| Field/map | boundary validation, centroid, acreage sanity warnings | farmer-drawn polygon | legal survey, GPS acquired without consent |
| Soil/sensors | unit/freshness/calibration checks and broad screening bands | reading, unit, source, timestamp | laboratory result or definitive nutrient prescription |
| Weather | last cached snapshot plus stale-age label | cached forecast | current/real-time forecast |
| Irrigation | crop-stage lower/target/upper band and rain-free local rule | moisture, crop, stage, recent irrigation | weather-aware dynamic target or pump control |
| Crop planning | season/rotation/soil candidate filter | crop history, season, soil evidence | live MSP/demand/profit/export eligibility |
| Crop health | symptom checklist, photo-quality score, red-flag escalation | crop, symptoms, optional local model result | definitive disease diagnosis or pesticide dose |
| Market/logistics | saved source-attributed directory/cache and cost checklist | crop, location, cached listings | stock, booking, current price/buyer demand |
| Schemes/finance | saved eligibility checklist and record templates | farmer-provided facts | current eligibility, sanction or payment |
| Tasks/reminders | local task state and stage checklist | field/cycle/action | physical completion or notification after app closes |
| Reports | local evidence and provenance export | stored facts | a forecast or unrecorded farm activity |

## 4. Make connected advisor review the universal second path

### 4.1 Event envelope

All **farmer-initiated semantic decisions** from Electron use one queue, not
individual page-to-agent implementations:

```json
{
  "event_id": "uuid",
  "workflow": "irrigation-review",
  "field_id": "farmer-scoped field id",
  "offline_result_id": "optional local decision id",
  "user_intent": "review irrigation target",
  "input_via": "ui-irrigation-review",
  "created_at": "ISO-8601"
}
```

The existing `requestAdvisorReview()` gateway is the client entry point. It
queues a request only when the Electron/Codex harness is available and network
connectivity exists. Typed and voice chat already enter the same conversation.

Do **not** send passive page loads, polls, or every API GET to the agent: that
would create duplicate/stale decisions and cost. Send a semantic farmer action
such as “review”, “compare”, “diagnose”, “find support”, or “create a proposed
task.” Each review uses the current state at tool-call time, not UI values
copied into a prompt.

### 4.2 Advisor workflow

For every event:

1. Resolve the exact field and farmer scope; stop and ask if ambiguous.
2. Read only the necessary local evidence: field/crop timeline, relevant
   sensor observations, device health, existing local result and recorded
   history.
3. Refresh or research only changing evidence appropriate to the workflow:
   field weather, official advisories, MSP/market record, official scheme,
   directory/provider evidence, or crop-health source.
4. Compare online evidence with the offline result and identify which input
   changed the decision.
5. Return a farmer-facing answer with source/date/geography, confidence,
   missing evidence, risks and the next 1–3 actions.
6. For a write or external effect, preview the exact change and require an
   explicit farmer confirmation. Never actuate equipment, purchase, book,
   sell, pay, message externally or mark physical work complete.

### 4.3 Tool policy

Expose the complete **farmer-safe KisanSathi tool inventory**, not unrestricted
OS, shell, arbitrary network or database access. Read tools can run for the
event. Persistent tools retain backend idempotency and the existing approval
gate. Tool results are always farmer-scoped and carry source/freshness data.

## 5. Deliver each service as a vertical slice

### Phase A — foundation

- Formalise `CropKnowledgePack`, validator, provenance model and pack registry.
- Add an `AdvisorEvent` audit record with event ID, workflow, local-result
  version, disposition (`queued`, `answered`, `offline`, `unavailable`) and no
  hidden prompt secrets.
- Replace remaining embedded crop thresholds with registry lookup.
- Add shared Electron connection state: network, backend health, advisor
  harness status and cache age.

### Phase B — water and soil (all 20 crops)

- Complete moisture/stage bands for the 20 packs, including generic fallback
  and `partial_support` behavior.
- Keep the present irrigation offline catalogue endpoint and expand it to read
  the selected pack; retain lower/target/upper in the response.
- Add online advisor review cards for irrigation, sensor/soil health and
  weather. The advisor refreshes field weather and proposes a **reviewed
  recommendation**, never a controller command or uncalibrated litres.
- Test dry, normal, stale sensor, recent irrigation, missing calibration,
  forecast rain, heavy rain and offline scenarios per crop category.

### Phase C — crop selection, lifecycle and tasks

- Implement pack-backed season, rotation, soil/drainage and water-access
  candidate rules for all 20 crops.
- Provide offline comparison cards with missing evidence; connected review
  obtains dated official advisory plus MSP/market evidence and asks the farmer
  to choose higher yield, export quality or organic farming before ranking.
- Route “what next?” and task proposals through the advisor event gateway,
  then keep task creation and notification farmer-confirmed.

### Phase D — crop health and vision

- Add per-crop symptom taxonomy, photo requirements, severity/red-flag and
  escalation packs; begin with the 20 cohort rather than promising all pests.
- Use a pre-trained VLM/local specialist only as triage. Store model/version,
  crop confidence, out-of-distribution signal and limitations.
- Offline path: photo quality + symptom checklist + model availability state.
  Connected path: agent combines field context with a current official advisory
  and asks for an expert when evidence conflicts or severity is high.
- Do not output pesticide brand, mixture or dose without an applicable,
  reviewed official/label source and local context.

### Phase E — market, services, logistics and export readiness

- Offline: cached source-attributed MSP/market/listings and freshness label;
  support record templates and comparison checklists.
- Connected: agent researches dated official sources and queries Mongo-backed
  records for machinery, transport, packhouse, buyer and exporter discovery.
- Separate discovery from booking/availability. Add export-quality packs only
  for crops with sourced traceability, residue, testing and packhouse
  requirements.

### Phase F — finance, schemes, reports and notifications

- Offline: farmer ledger, local scheme checklist and report provenance.
- Connected: agent uses current official scheme details and source-attributed
  market evidence; it never claims approval, disbursement, eligibility or
  profit without required evidence.
- Notifications are in-app/local while Electron is open; no claim of background
  delivery after closure.

## 6. Migrate screens with a mandatory checklist

For each screen—Fields, Map, Soil, Weather, Crop Guide, Irrigation, Tasks,
Pest & Disease, Market, Schemes, Finance, Machinery, Marketplace and Reports:

1. List its offline input fields and catalogue version.
2. Add an offline/connected status badge and cache age where applicable.
3. Make each decision button produce a local result first.
4. Add a single “Ask AI to review” action that calls
   `requestAdvisorReview({ workflow, fieldId, prompt })`.
5. Give the agent a workflow-specific prompt listing mandatory evidence,
   safety constraints and questions it may ask.
6. Render the returned answer in the existing conversation, with a link back
   to the originating screen/result.
7. Add offline, online-success, advisor-unavailable, stale-cache and
   confirmation-required tests.

## 7. Data and quality gates

### Dataset/provenance gate

- Every crop pack source has publisher, URL, geography, date, reviewer and
  expiry/review date.
- Pack changes are reviewed by a domain expert and test fixtures are labelled
  `simulation`/`demo`.
- No fabricated sensor, weather, market, disease, stock or quote values.

### Evaluation gate

- Build a 20-crop × workflow matrix: irrigation, sowing, health, market and
  post-harvest for each applicable crop.
- Maintain red-team cases: wrong crop, wrong field, stale weather, missing
  sensor unit, rain/waterlogging, uncalibrated volume, unknown disease,
  unavailable provider and offline reconnection.
- Score offline rules separately from online answers for provenance, correct
  uncertainty, safe action boundary, factual consistency and farmer-language
  clarity.
- Block release if any path claims actuation, current evidence while offline,
  unsupported disease certainty, unsourced price/availability, or an
  unconfirmed write.

### Observability gate

- Capture event ID, workflow, decision mode, pack version, tool names,
  source freshness, completion/error reason and explicit confirmation state.
- Do not log farmer secrets, raw private images or full sensitive prompts in
  analytics.
- Show a judge/demo panel with local-vs-connected mode, evidence sources,
  cache age and no-actuation status.

## 8. Completion definition

The plan is complete when all 20 crop packs pass validation; every listed
screen exposes a labelled offline result and one connected advisor event;
offline and online test matrices pass; connected answers use only farmer-safe
tools; all data sources are traceable; and every irreversible action remains
explicitly farmer-confirmed.

## Source baseline for crop-scope refresh

- [DES Agricultural Statistics at a Glance](https://desagri.gov.in/document-report-category/agriculture-statistics-at-a-glance/)
- [DES Area, Production & Yield query reports](https://www.data.desagri.gov.in/website/apy-index-report-web)
- [ICAR overview of Kharif/Rabi/Zaid cropping patterns](https://icar.gov.in/sites/default/files/Circulars/India_BRICS_Agriculture_Report.pdf)
- [DES five-year estimates](https://desagri.gov.in/statistics-type/five-year-estimates/)
