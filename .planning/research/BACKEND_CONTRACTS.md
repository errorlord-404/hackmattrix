# Backend Contract Research

**Project:** KisanSathi SIH MVP
**Track:** Backend REST contracts and MCP harness
**Researched:** 2026-08-19
**Confidence:** HIGH for the current repository surface; MEDIUM for intended product scope inferred from plans and frontend usage

## Scope and source of truth

This audit traced the current FastAPI application, Pydantic schemas, local SQLite store, Mongo reference-data routers, frontend API clients and pages, MCP tool registrations, tests, OpenAPI generation, and planning documents. The generated `app.openapi()` contains 58 application paths, including `/health`, at the current checkout.

The backend has two explicit data planes:

- Farmer-owned state is stored in one SQLite database per validated `X-Farmer-ID` through `backend/app/farm_state/dependencies.py` and `backend/app/farm_state/store.py`.
- Shared reference data is stored in MongoDB through Beanie models registered by `backend/app/core/database.py` and routers included by `backend/app/main.py`.

`X-Farmer-ID` is a temporary identity boundary, not authentication. The default is `demo`; `safe_farmer_key()` blocks path traversal and unsafe characters, but any caller can choose another valid ID. The MCP client attaches this header from launcher configuration in `agent/src/kisansathi_agent/backend_client.py`.

## Feature-to-route-to-tool matrix

Status meanings: **covered** means the current frontend call has a matching route; **partial** means the route exists but has a known behavioral or harness gap; **missing tool** means REST exists but no MCP wrapper is registered; **local by design** means no backend contract is expected under the current architecture.

