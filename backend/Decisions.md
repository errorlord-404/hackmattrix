# Decisions

## Crop.health receives only documented visual input
**Date:** 2026-09-26
**Context:** Crop.health rejected the prior image request because it included
unsupported crop and language body fields, even though the operator's API key
was valid.
**Decision:** Send only the documented base64 image list and parse disease
candidates from the provider's nested result envelope. Keep farmer-confirmed
crop, sensor readings, weather, and recommendation grounding inside
KisanSathi's consented evidence record.
**Trade-offs accepted:** The provider does not receive extra farm context,
which protects privacy and avoids treating local evidence as a visual-model
input; Codex must reconcile that evidence separately after the assessment.

## Offline irrigation is an explicit configurable screening mode
**Date:** 2026-09-26
**Context:** A field may have a moisture observation while connectivity and a
forecast are unavailable. Reusing a weather-aware response would falsely imply
that a current forecast had been evaluated.
**Decision:** Keep the existing weather-aware endpoint as the compatibility
default and add an opt-in `offline_catalog` mode with an explicit local
crop/stage lower-target-upper band. The API returns the mode and all three
bounds, while Electron sends connected cases to the agent for a fresh
field-weather review.
**Trade-offs accepted:** The compact catalogue is a clearly labelled,
configurable demo screening baseline, not a crop-specific hydrology model or
controller calibration. It needs verified local calibration before production
use.

## Presentation weather fixtures are explicit and field-scoped
**Date:** 2026-09-25
**Context:** A live short-range forecast cannot reliably provide a heavy-rain
case during a hackathon presentation, but inventing a forecast would undermine
the provenance story.
**Decision:** Add opt-in Tomato demo fixtures that write only the selected
farmer field's forecast snapshot under a `simulation:tomato-weather-fixture`
provider marker. The UI names the fixture and offers a clear action to use live
weather again. The heavy fixture supplies 30 mm over 48 hours, sufficient to
exercise the tested waterlogging rule. It is never presented as a live weather
provider result and never drives hardware.
**Trade-offs accepted:** The fixture provides repeatability rather than
meteorological realism; live weather remains the default outside the demo.

## Irrigation screening distinguishes rain chance from waterlogging risk
**Date:** 2026-09-25
**Context:** A low moisture reading alone can prompt unnecessary watering when
heavy rain is expected shortly, while a rain probability alone cannot safely
postpone a critically dry crop.
**Decision:** Use only a location-matched forecast snapshot and preserve the
existing critical-moisture guard. A heavy-rain branch requires a forecast
rainfall amount of at least 25 mm in 48 hours plus a strong probability when
available. It returns a 0% hold for ordinary deficits, drainage guidance when
moisture is already adequate, or a 25% emergency split for a critically dry
root zone. Percentages reference the farmer's calibrated normal application;
the system does not fabricate litres, durations, or actuator commands.
**Trade-offs accepted:** Broad thresholds are understandable for the prototype
but need crop, soil, drainage and irrigation-system calibration before field
automation.

## Crop-health images use staged consent and evidence separation
**Date:** 2026-09-25
**Context:** A farmer-facing chat must combine a photo with live or simulated
field context without silently sending personal images to a hosted model or
inventing a fused diagnostic certainty.
**Decision:** The client first stages an image privately, then obtains a
server-issued, expiring consent receipt naming the crop-health provider before
the hosted provider can receive that image. The diagnosis record stores the
provider response separately from an immutable latest-observation snapshot.
Sensor values are used only for descriptive consistency, missing-data and
provenance guidance; they never rerank provider candidates or create a
combined confidence score. Direct legacy image diagnosis remains local-only.
**Alternatives considered:** Send image bytes through the chat model, make the
browser call the provider directly, or use soil values to adjust visual-model
confidence. These approaches obscure consent, secret handling, or evidence
boundaries.
**Trade-offs accepted:** The interaction adds a clear confirmation step and
the hosted integration requires server configuration, but it keeps sharing
intent auditable and lets the prototype run safely without hardware.

## Tomato prototype simulation is opt-in and source-separated
**Date:** 2026-09-25
**Context:** Hardware logistics can prevent the hackathon demo from producing
live sensor packets, but the agent still needs to demonstrate changing,
condition-aware soil decisions.
**Decision:** Persist a deterministic, field-scoped simulator in each farmer's
existing SQLite store and write its seven values through `sensor_readings`.
Every row uses `simulation:tomato-demo:v1`, a bounded confidence, and canonical
units. Normal observation reads advance a running simulation only when its
15-second tick is due; the frontend also polls while the demo is visible.
The simulator is disabled by default and the local demo launcher explicitly
enables it. Simulated irrigation changes only future demo values and never
creates a physical irrigation event or actuator call.
**Alternatives considered:** Put random values in React, pretend the values
were device packets, or add a background process that could cross farmer
boundaries. The chosen path reuses the agent's existing read contract and
keeps provenance auditable.
**Trade-offs accepted:** Demo values are persisted in the local audit trail and
can temporarily be the newest observation for a field while running, but the
source badge and prompt policy prevent them from being represented as hardware
or lab evidence.

