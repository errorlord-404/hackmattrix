# Farm lifecycle workflow

This reference defines how the KisanSathi agent combines existing tools. Read
only the section relevant to the farmer's request, or all sections for a
whole-farm plan.

## Next-crop and season planning

### 1. Bind the decision to a field

1. Use `get_profile` for preferred language and recorded state/district.
2. Resolve the exact field with `get_field` or `list_fields`.
3. Use `get_field_timeline` to identify the previous crop, crop family when
   supported by a source, stage history, harvest timing, and repeated-cropping
   pattern. If the timeline is missing or ambiguous, ask the farmer rather than
   guessing.
4. Confirm the intended sowing month/season, available irrigation, area,
   household-versus-market goal, budget, labour limits, and risk preference
   when they can change the shortlist.

### 2. Build a soil evidence card

Call `get_soil_health`, `get_latest_field_observations`, and
`list_device_health`. Record each available value with unit, source, observed
time, and freshness:

- pH and EC/salinity;
- organic carbon or organic matter;
- laboratory or sensor nitrogen, phosphorus, and potassium;
- soil moisture and temperature;
- texture/soil type, drainage, and any known erosion or waterlogging history;
- micronutrients only when a valid test returned them.

Separate laboratory results, Soil Health Card records, calibrated sensors, and
farmer observations. Do not compare values whose units or extraction methods
are incompatible. Treat low-cost in-situ NPK readings as screening signals
until locally calibrated against laboratory samples. If the available evidence
cannot support nutrient or crop suitability, recommend the specific missing
test instead of inventing a value.

### 3. Build a weather and water evidence card

Use `get_weather_for_field` and `get_weather_alerts_for_field` for the stored
field coordinates. This supports immediate operations and the near-term
forecast only.

For a sowing window beyond the returned forecast:

1. Search for the newest official seasonal outlook for the field's region and
   note its issue date and horizon.
2. Search official crop packages for temperature, rainfall, sowing-window and
   water requirements for each candidate.
3. Use historical climate normals only as background probability, not a
   forecast for a specific future day.
4. Record water-source reliability, irrigation method, drainage/flood exposure,
   drought risk and heat risk from farmer input or authoritative evidence.

Never answer “rain will arrive next month” from a five-day forecast or climate
normal. Express seasonal evidence probabilistically.

### 4. Create and enrich the shortlist

Call `get_crop_options(field_id, season, previous_crop, soil_type)`. Preserve
the returned status, `checks`, `conflicts`, and `missing_evidence`. Use
`list_crops`/`get_crop` to inspect referenced details.

For each plausible candidate, compare:

- rotation: previous crops, shared pest/disease risk, residue effects, nutrient
  demand, and whether a break/legume crop has source-supported value;
- soil: pH/EC/texture/drainage fit and unresolved nutrient constraints;
- timing: locally recommended sowing window and crop duration;
- climate and water: near-term establishment conditions, seasonal risk,
  irrigation access and drainage;
- operations: seed access, labour, machinery, storage and transport;
- farmer objective: cash flow, household use, quality/organic/export goal and
  risk tolerance.

Do not use a universal rule such as “always plant a legume” or “never repeat a
crop.” Rotation effects are crop-, pest-, soil-, residue- and region-specific.
Reject or flag a candidate when an authoritative conflict is present; otherwise
show missing evidence.

### 5. Compare economics

For each shortlisted crop:

1. Use `get_market_summary`, then `get_market_history` and `get_market_trend`.
   Match commodity/variety/grade, unit, market, observation date and source.
2. Use `get_msp` and `compare_msp_with_market` where the crop is actually
   covered. MSP publication does not guarantee procurement.
3. Use `get_ledger_summary` and `list_ledger_entries` for farmer-recorded costs
   and previous experience, without treating historic cost as a current quote.
4. Use `recommend_seeds`, `recommend_fertilizers`, machinery and marketplace
   tools as reference/discovery. Current price, stock, dose, logistics and
   service availability must be confirmed.
5. Use `calculate_profit` only after a yield, sale price, quantity, and expense
   assumptions have been explicitly sourced or supplied. Keep all candidates
   in the same area, currency, unit and time horizon.

At minimum calculate:

`net profit = sale revenue - seed - nutrients - crop protection - labour - machinery - irrigation/energy - finance - harvest - packaging - storage - transport - market fees - expected loss`

If many components are unknown, provide a cost checklist rather than a false
number. With sufficient inputs, show conservative, base and optimistic cases.
Do not extrapolate a short price trend across an entire growing season without
an appropriate model and evaluation.

### 6. Recommend and hand off

Return a compact ranked comparison. Name one best-supported candidate only if
the evidence distinguishes it; otherwise present a tie or conditional choice.
State why it fits, why the next option lost, the weakest assumption, and what
could reverse the decision.

After the farmer chooses, offer—do not automatically perform—the relevant
writes: `start_crop_cycle`, `create_field_task`, `create_reminder`, or a
farmer-confirmed ledger entry. Obtain explicit confirmation immediately before
each persistent change.