| Frontend / product feature | Current REST contract | Current MCP tool | Status and contract finding |
|---|---|---|---|
| Dashboard / farm overview | `GET /v1/dashboard` in `backend/app/routers/farm_state.py` | `get_farm_overview` in `agent/src/kisansathi_agent/tools.py` | Partial. Dashboard returns fields, cached weather, open alerts, and `data_warnings`, but `market_summary` is always `[]` and does not include profile context. The frontend composes profile/field/soil/irrigation/market separately. |
| Profile and settings | `GET /v1/profile`; `PUT /v1/profile` | `get_profile`; `update_profile` | Covered for current UI. PUT is idempotency-aware. Profile creation is an upsert, so a first save can create the profile. Production auth remains unresolved. |
| Field list and map | `GET /v1/fields`; `GET /v1/fields/map` | `list_fields` | Covered for reads. `list_fields` supports `include_inactive`; the frontend client currently does not expose that option. Map response derives latest moisture, active crop stage, and open-alert count. |
| Field detail | `GET /v1/fields/{field_id}` | `get_field` | Covered. Field IDs are URL-quoted in the MCP tool, but frontend `src/api/farmStateApi.js` interpolates IDs directly. IDs are UUIDs today, but the client should still encode path parameters. |
| Create field / choose location | `POST /v1/fields` with `FieldCreate` and Polygon/MultiPolygon GeoJSON validation | `create_field` | Covered. Backend computes centroid and persists it. MCP requires confirmed name, area, and geometry. |
| Edit/archive field | `PATCH /v1/fields/{field_id}`; soft-delete `DELETE /v1/fields/{field_id}` | No `update_field`; no delete tool | Partial. The REST route is idempotency-aware, but neither the frontend API client nor MCP exposes PATCH. Delete is deliberately not exposed to the farmer-facing MCP harness. |
| Crop guide and lifecycle | `POST /v1/fields/{field_id}/crop-cycles`; `GET /v1/fields/{field_id}/timeline`; `PATCH /v1/crop-cycles/{cycle_id}/stage` | `get_field_timeline`; `start_crop_cycle`; `update_crop_stage` | Covered for the current crop-guide UI and agent writes. The frontend only reads timeline; it has no create/stage-update API methods. There is no variety field in `CropCycleCreate`, despite the MCP plan wording about confirming variety. |
| Soil health | `GET /v1/fields/{field_id}/soil-health` | `get_soil_health` | Covered. Response contains latest test, latest observations, screening status, recommendations, and provenance. Recommendations are deterministic screening rules, not agronomic prescriptions. |
| Record soil test | `POST /v1/fields/{field_id}/soil-tests` | `record_soil_test` | REST and MCP covered; frontend currently has no write UI. Payload requires `observed_at` and `source`; nutrient units are not represented, so callers must preserve the source's unit convention externally. |
| Sensor observations | `POST /v1/sensor-readings`; `GET /v1/fields/{field_id}/observations/latest` | `get_latest_field_observations` only | Partial. Read path is covered. POST is not idempotent, has no device authentication, and is not exposed by MCP; this is appropriate for the conversational MVP but requires a device-authenticated ingestion contract before production. |
| Weather forecast | `GET /v1/weather?lat={lat}&lon={lon}` | `get_weather_for_field` resolves field coordinates, then calls weather | Covered with explicit provider degradation. Weather snapshots are cached in SQLite. Provider failures return structured 503 detail. |
| Weather alerts | `GET /v1/weather/alerts?field_id={field_id}` | `get_weather_alerts_for_field` | Covered. The current route needs `field_id`, not coordinates. Older plan wording saying to resolve coordinates and call the alerts route is stale; only the weather forecast call uses coordinates. |
| Irrigation advice | `GET /v1/fields/{field_id}/irrigation-plan` | `get_irrigation_advice` | Partial and unsafe as a read contract. The handler calculates advice but also inserts a new `irrigation_plans` row on every GET. It never controls equipment, but repeated UI/MCP reads create durable records. |
| Irrigation history | `POST /v1/irrigation-events` | `record_irrigation_event` | Covered and idempotency-aware. It records a farmer-confirmed event only; no pump or valve operation exists. |
| Reminders | `GET /v1/reminders`; `POST /v1/reminders` | `list_reminders`; `create_reminder` | Covered and idempotency-aware for create. There is no update, cancel, or completion route; the current UI only creates and lists. |
| Alerts / notifications | `GET /v1/alerts?status={status}`; `PATCH /v1/alerts/{alert_id}` | `list_alerts`; `update_alert_status` | Covered. Alert generation is currently tied to low moisture observations and weather alert derivation. Status changes are idempotency-aware. |
| Pest and disease photo upload | `POST /v1/diagnoses` multipart; `GET /v1/diagnoses/{diagnosis_id}` | No diagnosis tool | Partial. The frontend route works as an upload/status workflow, but with the default `DIAGNOSIS_PROVIDER=unconfigured` it always returns `inconclusive`; no label, confidence, severity, or treatment is generated. Uploads are persisted and repeated uploads are not deduplicated. |
| Text AI advisor | `POST /v1/advisor/sessions`; `POST /v1/advisor/sessions/{session_id}/messages`; `GET /v1/advisor/sessions/{session_id}/stream` | No advisor tools; MCP plan intentionally avoids backend advisor | Partial. Routes persist user and assistant messages but the assistant response is a provider-unavailable stub. `AdvisorMessageCreate.idempotency_key` is accepted by the schema but ignored by the router. The frontend sends messages but does not consume the stream route. |
| Voice assistant | `POST /v1/voice/turns` raw audio | No voice tool | Partial. The route only checks that the body is non-empty and returns `provider_unavailable` for both configured and unconfigured providers. It has no content-type, byte-limit, farmer-store, or idempotency boundary. |
| Market prices | `GET /market-prices/summary`; `GET /market-prices/history`; `GET /market-prices/trend`; `GET /market-prices/compare/{crop_name}`; plus CRUD and crop listing | `get_market_summary`; `get_market_trend`; `compare_mandis` | Covered for frontend and MCP read use. Comparison returns explicit transport, loading, unloading, market-fee, storage, and expected-spoilage assumptions. All list routes are unpaginated. Mongo availability is a runtime dependency. |
| Farm finance ledger | No backend route | No MCP tool | Local by design. `src/features/financeStore.js` / `src/pages/FarmFinance.jsx` keep private transactions in browser storage and explicitly label them as not backend data. Do not add a cloud finance route unless the privacy boundary changes explicitly. |
| Government schemes | `GET /gov-schemes`; `GET /gov-schemes/by-state/{state}`; `POST /gov-schemes/check-eligibility` | `find_government_schemes` only calls state listing | Partial. State and nationwide scheme listing is covered. Eligibility REST exists, but the MCP tool does not expose it or accept criteria. Current eligibility logic is state-only; free-form criteria are intentionally not evaluated. |
| Machinery rentals | `GET /machinery-rentals` with category/district/state filters; central CRUD | No MCP tool | Covered for the current frontend page only. This is central Mongo reference data, not farmer-owned state. No agent wrapper or idempotency boundary exists for central writes, which is correct for the current farmer-safe allow-list. |
| Reports | `POST /v1/reports`; `GET /v1/reports`; `GET /v1/reports/{report_id}` | `create_report`; `list_reports`; `get_report` | Covered. Reports are synchronous SQLite snapshots, not generated files or asynchronous jobs despite the `report_jobs` table. Report type/date filters are stored but the snapshot builder currently returns the same farm-state snapshot shape. |
| Crop, fertilizer, seed, disease reference catalogs | `/crops`, `/fertilizer`, `/fertilizer/recommend`, `/seeds`, `/seeds/recommend`, `/diseases` CRUD/reference routes | No MCP tools | REST exists for administration/reference use, but the MCP plan explicitly excludes exposing central administration and deletion. The frontend currently uses crop listing only indirectly; no frontend client exists for fertilizer, seed, or disease catalog recommendation. |