## APEDA directory pagination is approved with source-bound limits
**Date:** 2026-09-09
**Context:** The initial marketplace importer read a single APEDA exporter
page, leaving nationwide marketplace coverage sparse. APEDA also publishes
public pagination for recognised packhouses and FarmerConnect importers.
**Decision:** Follow only the finite page range advertised by each public
directory, with a configurable per-page delay and operator page caps. Store
only the fields visible on public cards/profile links. Packhouses are logistics
facilities, not carriers; importers are potential buyers, not active demand.
Do not traverse contact buttons, capture their query-string phone/email values,
decrypt identifiers or infer availability/price.

## Government source boundary for machinery and schemes
**Date:** 2026-09-09

MahaDBT is used for Maharashtra agricultural scheme detail pages because it
publishes the catalogue and eligibility/documents on public HTTPS pages. The
source URL, stable source ID and fetch time are retained.

The FARMS dashboard is used for machinery-network evidence, and its public
KisanRath CHC feed is used for provider/vehicle discovery. Provider rows keep
the published agency, address, coordinates, phone, vehicle and cost fields;
dashboard counts remain `record_kind=network_status` rows. Neither path claims
live availability or creates a booking.

The official FARMS API help also lists individual CHC/implement endpoints that
require an `EncryptedRequest`; we do not reverse-engineer those private flows.
The public KisanRath CHC feed is sufficient for the current read-only provider
directory and is bounded by a date window and stable transaction/vehicle IDs.

Records WHY a non-obvious choice was made. Not every change needs an entry -
only ones where a reasonable person might ask "why did you do it this way?"

## Diagnostics, audit, and export stay farmer-scoped
**Date:** 2026-09-09
**Context:** A field-deployable demo needs recovery and failure evidence without
exposing filesystem paths, credentials, or another farmer's records.
**Decision:** Diagnostics, append-only audit events, and JSON export all use the
validated `X-Farmer-ID` SQLite boundary. Demo reset is explicit and only removes
records with the local-demo provenance marker.

## Sarvam keys entered in Settings are runtime-only
**Date:** 2026-09-09
**Context:** A desktop settings screen needs to enable voice and translation,
but storing a provider API key in browser storage, SQLite, MongoDB, a repo file
or a response body would expand the secret-exposure surface.
**Decision:** Accept a key only over the local backend configuration route,
keep it in the active process memory, and expose configuration status plus
non-secret defaults only. Restarting the backend requires entering the key
again or configuring it through deployment environment variables.
**Alternatives considered:** Persist it in localStorage, put it in the farmer
SQLite store, write `.env` from the UI, or send requests directly from React.
**Trade-offs accepted:** The user must re-enter a UI-supplied key after restart,
but the browser bundle and persistent farmer/reference stores never contain it.

## Local prototype data is explicit demo/reference data
**Date:** 2026-09-09
**Context:** Reference-driven screens were empty when MongoDB was not running,
but quietly fabricated market prices, MSP values, supplier availability, or
scheme eligibility would be unsafe and misleading.
**Decision:** Run MongoDB locally in a named Docker volume bound only to
`127.0.0.1` and populate it through an idempotent script. All local records
are tagged `local_demo_seed_not_live` or carry equivalent visible wording and
link to official portals only as verification destinations.
**Alternatives considered:** Hard-code values in the frontend, leave all
screens empty, or present static figures as live data.
**Trade-offs accepted:** The UI becomes demonstrable offline, but these entries
cannot drive recommendations, purchases, claims, bookings, or field decisions;
a source-attributed ingestion path is required before deployment.

## Controlled demo prefers EfficientNetV2-B0 without expanding authority
**Date:** 2026-09-09
**Context:** On the same deterministic 400-image controlled tomato split, dynamic TFLite accuracy was 95.50% for the previous MobileNetV3-Small artifact, 96.50% for MobileNetV3-Large and 97.75% for EfficientNetV2-B0. No candidate has Indian field, unknown/OOD, agronomist or target-device evidence.
**Decision:** Point only the explicit demo launcher at the checksum-bound EfficientNetV2-B0 dynamic artifact and pass its rejected-for-field-release manifest to runtime. Keep normal deployment unconfigured and all results review-only.
**Alternatives considered:** Promote the smaller full-INT8 export immediately, keep the less accurate prior demo, or label the controlled winner field-ready.
**Trade-offs accepted:** The dynamic model is larger (6.58 MB) and device performance is unknown, but it has the strongest balanced controlled metrics. No treatment or actuation authority is added.