## Crop-stage execution

First call `get_field_timeline` and `get_crop_stage_action_proposals`. Use the
recorded current stage, not crop age alone. Combine only the tools relevant to
the stage:

| Stage | Evidence and tools | Typical output |
| --- | --- | --- |
| Land preparation | soil health, weather, machinery, ledger | test/land-preparation checklist and verified service options |
| Seed treatment and sowing | crop record, seed references, short forecast, tasks | sowing-window checks and label/official-package reminders |
| Germination and vegetative | observations, weather, device health, irrigation, crop health | scouting and irrigation priorities |
| Flowering and fruit/grain filling | crop health, weather alerts, moisture, tasks | heat/water/pest risk actions with escalation thresholds |
| Maturity and harvest | stage, forecast, machinery, buyer/mandi evidence | harvest-window and logistics comparison |
| Post-harvest | buyer/exporter/packhouse discovery, mandi/MSP, quotes | grade/store/sell scenarios and direct-verification checklist |

Convert advice into two or three prioritized actions. `create_field_task` and
`create_reminder` require farmer confirmation. Do not imply that task creation
executed physical work.

## Crop-health triage

1. Identify the exact field and load its current crop/stage, recent weather,
   soil/irrigation evidence and alerts.
2. Ask the farmer to confirm the crop. A router suggestion may narrow the
   question but must not silently select a disease specialist.
3. Use `diagnose_crop` only with the original image and confirmed crop when
   known. Preserve model ID/version, candidates, confidence, unsupported or
   inconclusive status, and warnings.
4. If the host model can inspect images, use that as a second qualitative check
   for visible agreement/disagreement—not as proof. Look for distribution,
   affected plant parts, lesions, insects, wilting and non-disease explanations.
5. Ask targeted follow-ups: onset, field distribution, underside of leaves,
   irrigation/rain, recent inputs and neighbouring cases.
6. Search only current authoritative crop-specific pest/disease advisories and
   integrated pest-management guidance when needed. Cite exact sources and
   geography.
7. Give triage: likely possibilities, confidence, safe inspection steps,
   conditions requiring a local extension officer/agronomist, and what sample
   or additional photo is needed.

Do not convert visual similarity into a definitive diagnosis. Do not recommend
a pesticide dose or restricted product without the exact crop, target, product
label/official recommendation, formulation, local authorization, pre-harvest
interval and safety context.

## Irrigation and weather-risk support

Use `get_latest_field_observations`, `list_device_health`,
`get_weather_for_field`, `get_weather_alerts_for_field`,
`list_irrigation_events`, and `get_irrigation_advice` together. Confirm units,
sensor freshness and whether a recent irrigation event may make the reading
temporarily misleading.

Explain whether the backend screen recommends irrigating, waiting for rain, or
checking the sensor. State that thresholds need local crop/soil calibration.
Never claim that the agent turned equipment on. Only
`record_irrigation_event` is available, and it records a farmer-confirmed past
event after explicit confirmation.

For drought, flood, heat, wind or heavy-rain risk, organize advice as:

- before: source-backed warning, preparation and prioritized tasks;
- during: human-safety-first checks and no risky field entry;
- after: damage observations, crop-health/soil reassessment, documentation and
  applicable scheme discovery.

## Support, inputs and market discovery

- Use `query_support_catalog` for a bounded first pass over schemes, machinery
  and marketplace records when state/district/category filters answer the
  request.
- Use `find_nearby_machinery` or
  `find_nearby_marketplace_listings` for radius searches around an exact field.
- Use `recommend_seeds` and `recommend_fertilizers` as reference catalogs, then
  supplier discovery if available. A catalog recommendation is not a soil-test
  prescription, stock claim, or quote.
- Use `find_logistics_providers`, `find_crop_buyers`, and `find_exporters` as
  directories. APEDA importer/exporter or packhouse presence does not prove a
  live order, transport service, acceptance or capacity.
- Compare only quotes the farmer/provider supplied with
  `compare_marketplace_quotes`, `compare_machinery_costs`, or
  `compare_logistics_options`. Do not fabricate missing charges.

For harvest sale decisions, match crop/variety/grade and observation date,
compare nearby mandis and MSP, then subtract explicit transport, handling,
fees, storage and expected-loss assumptions. “Store” is appropriate only when
the projected price gain still exceeds those costs and quality risk; otherwise
show that the evidence is insufficient.

## Web source priority

Prefer the most local authoritative source that covers the decision:

1. current Government of India/state department/IMD/ICAR/SAU/commodity-board
   publication or API;
2. a current official scheme, label, market, MSP or export document;
3. peer-reviewed primary research that matches crop, region and conditions;
4. clearly labelled secondary explanation only when primary evidence is
   unavailable.

For high-impact advice, corroborate material claims when practical. Never cite
a search-result snippet as the evidence; open the underlying page. Preserve
publication date and direct URL and explain when evidence is national rather
than district-specific.