## REST contract inventory

### Farmer-scoped SQLite routes

Defined primarily in `backend/app/routers/farm_state.py`, `backend/app/routers/weather.py`, and `backend/app/routers/assistants.py`; these depend on `get_farm_store()` and therefore use the `X-Farmer-ID`-selected database:

```text
GET/PUT  /v1/profile
GET/POST /v1/fields
GET      /v1/fields/map
GET/PATCH/DELETE /v1/fields/{field_id}
POST     /v1/fields/{field_id}/crop-cycles
GET      /v1/fields/{field_id}/timeline
PATCH    /v1/crop-cycles/{cycle_id}/stage
POST     /v1/fields/{field_id}/soil-tests
GET      /v1/fields/{field_id}/soil-health
POST     /v1/sensor-readings
GET      /v1/fields/{field_id}/observations/latest
GET      /v1/fields/{field_id}/irrigation-plan
POST     /v1/irrigation-events
GET/POST  /v1/reminders
GET      /v1/alerts
PATCH    /v1/alerts/{alert_id}
GET      /v1/dashboard
GET/POST  /v1/reports
GET      /v1/reports/{report_id}
GET      /v1/weather
GET      /v1/weather/alerts
POST/GET  /v1/diagnoses and /v1/diagnoses/{diagnosis_id}
POST     /v1/advisor/sessions
POST/GET  /v1/advisor/sessions/{session_id}/messages and /stream
POST     /v1/voice/turns
```

The frontend uses these client modules as its actual call boundary:

- `src/api/client.js` adds base URLs, request IDs, timeouts, and `X-Farmer-ID` for farmer-state calls.
- `src/api/farmStateApi.js` covers the profile, field, weather, irrigation, reminders, alerts, dashboard, diagnosis, advisor, voice, and report calls listed above.
- `src/api/referenceApi.js` covers crop listing, market views, schemes, and machinery rentals.

### Shared Mongo reference routes