## Marketplace discovery uses an approved-source registry
**Date:** 2026-09-06
**Context:** The project needs vendors, machinery, logistics, buyers and export contacts, but unrestricted scraping produces unverifiable listings and can violate provider terms.
**Decision:** Store source-attributed JSON-LD records only from operator-configured HTTPS public pages. Use one typed directory collection/API/MCP tool; it supports discovery only and does not create transactions.
**Alternatives considered:** Scrape Google Maps/general marketplaces, hard-code demo vendors, or make separate unverified scrapers per category.
**Trade-offs accepted:** The directory begins empty until approved sources are configured and many real services will need partnership/API integration later, but every displayed item stays traceable and the product does not promise bookings or prices it cannot verify.

## Marketplace quote comparison is explicit-input only
**Date:** 2026-09-06
**Context:** Farmers need to compare machinery and logistics providers after directory discovery, but sources rarely publish comparable all-in quotes.
**Decision:** Accept supplier/farmer-provided line items and calculate a transparent total, ranking only inside each currency group.
**Alternatives considered:** Estimate freight from distance, convert currencies automatically, or publish a lowest-price recommendation from incomplete listings.
**Trade-offs accepted:** The user must obtain quotes and verify identical units; the service will not fabricate distance, tax, insurance, exchange-rate, or any unpublished charge.

## MSP comparison keeps procurement uncertainty visible
**Date:** 2026-09-06
**Context:** Comparing MSP with a mandi price can help explain a distress-sale decision, but it cannot establish procurement eligibility or centre availability.
**Decision:** Compare only the newest source records and return the source/observation metadata with a procurement verification warning.
**Alternatives considered:** Recommend a sale path from the price difference alone, or omit MSP comparison entirely.
**Trade-offs accepted:** The result is a decision-support reference, not a promise that the farmer can sell at MSP.

## APEDA exporter ingestion is bounded to its public directory page
**Date:** 2026-09-06
**Context:** APEDA's Agri Exchange exporter page contains public directory cards but its contact workflow uses client-side protected identifiers.
**Decision:** Parse only the first public page's name, address, commodity and state using a named adapter; do not use contact controls, decrypt identifiers or expand pagination.
**Trade-offs accepted:** Discovery is incomplete by design, but it avoids collecting protected contact information or imposing load on an official portal.

---

## Agent-facing writes use per-farmer idempotency records
**Date:** 2026-08-18
**Context:** A Codex/MCP client can retry an approved write after a transport timeout, while farmer state is stored in SQLite files selected by the farmer identity boundary.
**Decision:** Store a request hash and serialized response under an `Idempotency-Key` in each farmer's SQLite database. Replaying the same key returns the original response; reusing it with a different payload returns a conflict.
**Alternatives considered:** Trust the MCP client to avoid retries, or deduplicate only in the in-memory agent process. Both fail across process restarts or backend timeouts.
**Trade-offs accepted:** Records require eventual retention/cleanup policy, and deterministic client-generated keys mean an identical payload represents the same logical operation until an explicit operation identity is added.

---

## Seed and fertilizer recommendation scope
**Date:** 2026-08-18
**Context:** The PRD requires `recommend_seed()` and `recommend_fertilizer()`, while the central catalogs currently contain only a limited set of structured fields.
**Decision:** Rank only stored reference records using crop compatibility and optional preferences that map directly to existing fields; do not infer unsupported agronomy.
**Alternatives considered:** Invent soil/weather scoring or block the feature until richer schemas exist.
**Trade-offs accepted:** Recommendations are intentionally narrow now, but the mutator contracts remain stable for later enrichment.

