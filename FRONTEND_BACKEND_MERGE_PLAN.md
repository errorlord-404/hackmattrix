# Frontend–Backend Merge Plan

## Goal

Connect the existing React application to the existing FastAPI service without changing the dual-database boundary: shared reference data remains in MongoDB/Beanie, while farmer-owned state remains in one SQLite file per `X-Farmer-ID`.

The merged application must never replace unavailable backend/provider data with an apparently real value. Loading, empty, stale, offline, inconclusive, and provider-unavailable states are part of the contract.

## Current-state audit

| Frontend route / feature | Current frontend behavior | Backend coverage | Merge work |
| --- | --- | --- | --- |
| Global farmer header and settings | Hard-coded farmer and location; language only in `localStorage` | `GET/PUT /v1/profile` including language and notification preferences | Load profile globally; persist settings changes; keep local language as an offline cache |
| Dashboard `/` | Static weather, moisture, irrigation, market, field, soil, and alert values | `/v1/dashboard`, fields/map, observations, soil health, irrigation plan, alerts, weather; reference market summary/trend | Compose live screen data, show per-source failures and freshness, and remove unsupported claims |
| My Fields `/fields` | Static cards; “Add field” does nothing | Field CRUD and GeoJSON validation | Load fields, add a working create-field form, refresh after create, and show empty/error states |
| Field Detail `/fields/:id` | Static timeline, recommendations, irrigation date, alert, and yield | Field detail, timeline, observations, irrigation plan, alerts | Load by route ID; derive timeline/progress from stage events; show only backend recommendations; mark yield unavailable unless a sourced model exists |
| Farm Map `/map` | Illustrative CSS positions | `GET /v1/fields/map` returns boundaries, centroids, stage, moisture, and alert count | Render normalized SVG polygons from returned GeoJSON and retain a list fallback |
| Crop Guide `/crop-guide` | Static wheat stages and advice | Crop-cycle timeline plus shared crop reference CRUD | Select a live field/cycle and display recorded stages; use crop reference values only when Mongo is available; no invented agronomy doses |
| Soil Health `/soil` | Static pH/N/P/carbon/moisture and recommendations | Soil-health read model and latest observations | Add field selector; render latest sourced measurements, provenance, recommendations, and missing-data state |
| Weather `/weather` | Static Indore forecast and alerts | Open-Meteo-backed `/v1/weather` and field weather alerts | Resolve location from selected field/profile; render provider timestamps, current/hourly/daily data; show explicit 503/offline state |
| Irrigation `/irrigation` | Static plan/schedule; reminder button does nothing | Irrigation plan, manual events, reminder creation | Load explainable plan; create persisted reminders; add reminder listing endpoint and UI status |
| Pest & Disease `/pest` | Button reveals a fabricated aphid result without choosing a file | Multipart diagnosis create/get; safe inconclusive response until provider configured | Use a real file input, upload progress/status, poll result, and display inconclusive/provider errors verbatim |
| Market `/market` | Static price, trend, arrivals, comparison, and recommendation | Summary/history/trend and assumption-bearing compare APIs in Mongo | Load live values with crop/location filters, make comparison action real, expose assumptions/freshness, and remove storage advice not supported by data |
| AI Advisor `/ai` | Appends a canned answer | Session/message/stream endpoints with explicit provider-unavailable fallback | Create session for selected field, post messages, render stored backend response/citations, and never synthesize a local answer |
| Voice `/voice` | Timer inserts a canned transcript and answer | Raw audio turn endpoint with provider-unavailable response | Capture actual browser audio where supported, upload it, render transcript/response or safe fallback; typed questions use advisor flow |
| Reports `/reports` | “Generate report” does nothing | Create/get snapshot-backed reports | Add report listing endpoint, create report, display status and saved artifact data |
| Notification bells | Decorative | Alerts list and read/dismiss update | Add alert drawer/list, unread count, read/dismiss actions, and refresh after mutations |

## Contract and infrastructure decisions

1. Add `src/api/client.js` with separate `VITE_FARM_STATE_API_URL` and `VITE_REFERENCE_API_URL`, timeout/abort handling, request IDs, normalized errors, and `X-Farmer-ID` on Farm State requests.
2. Add typed-by-convention domain clients (`farmStateApi.js`, `referenceApi.js`) and keep response normalization there, not inside page markup.
3. Add a global farm-data provider for profile, fields, map summaries, alerts, refresh/mutation methods, and independent loading/error state.
4. Use `VITE_DEMO_FARMER_ID` or `localStorage` for the temporary development identity. The UI must label this as a local development profile, not authentication.
5. Do not auto-seed business values from the old `src/data/dashboard.js`, `src/data/fields.js`, or `src/data/chat.js`. Image and navigation assets may remain static presentation data.
6. Keep FastAPI usable for local Farm State routes when MongoDB is unavailable; reference pages should show a reference-service error rather than taking down personal farm state.

## Implementation sequence

### 1. Shared integration layer

- Add API clients, normalized `ApiError`, request timeout, request IDs, and URL configuration.
- Add reusable loading, empty, error, stale/source, and mutation-status components.
- Add `FarmDataProvider` and mount it above the router.

### 2. Farmer state vertical slice

- Wire profile/settings/header.
- Wire field list, add-field form, field detail, timeline, and GeoJSON map.
- Remove hard-coded field IDs and derive all links/selectors from API records.

### 3. Observations and decisions

- Wire soil health and latest observations.
- Wire provider-backed weather and weather alerts.
- Wire irrigation plans and persisted reminders.
- Compose dashboard cards from these same responses so values agree across pages.

### 4. Provider workflows

- Replace diagnosis simulation with actual multipart upload and result display.
- Replace advisor canned replies with session/message calls.
- Replace voice timer with browser recording and `/v1/voice/turns`; keep typed fallback via advisor.

### 5. Reference data and reports

- Wire market summary/history/trend/compare with source and assumptions.
- Add `GET /v1/reports` and `GET /v1/reminders`, then wire report/reminder lists.
- Wire notification bells to alerts and acknowledgment.

### 6. Verification

- Backend: unit/integration tests for new list endpoints, isolation, error contracts, rule outputs, and OpenAPI coverage.
- Frontend: lint/build plus API client tests where available.
- Browser flows: empty profile; create profile; create field; field persists after refresh; low-moisture alert; reminder persists; diagnosis returns inconclusive instead of a fake label; advisor/voice provider failure is explicit; market service failure is isolated; report appears after creation.

## Acceptance criteria

- No page imports hard-coded farmer, field, dashboard, or chat business values.
- Every visible number or recommendation comes from an API response and includes source/freshness where applicable, or is clearly labelled unavailable.
- Creating a field, reminder, alert acknowledgment, advisor message, diagnosis, and report survives page refresh.
- One `X-Farmer-ID` cannot see another farmer's SQLite state.
- MongoDB/reference failure does not prevent local Farm State screens from loading.
- `pytest`, frontend lint/build, and the focused browser flows pass.