Routers registered in `backend/app/main.py` expose full CRUD for `farmers`, `crops`, `diseases`, `fertilizer`, `market-prices`, `gov-schemes`, `msp`, `seeds`, and `machinery-rentals`. `backend/app/core/database.py` registers their Beanie documents. These routes are not farmer-scoped by header and have no authentication or write idempotency. They should remain an administrative/internal surface, not a model-controlled farmer tool surface.

### Ingestion routes

`backend/app/routers/ingestion.py` exposes:

- `POST /internal/universal-data/sync`, protected by `X-Ingestion-Token`, which delegates to `backend/app/scraping/service.py`.
- `GET /internal/universal-data/runs`, which lists ingestion telemetry.

`backend/n8n/universal-data-sync.json`, `backend/docs/UNIVERSAL_DATA_INGESTION.md`, and `backend/tests/test_universal_data_sources.py` confirm that n8n is intended to schedule the protected backend sync, not write MongoDB directly.

## Missing or incomplete contracts

### P0: fix before calling the MCP harness contract complete

1. **Make irrigation advice genuinely read-only.** Split calculation from persistence in `backend/app/routers/farm_state.py`. `GET /v1/fields/{field_id}/irrigation-plan` should calculate or return a stable saved plan without inserting a new row. If saving a plan is needed, add an explicit idempotent `POST` route. This is called out in `MCP_AGENT_IMPLEMENTATION_PLAN.md` Phase 0 and is observable today by repeatedly loading the field detail page.
2. **Define provider-backed assistant behavior or keep the UI explicitly stubbed.** Diagnosis, advisor, and voice routes exist but are not functional providers under the defaults in `backend/app/core/config.py`. The frontend must not present them as completed intelligence until the provider adapters, timeout/error schema, provenance, and tests exist. The current explicit degraded responses are safe but incomplete.
3. **Close the identity and tracing boundary.** Replace or wrap arbitrary `X-Farmer-ID` before multi-user deployment. `agent/src/kisansathi_agent/backend_client.py` sends `X-Request-ID`, but the backend has no request-ID middleware/response-header implementation in `backend/app`; tool responses therefore rely on the client-generated ID rather than a server-confirmed trace ID.
4. **Add idempotency to any newly enabled mutation.** Existing farm-state writes mostly use `backend/app/farm_state/store.py` helpers, but sensor ingestion, diagnosis upload, advisor session/message creation, voice turns, field soft-delete, and all central Mongo writes do not. The MCP plan correctly excludes most of these until their mutation semantics are defined.

### P1: required for frontend/MCP parity

1. **Add the missing `update_field` MCP wrapper and frontend API method** for existing `PATCH /v1/fields/{field_id}`. The route already validates and deduplicates; only the clients are incomplete.
2. **Expose scheme eligibility deliberately.** Either add a separate MCP `check_scheme_eligibility` tool mapping to `POST /gov-schemes/check-eligibility`, or document that the harness only supports state filtering. Do not imply that free-form `eligibility_criteria` are evaluated; `backend/Decisions.md` says they are not.
3. **Add bounded pagination/filter contracts** to large reference and farmer-state list routes. Current MCP result bounding in `agent/src/kisansathi_agent/result.py` limits model context after the response is received; it does not prevent large backend queries or large network responses.
4. **Add a non-stream advisor history route or consume the existing SSE route in the frontend.** `GET /v1/advisor/sessions/{session_id}/stream` exists, but `src/api/farmStateApi.js` has no stream method and `src/context/AIConversationContext.jsx` uses the synchronous message response only.
5. **Define a real sensor ingestion contract.** Keep it outside conversational MCP tools, but require device authentication, source/device ownership, unit rules, timestamps, deduplication, and replay behavior before accepting production sensor data. Current `POST /v1/sensor-readings` accepts a field ID plus free-form source and creates a new reading on every request.
6. **Complete missing agent capabilities if the harness must cover the whole UI:** diagnosis status, advisor session/message workflow, voice turn, machinery lookup, and scheme eligibility are all REST-accessible but absent from `agent/src/kisansathi_agent/server.py`.