## Official-source ingestion is provenance-first and schema-bounded
**Date:** 2026-08-18
**Context:** The central database needs broad crop/market reference coverage, but government sources expose different fields and update mechanisms. AGMARKNET has a structured daily feed; current MSPs are authoritative PIB HTML tables; fertilizer, disease, seed-supplier, and scheme pages do not provide stable structured records matching the existing models.
**Decision:** Ingest every valid current AGMARKNET row, parse the configured official PIB MSP releases, and derive only commodity name/current mean modal price plus an MSP-matched season for crop catalog entries. Store stable source IDs, URLs, and timestamps on every imported document. Leave unavailable fields null/empty and leave unsupported collections manual until approved source adapters exist.
**Alternatives considered:** Fill missing values with defaults, treat produce varieties as commercial seed inventory, scrape arbitrary third-party aggregators, or allow n8n to write directly to MongoDB.
**Trade-offs accepted:** Crop imports are intentionally incomplete agronomy records and some reference collections remain unpopulated, but every stored fact is traceable and the backend owns validation/idempotency while n8n remains a scheduler only.

## Protected backend sync boundary for n8n
**Date:** 2026-08-18
**Context:** A scheduled workflow must trigger large paginated fetches without duplicating source logic or exposing an unauthenticated mutation endpoint.
**Decision:** n8n calls a token-protected internal FastAPI endpoint; the backend fetches, validates, normalizes, bulk-upserts, and records run telemetry. The workflow runs daily at 06:30 Asia/Kolkata and retries transient failures three times.
**Alternatives considered:** Put scraping and MongoDB credentials directly in n8n nodes, or schedule an in-process FastAPI background task.
**Trade-offs accepted:** FastAPI must be reachable when the schedule fires and the shared webhook token must be rotated like any other secret, but source logic stays tested and reusable from both CLI and n8n.

## Farm State is local SQLite within the existing FastAPI process
**Date:** 2026-08-18
**Context:** The frontend parity plan requires fields, observations, crop lifecycles, alerts, and other farmer-owned state, while the existing service already owns the FastAPI boundary and MongoDB reference APIs.
**Decision:** Keep one SQLite file per temporary `X-Farmer-ID` under `FARM_STATE_DB_DIR`, open it through a FastAPI dependency, and leave shared crops, inputs, schemes, MSP, and market reference data in MongoDB. The header is a development identity boundary, not authentication.
**Alternatives considered:** Put personal state in MongoDB, add a separate service, or use one shared SQLite file. These were rejected because they violate offline/tenant isolation or the request to expand the existing backend only.
**Trade-offs accepted:** The current identity mechanism must be replaced or wrapped by authentication before multi-user deployment, and SQLite operations are intentionally local to the application instance.

## Provider-unavailable responses are explicit
**Date:** 2026-08-18
**Context:** Vision, advisor, and voice providers are not configured in the current repository.
**Decision:** Persist uploads/session messages where appropriate but return `inconclusive` or `provider_unavailable` with no fabricated label, transcript, or recommendation. Weather uses Open-Meteo by default and only uses the empty, explicitly labelled fixture when configured.
**Alternatives considered:** Return demo values to keep screens populated, or fail with an opaque 500. Both obscure provenance or make the client unable to present a safe recovery state.
**Trade-offs accepted:** Some UI workflows remain incomplete until approved providers are configured.

## GovScheme eligibility interface scope
**Date:** 2026-08-15
**Context:** PRD section 22 requires `check_scheme_eligibility()` to accept a farmer state and optionally other criteria, but the current filtering rule is state-only plus nationwide schemes.
**Decision:** Define the mutator interface with optional `eligibility_criteria`, but only apply the state and nationwide filter for now.
**Alternatives considered:** Omit extra criteria from the interface entirely, or attempt to infer eligibility semantics from free-form scheme criteria text.
**Trade-offs accepted:** The interface stays forward-compatible for future actor logic, but non-state criteria remain explicitly unsupported until the PRD defines machine-checkable rules.

## Disease severity representation
**Date:** 2026-08-15
**Context:** The disease collection needs to pair knowledge-base records with ML vision model output, and the requested shape only specified `severity_levels` as a list.
**Decision:** Store `severity_levels` as `List[str]` without enforcing an enum in the backend schema.
**Alternatives considered:** Hard-code an enum such as `low`/`medium`/`high`, or model severity as nested scored objects.
**Trade-offs accepted:** This keeps the collection flexible for different ML output labels and stays aligned with the existing lightweight reference-data CRUD pattern, but leaves canonical severity vocabulary to a later contract decision.

## Seed supplier info shape
**Date:** 2026-08-15
**Context:** The requested seed collection specified a `supplier_info` field name but did not define a nested structure.
**Decision:** Store `supplier_info` as a plain string in both the Beanie document and Pydantic schemas.
**Alternatives considered:** A nested supplier object with contact/address fields, or a free-form dictionary.
**Trade-offs accepted:** This keeps the CRUD surface aligned with the existing simple reference-data models, but defers stricter supplier structure until the API contract is explicitly defined.

## Chose Beanie over raw Motor/PyMongo
**Date:** 2026-08-15
**Context:** Needed an ODM/data layer for MongoDB with FastAPI.
**Decision:** Beanie
**Alternatives considered:** Raw PyMongo (too much boilerplate, no async),
raw Motor (async but no schema validation)
**Trade-offs accepted:** Slightly more setup (needs init_beanie on startup),
but models double as both DB schema and Pydantic validation, matching
FastAPI's existing style.

## Dual database split (central Mongo + local SQLite)
**Date:** 2026-08-15
**Context:** Team debated single vs dual DB architecture.
**Decision:** Central MongoDB (shared reference data: crops, fertilizers,
schemes, MSP) + per-farmer local SQLite (personal farm/sensor/finance data),
per PRD section 8.
**Alternatives considered:** Single MongoDB for everything - rejected because
personal data needs to work offline (PRD section 29) and shared reference
data would be wastefully duplicated per-client otherwise.
**Trade-offs accepted:** This backend service only owns the central DB half;
sync logic between local SQLite and server is a separate concern owned by
another part of the team.

## MarketPrice route ordering
**Date:** 2026-08-15
**Context:** Added a crop-scoped listing endpoint alongside the ID-based lookup.
**Decision:** Keep `/by-crop/{crop_name}` above `/{market_price_id}` in the router so the static prefix resolves before the dynamic ID route.
**Alternatives considered:** Rely on route ordering implicitly or place only the ID route in this router.
**Trade-offs accepted:** Slightly more route definition clutter, but avoids accidental path matching ambiguity.

## Degraded startup for the dual-database service
**Date:** 2026-08-18
**Context:** Farm State is intentionally local and must remain usable when MongoDB is unavailable, while the existing reference-data routers still depend on MongoDB.
**Decision:** Bound the MongoDB server-selection timeout and let application lifespan complete in degraded mode when reference initialization fails. Expose the state through `/health`; Farm State requests continue to use the per-farmer SQLite store.
**Alternatives considered:** Block all startup until MongoDB is healthy, or silently return reference-data placeholders.
**Trade-offs accepted:** Reference-data requests can still fail while the database is offline, but the service does not fabricate shared data and local farmer workflows remain available.

## Frontend farmer identity boundary
**Date:** 2026-08-18
**Context:** The frontend needs a temporary identity until the product's authentication contract is finalized.
**Decision:** Send `X-Farmer-ID` on every Farm State request, sourced from browser local storage with an explicit demo fallback. The API client keeps reference-data requests separate and never sends personal Farm State records to MongoDB routes.
**Alternatives considered:** Reuse the central Farmer document, or put farmer identity in URL paths.
**Trade-offs accepted:** This is not an authentication system; production must replace the temporary header with the approved identity provider before multi-user release.
# Crop-health demo models remain opt-in and fail closed
**Date:** 2026-09-07
**Context:** A controlled-image crop router and tomato specialist have been fine-tuned for the SIH prototype, but neither is field validated.
**Decision:** Enable them only through explicit environment paths and `DIAGNOSIS_PROVIDER=local_hierarchical_demo`. Require farmer crop confirmation, persist model evidence, use a confidence gate, and return review states without treatment advice.
**Trade-offs accepted:** The demo can be shown end-to-end locally, but it cannot silently become a production diagnosis or recommendation engine.

# TensorFlow Lite specialist is crop-confirmed and demo-only
**Date:** 2026-09-07
**Context:** The TensorFlow Hub MobileNetV3 controlled benchmark exports a compact dynamic-range TFLite file, but it has no released crop router, unknown class or field validation.
**Decision:** Add it only as `local_tflite_demo`, require a farmer-confirmed configured crop, and return candidate/model limitations through the diagnosis envelope. Do not use it for unsupported crops or full-INT8 deployment.
**Trade-offs accepted:** The prototype gains an actual TensorFlow inference path while crop routing and field-release responsibilities remain explicit.

# Crop-health acceptance needs confidence and margin
**Date:** 2026-09-07
**Context:** A classifier can report a large top probability while two disease candidates remain too close for safe screening.
**Decision:** TFLite results require both a configurable minimum top score and top-one/top-two margin; failures are persisted as `needs_expert_review`.
**Trade-offs accepted:** More photos enter review, but the model does not hide its ambiguity behind a single label.

# Crop router can suggest but not select a specialist
**Date:** 2026-09-07
**Context:** The proposed vision design identifies a crop before using a crop-specific disease model, but an incorrect router result would select the wrong disease label space.
**Decision:** Keep the router as an optional TFLite component with separate conservative score and margin gates. Persist its ranked candidates and always return `needs_crop_confirmation`; only a subsequent farmer-confirmed request may invoke a specialist.
**Trade-offs accepted:** The UX can require a second confirmation/upload step, but a controlled-data router never silently becomes an agronomic decision.