### P2: clarify rather than expand blindly

1. **Keep finance local unless product requirements change.** The frontend intentionally stores private transactions in `src/features/financeStore.js`; adding backend finance routes would change the privacy/offline architecture described in `backend/AGENTS.md` and `backend/Decisions.md`.
2. **Clarify report semantics.** `ReportCreate` accepts `crop_health`, `water`, and `market`, but `_report_snapshot()` in `backend/app/routers/farm_state.py` currently builds one common fields/open-alerts/latest-moisture snapshot for every type. Either specialize artifacts or rename the contract to snapshot report.
3. **Clarify crop-cycle fields.** The frontend/MCP planning text mentions variety, while `CropCycleCreate` has only crop name, dates, and stage. Add variety only if it is a required product concept, rather than silently accepting an unsupported field.
4. **Decide whether dashboard composition belongs in backend or client.** The current dashboard route returns `market_summary=[]`; the frontend correctly composes a separate market request. A future aggregate route should define freshness and partial-failure semantics before replacing that composition.

## Safety, idempotency, and provenance concerns

| Operation / boundary | Current behavior | Risk | Required contract rule |
|---|---|---|---|
| Farmer identity | `X-Farmer-ID` defaults to `demo`; validated by `safe_farmer_key()` | Header is spoofable and is not authentication | Keep it only as development/launcher identity; require authenticated subject-to-store mapping for deployment |
| Farmer database isolation | `FarmStateStore` uses one SQLite file per farmer key | Isolation is filesystem/process-local; concurrent multi-worker deployment needs explicit storage strategy | Document single-instance/SQLite limits or move to an authenticated durable tenant store before scale-out |
| Farm-state writes | `get_idempotent_response()` hashes payload and stores response per key | No expiry/cleanup policy; deterministic MCP keys make the same payload one logical operation forever | Add retention/cleanup and, where needed, an explicit operation ID rather than payload-only identity |
| Profile, field create/update, crop cycle/stage, soil test, irrigation event, reminder, alert patch, report | Idempotency-aware via `Idempotency-Key` | Good retry behavior, but response status is not consistently replayed by the helper API | Preserve the first response body/status; test conflict and replay for each route |
| Sensor reading create | Always inserts a UUID row; no idempotency header | Transport retry duplicates observations and may repeatedly trigger downstream logic | Add device/source event ID or idempotency key in a device-authenticated ingestion API |
| Irrigation plan GET | Inserts a new `irrigation_plans` row on every request | Read tools and page refreshes mutate state and create unbounded history | Make GET pure; use explicit idempotent save endpoint if persistence is a product feature |
| Diagnosis upload | Stores a file and request on every upload; provider can be unavailable | Duplicate uploads consume disk; no replay contract; image path is local to backend instance | Require request id/checksum deduplication, quotas/retention, and provider job status semantics |
| Advisor message | Schema includes `idempotency_key`, router ignores it and inserts user+assistant rows | Client retry duplicates conversation turns | Enforce the schema key or remove it; return a replayable assistant message ID |
| Voice turn | Only checks non-empty body; no `get_farm_store()` dependency | No farmer ownership, content-type/size guard, replay handling, or provider timeout contract | Add authenticated scope, media validation/limit, idempotency, and explicit provider result metadata |
| Weather GET | Reads cache, may fetch provider, and inserts a weather snapshot | Technically not side-effect-free; concurrent misses can insert duplicate snapshots | Treat cache writes as infrastructure side effects, dedupe by location/time, and do not describe it as pure if strict read annotations matter |
| Reference Mongo CRUD | Full create/update/delete routes, no auth or idempotency | Central catalogs can be changed or deleted by any caller reaching the service | Restrict to ingestion/admin credentials; keep them out of farmer MCP registration |
| Ingestion sync | `X-Ingestion-Token` protects the sync route; source IDs support bulk upsert | Token rotation and replay/overlap behavior need operational policy | Keep backend-owned validation/upsert; document token rotation, run dedupe, and partial-failure semantics |
| Request tracing | MCP sends `X-Request-ID`; backend does not visibly echo or persist it | Tool result request IDs are not server-confirmed and cross-service diagnosis is weak | Add middleware to accept/generate, echo, and log request IDs without leaking secrets |
| Error contract | Farm-state conflicts use `{detail: {code, message}}`; many routers use string detail; provider routes vary | MCP client must normalize several shapes; frontend gets inconsistent messages | Standardize `{detail: {code, message, retryable?, request_id?}}` or publish a stable error schema |
| CORS | `allow_origins=["*"]` with credentials enabled in `backend/app/main.py` | Unsafe for a credentialed production browser boundary | Restrict origins and decide whether cookies/auth are used before release |