# TFLite demonstration enablement is explicit and process-local
**Date:** 2026-09-07
**Context:** A local demo must be easy to run for SIH judging, but persisting its paths/provider in a checked-in `.env` would make a controlled-data artifact look like a deployment default.
**Decision:** Provide a launcher that verifies the versioned dynamic-range artifact and supplies environment settings only to the launched backend process.
**Trade-offs accepted:** Operators must deliberately start the demo script, but ordinary backend startup cannot accidentally claim local field-ready diagnosis.

# Irrigation forecast selection is field-scoped
**Date:** 2026-09-07
**Context:** Weather snapshots are cached per farmer store and a farmer may have fields in different microclimates. Selecting the newest snapshot globally could defer water based on another field's forecast.
**Decision:** Select a snapshot only when its latitude/longitude falls within the same 0.01-degree tolerance already used by the field-weather route. If none exists, state that rain was not used in the screening decision.
**Trade-offs accepted:** A plan can have lower confidence without a matched forecast, but it cannot silently use weather for the wrong field.

# Sensor units must be interpretable before deterministic rules use them
**Date:** 2026-09-07
**Context:** Sensor readings previously accepted arbitrary unit text while irrigation compared raw moisture values with percentage thresholds.
**Decision:** Normalize only approved unit aliases at API ingestion and make legacy/unrecognized moisture values insufficient data for irrigation planning.
**Trade-offs accepted:** Some device payloads require a gateway update, but the system avoids treating uncalibrated raw values as agronomic percentages.

# Crop-stage writes use a canonical lifecycle vocabulary
**Date:** 2026-09-07
**Context:** Crop stages were arbitrary free text, making stage-aware irrigation and calendar behavior sensitive to spelling, capitalization, and localization.
**Decision:** Normalize a defined lifecycle vocabulary on new writes and reject unsupported stage names. Existing historic rows remain readable; later crop-specific calendars can map additional stages explicitly.
**Trade-offs accepted:** Some crop-specific wording needs an explicit future mapping, but the rules no longer silently miss a stage due to text variation.

# Action engine records farmer-confirmed tasks only
**Date:** 2026-09-07
**Context:** The project contains recommendations and reminders, but the existing `field_tasks` state had no operational API or agent workflow.
**Decision:** Expose idempotent task creation/listing/status updates; agent task writes are confirmation-gated and labelled by source. Tasks are records, not authorization to purchase, book, apply chemicals, or control hardware.
**Trade-offs accepted:** This establishes an auditable action loop without overclaiming transactional or physical-control capability.

# Finance ledger is farmer-entered, INR-only, and audit-preserving
**Date:** 2026-09-07
**Context:** Finance records were only in browser storage, so they could not participate in the farmer-scoped digital twin or agent workflow.
**Decision:** Store confirmed income/expense entries in the existing per-farmer SQLite database. Limit the first contract to INR; void entries rather than deleting them; return only record-keeping totals. The API cannot make payments, transfers, credit decisions, tax statements, or forecasts.
**Alternatives considered:** Continue localStorage-only finance, create a central Mongo financial database, or permit destructive deletes.
**Trade-offs accepted:** This is durable within the current farmer-scoped backend store but is not yet an offline mobile-sync implementation or an accounting system.

# Device telemetry uses a dedicated provisioned gateway boundary
**Date:** 2026-09-07
**Context:** The existing sensor-reading endpoint is a farmer/agent write record and cannot safely be used as an unrestricted ESP32 ingress point.
**Decision:** Authenticate gateway packets with a provisioned environment-held token, scope each device to a farmer and optional fields, make `(device_id, boot_id, sequence)` idempotent, preserve packet/sample Modbus and CRC evidence, and persist only CRC-valid normalized samples as field readings. Provide device health as a read-only farmer API.
**Alternatives considered:** Allow the device to use `X-Farmer-ID`, expose a device credential to the MCP agent, or discard CRC-failed packets entirely.
**Trade-offs accepted:** Credential provisioning is currently deployment configuration rather than a staff enrollment UI; raw rejected evidence is retained, but neither the gateway nor agent gains pump/actuator control.