## MCP harness inventory

The registered tools are in `agent/src/kisansathi_agent/server.py`; HTTP orchestration is in `agent/src/kisansathi_agent/tools.py` and transport/error normalization is in `agent/src/kisansathi_agent/backend_client.py`.

### Registered farmer-safe reads

```text
get_farm_overview              -> GET /v1/dashboard
get_profile                    -> GET /v1/profile
list_fields                    -> GET /v1/fields
get_field                     -> GET /v1/fields/{field_id}
get_field_timeline             -> GET /v1/fields/{field_id}/timeline
get_soil_health                -> GET /v1/fields/{field_id}/soil-health
get_latest_field_observations  -> GET /v1/fields/{field_id}/observations/latest
get_weather_for_field          -> GET field, then GET /v1/weather
get_weather_alerts_for_field   -> GET /v1/weather/alerts?field_id=...
get_irrigation_advice          -> GET /v1/fields/{field_id}/irrigation-plan
list_alerts                    -> GET /v1/alerts
list_reminders                 -> GET /v1/reminders
list_reports                   -> GET /v1/reports
get_report                     -> GET /v1/reports/{report_id}
get_market_summary             -> GET /market-prices/summary
get_market_trend               -> GET /market-prices/trend
compare_mandis                 -> GET /market-prices/compare/{crop_name}
get_msp                        -> GET /msp/by-crop/{crop_name}
find_government_schemes        -> GET /gov-schemes/by-state/{state}
```

The tool result envelope in `agent/src/kisansathi_agent/result.py` bounds response data and carries status/summary/request ID, which is appropriate for model context. It does not repair backend side effects, missing provenance, or unbounded upstream queries.

### Registered approved writes

```text
update_profile                -> PUT /v1/profile
create_field                  -> POST /v1/fields
start_crop_cycle              -> POST /v1/fields/{field_id}/crop-cycles
update_crop_stage             -> PATCH /v1/crop-cycles/{cycle_id}/stage
record_soil_test              -> POST /v1/fields/{field_id}/soil-tests
update_alert_status            -> PATCH /v1/alerts/{alert_id}
record_irrigation_event        -> POST /v1/irrigation-events
create_reminder                -> POST /v1/reminders
create_report                  -> POST /v1/reports
```

Every current MCP write derives a deterministic key from path and payload in `KisanSathiTools._idempotency_key()` and marks the tool as non-read-only, idempotent, and non-destructive. This is a good baseline, but `update_field` is absent even though its backend route and plan entry exist.

## Verification evidence

- `pytest -q backend/tests`: **11 passed**, one Starlette/httpx deprecation warning.
- `pytest -q agent/tests`: **8 passed**, one pytest-asyncio configuration warning and one pydantic-settings warning.
- `python -m compileall -q backend/app agent/src`: passed with no output.
- `app.openapi()` route inventory: **58 paths** at this checkout.
- Existing tests cover farmer SQLite isolation, low-moisture alert deduplication, explicit weather/diagnosis degradation, two profile idempotency cases, market calculation, ingestion parsers, MCP request headers, MCP write-key determinism, HTTP error mapping, and result bounding. They do not cover all frontend API calls, generated OpenAPI schemas, irrigation GET side effects, advisor message replay, voice validation, pagination, or request-ID echo.