# Crop-stage rules may propose actions but never create them
**Date:** 2026-09-08
**Context:** Crop stages were persisted and the task API existed, but farmers still had to infer the next action from disconnected records.
**Decision:** Return a small, generic, read-only stage-action proposal set only for the active cycle. Suppress a proposal when an open task already has the same title. The farmer must explicitly accept it through the UI or a confirmation-gated MCP task write.
**Alternatives considered:** Automatically create lifecycle tasks, let an LLM invent crop-specific actions, or issue crop-input/chemical recommendations from stage alone.
**Trade-offs accepted:** The MVP gives less automation but avoids silently committing work or prescribing inputs without crop-pack/agronomist context.

# Completed local TFLite results must be bound to an evaluated release manifest
**Date:** 2026-09-08
**Context:** A non-crop project image received a high-confidence tomato disease label from the controlled PlantVillage specialist despite score and top-two margin gates.
**Decision:** Remove the mutable completion boolean. Return ranked candidates with `needs_expert_review` unless an operator-mounted versioned manifest has `approved_for_field_release`, matches the configured model and label SHA-256 values, covers the farmer-confirmed crop, and explicitly marks independent-field, unknown/OOD, and agronomist-review gates as passed.
**Alternatives considered:** Keep the completed label with a disclaimer, use a mutable environment boolean, invent a visual non-crop heuristic, or hide candidate evidence entirely.
**Trade-offs accepted:** The demo no longer presents a completed disease result, and a future release requires deliberate manifest maintenance. This is auditable but not cryptographic signing; the approved bundle must still be deployment-controlled.

# Irrigation forecast deferral cannot override critical dryness
**Date:** 2026-09-08
**Context:** The read-only irrigation screen could defer any below-target moisture value when a location-matched forecast probability was high, including a substantially dry reading.
**Decision:** Reserve rain deferral for a small below-target deficit. Below a transparent critical screening bound, recommend an earlier farmer-reviewed irrigation window and keep monitoring the forecast. When an irrigation event is less than 12 hours old and moisture is not critical, request a fresh observation before another application.
**Alternatives considered:** Defer whenever rain probability is high, ignore recent irrigation history, or claim a volume-derived water balance without field capacity/root depth/flow evidence.
**Trade-offs accepted:** The thresholds are still generic screening values, not a crop/soil-specific water balance. The endpoint stays advisory and read-only until calibrated field parameters and actuator safeguards exist.

# Irrigation history records only farmer-confirmed events
**Date:** 2026-09-08
**Context:** The irrigation plan can use a recent event to avoid duplicate advice, but the client and agent had no read contract for the resulting event history.
**Decision:** Expose a farmer-scoped bounded event list with an optional field filter. Preserve entered volume/duration/method/note exactly; do not infer absent values from sensor changes, pump capability, or the plan.
**Alternatives considered:** Keep history write-only, estimate volume from duration, or use a global shared log.
**Trade-offs accepted:** The history is useful for review and future calibrated balances but is not verified flow telemetry or a pump audit.

# Local crop-health demo uses one fast ONNX research model
**Date:** 2026-09-26
**Context:** The installed registry has optional TensorFlow, PyTorch, and ONNX checkpoints, but loading all of them makes a presentation response depend on multiple heavyweight runtimes.
**Decision:** The local demo launcher selects `mesabo_resnet50_onnx` with a maximum of one model.
**Trade-offs accepted:** The output remains a research-only `needs_expert_review` signal; selecting a responsive model does not elevate its confidence or authorize treatment.

# Agent-created tasks notify but never execute work
**Date:** 2026-09-26
**Context:** The farmer needs to see a task the agent creates, but task creation must not be confused with dispatching labour or controlling equipment.
**Decision:** A successfully persisted field task creates a deduplicated farmer-scoped in-app alert. The open Electron client may show that alert as a native notification when the farmer has enabled notifications.
**Trade-offs accepted:** Delivery is not guaranteed while the app is closed, and the agent cannot complete a physical task without a farmer report and confirmation.

# Windows runtime launch paths must be explicitly quoted
**Date:** 2026-09-08
**Context:** The workspace-local MongoDB setup failed on a repository path containing a space because `Start-Process` joined a Mongo argument array without preserving embedded path quoting.
**Decision:** Pass a deliberately quoted Mongo command argument string for filesystem-valued flags.
**Trade-offs accepted:** The launch string is less structurally elegant than a simple array but works reliably for the Windows process API and prevents path splitting.

# Development reload watches source, not mutable runtime installs
**Date:** 2026-09-08
**Context:** The local TFLite demo's Uvicorn watcher detected files written while n8n installed under ignored `backend/.runtime`, then shut down the concurrently paired frontend/backend process.
**Decision:** Exclude `.runtime` from development reload globs while retaining source-code reload.
**Trade-offs accepted:** Runtime-only configuration changes need an explicit restart, but package installation cannot interrupt a demo.