## Exact files consulted

### Backend application

- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/core/database.py`
- `backend/app/farm_state/dependencies.py`
- `backend/app/farm_state/rules.py`
- `backend/app/farm_state/store.py`
- `backend/app/routers/farm_state.py`
- `backend/app/routers/weather.py`
- `backend/app/routers/assistants.py`
- `backend/app/routers/market_price.py`
- `backend/app/routers/gov_scheme.py`
- `backend/app/routers/machinery_rental.py`
- `backend/app/routers/ingestion.py`
- `backend/app/routers/crop.py`, `disease.py`, `farmer.py`, `fertilizer.py`, `msp.py`, `seed.py`
- `backend/app/schemas/farm_state.py`
- `backend/app/schemas/market_price.py`
- `backend/app/schemas/gov_scheme.py`
- `backend/app/schemas/machinery_rental.py`
- `backend/app/schemas/ingestion.py`, `sensors.py`, and the remaining domain schemas
- `backend/app/services/weather.py`, `market.py`, `fertilizer_mutator.py`, `gov_scheme_mutator.py`, `seed_mutator.py`

### MCP harness

- `agent/src/kisansathi_agent/server.py`
- `agent/src/kisansathi_agent/tools.py`
- `agent/src/kisansathi_agent/backend_client.py`
- `agent/src/kisansathi_agent/result.py`
- `agent/src/kisansathi_agent/config.py`
- `agent/tests/test_tools.py`
- `agent/tests/test_backend_client.py`

### Frontend contract consumers

- `src/api/client.js`
- `src/api/farmStateApi.js`
- `src/api/referenceApi.js`
- `src/context/FarmDataContext.jsx`
- `src/context/AIConversationContext.jsx`
- `src/pages/Dashboard.jsx`
- `src/pages/FieldTools.jsx`
- `src/pages/FieldDetail.jsx`
- `src/pages/CorePages.jsx`
- `src/pages/GovtSchemes.jsx`
- `src/pages/MachineryRentals.jsx`
- `src/pages/FarmFinance.jsx`
- `src/pages/Settings.jsx`
- `src/features/financeStore.js`
- `src/routes/index.jsx`

### Planning and project boundary documents

- `backend/AGENTS.md`
- `backend/Decisions.md`
- `backend/Flow.md`
- `backend/docs/PRD.md`
- `backend/docs/UNIVERSAL_DATA_INGESTION.md`
- `FRONTEND_BACKEND_MERGE_PLAN.md`
- `MCP_AGENT_IMPLEMENTATION_PLAN.md`
- `CODEX_AI_HARNESS_MERGE_PLAN.md`
- `.planning/codebase/ARCHITECTURE.md`
- `.planning/codebase/INTEGRATIONS.md`
- `.planning/codebase/TESTING.md`

## Recommended implementation order for roadmap planning

1. Stabilize backend semantics and test contracts: pure irrigation reads, idempotent assistant/session mutations, upload/audio limits, error/request-ID envelopes, and pagination.
2. Close client parity: frontend field patch/crop lifecycle methods, advisor stream consumption, and explicitly degraded provider UI states.
3. Close MCP parity only for approved farmer-safe operations: add `update_field`, decide on scheme eligibility, and add diagnosis/voice/advisor tools only after provider and safety contracts are real.
4. Harden boundaries: authenticated farmer identity, device-authenticated sensor ingestion, restricted central Mongo administration, CORS origins, and SQLite deployment constraints.
5. Preserve local finance privacy and keep ingestion scheduler/backend ownership separate from conversational tools.