# PowerShell reload globs are passed as option values
**Date:** 2026-09-08
**Context:** Passing a reload-exclude glob as a separate native-command argument
allowed PowerShell to expand it into every file below `.runtime`, preventing
Uvicorn from starting.
**Decision:** Supply the glob in the same argument as `--reload-exclude=`.
**Trade-offs accepted:** The launcher is slightly more platform-specific, but
the local Windows demo keeps source reload without treating runtime files as
command-line arguments.

# Crop option output is evidence screening, not a crop optimizer
**Date:** 2026-09-08
**Context:** The product needs crop-rotation support, but the current shared
catalogue has compatibility metadata and sparse reference prices, not a
validated local yield, nutrient, weather or profitability model.
**Decision:** Return transparent candidate checks for farmer-supplied season,
previous crop and soil type. Mark missing evidence and conflicts; never label a
crop “best,” estimate profit, or initiate an input purchase.
**Alternatives considered:** Rank crops by incomplete reference prices, let an
LLM invent agronomic fit, or block the interface until a full recommendation
model exists.
**Trade-offs accepted:** The first workflow requires farmer/agronomist review,
but it is explainable and cannot overstate what current data supports.

# Farmer diagnosis feedback is a review lead, not a training label
**Date:** 2026-09-08
**Context:** The project needs target-region field data to evaluate and
fine-tune TF Hub candidates, but model output and an unverified correction are
not ground truth.
**Decision:** Persist append-only farmer feedback only with explicit sharing
consent. Return a fixed boundary that it requires expert review and a separate
controlled export before it may join a dataset.
**Alternatives considered:** Automatically add feedback to training folders,
export stored images on consent, or silently relabel a diagnosis.
**Trade-offs accepted:** This creates a useful provenance record but needs a
future governed expert-review/export workflow before any ML use.

# Nearby provider search is bounded and provenance-preserving
**Date:** 2026-09-09
**Context:** Machinery and marketplace results were exact-filtered from a display location string, and the MVP needs field-centered discovery.
**Decision:** Normalize administrative values at the boundary, store optional provider coordinates/provenance, return bounded distance-sorted results, and keep district/list fallback when coordinates are absent. Add a 2dsphere index declaration without making unverified geocoding mandatory.
**Alternatives considered:** Parse display strings in every client, silently geocode every listing, or expose unbounded all-provider results.
**Trade-offs accepted:** Existing un-geocoded records remain discoverable only through explicit fallback paths; a later ingestion job may populate verified points.

# FARMS rows without addresses remain queryable with explicit unknown location
**Date:** 2026-09-09
**Context:** The official FARMS CHC feed contains provider rows without an address, while the legacy machinery response contract requires a location string.
**Decision:** Preserve the row, use `Location not provided by FARMS` only as a display-valid marker, and add `metadata.location_missing=true`. Older rows are normalized at response time as a compatibility guard.
**Alternatives considered:** Drop incomplete provider rows, invent a state/district location, or relax the response contract without a migration.
**Trade-offs accepted:** The row is discoverable but cannot be treated as geographically located; nearby search still requires valid coordinates.
## 2026-09-09 — Diagnostics are operational, not domain data

The readiness panel uses a dedicated farmer-scoped diagnostics route. It reports bounded counts and component availability, but never exposes SQLite paths, farmer identifiers, credentials, or claims that demo records are live. This keeps health checks useful to the launcher and judge while preserving the separate private SQLite/shared Mongo boundary.

## 2026-09-19 — Onboarding is a read-only checklist, not an automatic mutation

The first-open assistant may ask `GET /v1/onboarding-status` to choose a setup question, but profile, field, boundary, and crop-cycle writes remain separate confirmed operations. Boundary quality is reported as farmer-supplied provenance, not independent survey verification. The endpoint reports missing sensor evidence and optional provider readiness without making voice or Mongo availability a prerequisite for local farm records. A lightweight geometry validator rejects malformed rings at the API boundary without adding a GIS runtime dependency; polygon holes and multipolygon relationships still require a future topology/survey review before any legal-area claim.

## 2026-09-20 — Harvest records preserve reported facts without implying a sale

The original Electron agent can record one farmer-reported lot on an existing crop cycle only after a write approval. The API requires an idempotency key and validates date, quantity, unit, and active-cycle state. `final_harvest` is explicit because the first picking may not finish the crop. No revenue, sale, certified grade, or measured yield is inferred. The local `X-Farmer-ID` selector remains a desktop trust boundary, not multi-user authentication.
