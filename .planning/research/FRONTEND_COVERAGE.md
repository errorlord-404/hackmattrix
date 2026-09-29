# Frontend Coverage Audit

**Project:** KisanSathi
**Track:** Frontend
**Audited:** 2026-08-19
**Scope:** `src/routes`, `src/pages`, `src/api`, contexts/features, layout/navigation, and frontend-backend merge notes.
**Confidence:** HIGH for current source behavior; MEDIUM for runtime/provider availability because this audit did not start the backend or external providers.

## Executive Summary

The frontend has a complete navigable shell with 17 registered routes and no route currently using `PlaceholderPage`. The application is now structured around two API clients: farmer-owned state under `/v1` with `X-Farmer-ID`, and shared reference data under the non-scoped catalog routes. `FarmDataProvider` loads profile, fields, map summaries, and open alerts globally; the AI context owns advisor sessions, text, voice, and diagnosis actions. The current code builds and lints successfully (`npm run lint`, `npm run build`).

Most core farmer-state screens are live enough to form vertical slices: profile/settings, field creation, field list, field detail, map, soil health, weather, irrigation/reminders, alerts, and reports all call matching backend contracts and render loading/empty/error or source states. The field creation flow deliberately creates an approximate point-buffer GeoJSON boundary, so it is an operational MVP boundary rather than a surveyed parcel boundary.

The remaining gaps are primarily product completeness and degraded-state fidelity. Government schemes can list and search reference records but do not expose the backend eligibility endpoint. Crop Guide only renders recorded timeline events and does not use the available crop catalog/guidance APIs. Dashboard `Promise.allSettled` only surfaces market failure; dashboard/soil/irrigation sub-request failures silently become blank cards. Irrigation has no loading state. These are important because the merge plan claims per-source failure and freshness handling as part of the contract.

Provider-assisted features are wired to real endpoints but are not fully capable with the repository's current configuration: diagnosis returns an explicit inconclusive state, advisor returns an explicit provider-unavailable response, and voice accepts audio but returns provider-unavailable without a transcript. Finance is intentionally browser-local (`localStorage`) and only its mandi comparison crosses the backend boundary; the unused IndexedDB module contains seeded demo data but is not connected to the finance page.

## Integration Topology

```text
App
├─ LanguageProvider
├─ FarmDataProvider
│  └─ profile, fields, map fields, open alerts, profile/field/alert mutations
├─ AIConversationProvider
│  └─ advisor session, text messages, MediaRecorder voice, image diagnosis
└─ Router / AppShell
   └─ route pages call farmStateApi or referenceApi
```

Evidence:

- Provider mounting: `src/App.jsx:3-14`.
- Route registry: `src/routes/index.jsx:21-45`.
- Farm-state client and farmer header: `src/api/client.js:3-28`, `src/api/farmStateApi.js:3-20`.
- Reference client: `src/api/referenceApi.js:3-11`.
- Global farm load and mutations: `src/context/FarmDataContext.jsx:7-25`.
- AI session and action ownership: `src/context/AIConversationContext.jsx:16-120`.

The temporary identity is a browser local-storage value or `VITE_DEMO_FARMER_ID`, falling back to `demo` (`src/api/client.js:13-15`). This is a development tenant boundary, not authentication. The merge notes explicitly preserve that decision (`FRONTEND_BACKEND_MERGE_PLAN.md:31-36`; `backend/Decisions.md:108-113`).

## Route Coverage Matrix

Status meanings: **Live** means the displayed business value is API-derived; **Partial** means the main read path works but a meaningful capability is missing or degraded; **Local** means the feature is intentionally client-side; **Provider-gated** means transport is implemented but useful provider output is unavailable in the current repository.

| Route / displayed feature | What it currently does | Backend/API calls | Status and remaining work | Evidence |
|---|---|---|---|---|
| `/` Dashboard | Shows profile greeting, weather, soil moisture/test metrics, irrigation status, market price, primary field, open alerts, forecast, and links to detail pages. Mobile shows a reduced weather card. | Global context: profile, fields, map fields, open alerts. First field: `getDashboard`, `getSoilHealth`, `getIrrigationPlan`, and `marketSummary` when a crop exists. | **Partial/live.** Values are no longer seeded from legacy dashboard data. However, only market rejection reaches `error`; fulfilled/rejected dashboard, soil, and irrigation results are otherwise silently omitted. The mobile layout also exposes less of the live summary. | `src/pages/Dashboard.jsx:14-23`; `src/context/FarmDataContext.jsx:9-24`; `src/data/dashboard.js` has no active import. |
| `/fields` My Fields | Lists live fields, status, crop, area, moisture, and approximate crop images. Add-field dialog accepts name/area/crop and location from search, GPS, map click, or dragged pin; creates an approximate boundary. | Context load; `POST /v1/fields` through `createField`, followed by refresh. Location search calls Nominatim directly. | **Live/partial.** Main CRUD slice works. Field images are static presentation assets. There is no edit/archive flow, no field-level mutation UI beyond creation, and the first boundary is explicitly approximate. | `src/pages/MyFields.jsx:10-27`, `30-37`; `src/components/fields/LocationPicker.jsx:25-134`; `src/api/farmStateApi.js:7-10`. |
| `/fields/:fieldId` Field Detail | Loads field identity, crop stage timeline/progress, current stage, irrigation recommendation/window, moisture provenance, and open field alerts. Yield is explicitly unavailable. | `getField`, `getTimeline`, `getLatestObservations`, `getIrrigationPlan`; alerts come from global `FarmDataProvider`. | **Live/partial.** Four-request detail slice is real and has loading/error/not-found states. It does not refresh or acknowledge alerts, does not load historical alert state, and has no sourced yield model. | `src/pages/FieldDetail.jsx:9-20`; `src/api/farmStateApi.js:8-14`. |
| `/map` Farm Map | Renders returned GeoJSON boundaries as normalized SVG polygons, allows field selection, shows stage/moisture/alert summary, and links to detail. List view is a fallback. | Global `listMapFields` plus `listFields` fallback. | **Live/partial.** Data is backend-derived, but the visual is a custom normalized SVG rather than a geographic map; it has no basemap, zoom, coordinate labels, or boundary editing. | `src/pages/FieldTools.jsx:11-35`; `src/context/FarmDataContext.jsx:11-15`. |
| `/crop-guide` Crop Guide | Displays the selected field's first crop cycle, current stage, and recorded stage events/dates. | `getTimeline(fieldId)` only. | **Partial.** It is a timeline viewer, not a crop guidance feature. It does not call `referenceApi.listCrops`, does not show crop-specific recommendations, and only renders `cycles[0]`; multiple cycles are not selectable. | `src/pages/FieldTools.jsx:44-48`; available but unused `src/api/referenceApi.js:5`. |
| `/soil` Soil Health | Field selector, latest pH/organic carbon/N/P values, moisture, recommendation cards, status, and source/freshness. | `getSoilHealth(fieldId)`. | **Live/partial.** Read-only view is backed by the farm-state read model. There is no UI to record a soil test or sensor observation even though backend routes exist; no historical test chart. | `src/pages/CorePages.jsx:13-20`; backend route evidence `backend/app/routers/farm_state.py:443-520`. |
| `/weather` Weather | Selects a field, resolves field centroid or profile coordinates, shows current conditions, humidity/wind/rain, alerts, and five-day forecast. | `getWeather(lat, lon)` and `getWeatherAlerts(fieldId)`. | **Live/partial.** Provider-backed with explicit missing-location/error states and source stamps. It has no hourly view or refresh control, and the user cannot choose which coordinate source is preferred beyond field selection. | `src/pages/CorePages.jsx:22-28`; `src/api/farmStateApi.js:11-12`. |
| `/irrigation` Irrigation | Selects field, displays rule-based plan, target moisture, explainable recommendation, can create reminder, and lists saved reminders. | `getIrrigationPlan`, `listReminders`, `POST /v1/reminders`. | **Live/partial.** The write and persisted list are wired. Initial loading is not shown, and failures during the initial `Promise.all` are only rendered after rejection; there is no irrigation-event recording or reminder edit/delete. | `src/pages/CorePages.jsx:30-35`; `src/api/farmStateApi.js:13-15`. |
| `/pest` Pest & Disease | Requires a real JPEG/PNG/WebP file, optionally associates a field, uploads it, and shows provider status/label/error/source. | Multipart `createDiagnosis(file, fieldId)`; backend stores request/image and returns diagnosis. | **Provider-gated but safe.** No fabricated aphid result remains. Current backend behavior is explicitly `inconclusive` when no vision provider is configured; frontend does not poll `getDiagnosis`, although current backend returns the response immediately. | `src/pages/FieldTools.jsx:38-42`; `src/api/farmStateApi.js:16-17`; `backend/app/routers/assistants.py:91-123`. |
| `/market` Market Prices | Crop selector from current fields, latest price, seven-day trend, mandi table with arrivals/freshness, and net-realisation comparison. | `marketSummary`, `marketTrend`, `compareMandis`; `marketHistory` exists but is unused. | **Live/partial.** Reference data and assumptions are exposed. There is no historical chart despite a history API, no MSP display, and no crop selector when no current crop is recorded. | `src/pages/CorePages.jsx:37-44`; `src/api/referenceApi.js:5-7`; `backend/Flow.md:77-81`. |
| `/schemes` Government Schemes | Loads state-specific or all reference schemes, searches name/benefits/eligibility text, shows benefits, criteria, documents, deadline, and official source link. | `listSchemesByState(state)` or `listSchemes()`. | **Partial/live.** Listing is real and state-aware. It does not call the available `check-eligibility` backend contract, collect farmer criteria, or provide an eligibility result. | `src/pages/GovtSchemes.jsx:12-64`, `66-120`; backend route `backend/app/routers/gov_scheme.py:55-63`; `FRONTEND_BACKEND_MERGE_PLAN.md:23`. |
| `/finance` Farm Finance | Adds/deletes/filter local income/expense entries, computes balance, runs a local profit scenario, and optionally compares backend mandi returns. | Local `financeStore` uses `localStorage`; `compareMandis` uses `referenceApi.compareMandis`. | **Local/partial by design.** No financial ledger API is called. The page correctly labels private local data, but `src/db/localDatabase.js` is not used by this page and contains seeded demo data that can mislead future integration work. No backend persistence, export, or finance audit trail exists. | `src/pages/FarmFinance.jsx:20-80`; `src/features/financeStore.js:1-27`; unused IndexedDB engine and seed data `src/db/localDatabase.js:1-7`, `71-150`. |
| `/machinery` Machinery Rentals | Loads rental catalog by inferred district/state, filters by category and free-text query, shows rates/location/availability/source, and exposes telephone contact. | `listMachineryRentals({ district, state, category })`. | **Live/partial.** Catalog list is real. Contact is a direct `tel:` link; there is no booking, reservation, availability confirmation, provider profile, or distance sorting. This matches the merge note's “no booking” boundary. | `src/pages/MachineryRentals.jsx:13-40`; `src/api/referenceApi.js:10`; `FRONTEND_BACKEND_MERGE_PLAN.md:23`. |
| `/ai` AI Advisor | Creates a field/language session, sends suggested or typed questions, and renders stored assistant messages, provider, and citations. | `POST /v1/advisor/sessions`; `POST /v1/advisor/sessions/{id}/messages`. | **Provider-gated but transport-live.** Backend currently stores the conversation and returns a safe provider-unavailable message. Session stream/history is not consumed, and the context exposes no confirmation workflow (`pendingAction: null`). | `src/pages/AIAssistant.jsx:7-10`; `src/context/AIConversationContext.jsx:33-59`, `120`; `backend/app/routers/assistants.py:134-172`. |
| `/voice` Voice Assistant | Uses browser `MediaRecorder`, sends an audio blob, renders transcript/response if returned, and provides typed questions through the advisor flow. | `POST /v1/voice/turns`; typed fallback uses advisor message endpoint. | **Provider-gated.** Actual audio transport exists, but current backend returns `provider_unavailable` and no transcript or spoken response. Browser support and microphone permission failures are handled. | `src/pages/VoiceAssistant.jsx:9-15`; `src/context/AIConversationContext.jsx:61-105`; `backend/app/routers/assistants.py:175-185`. |
| `/reports` Reports | Lists snapshot-backed reports, generates a `farm_summary`, and displays saved artifact/input JSON. | `listReports`, `POST /v1/reports`. | **Live/partial.** Create/list survives refresh through the backend. It has no report detail route, download/share/export action, or user-friendly artifact rendering. | `src/pages/CorePages.jsx:46-49`; `src/api/farmStateApi.js:20`; backend `backend/app/routers/farm_state.py:694-736`. |
| `/settings` Settings | Edits farmer name/phone/location/coordinates/notification preference, changes language, and saves profile. | `PUT /v1/profile`; language is also saved in local storage by i18n hook. | **Live/partial.** Profile persistence is wired. Language UI has English/Hindi/Marathi, but several page labels remain hard-coded English and backend profile language is not rehydrated into i18n on startup. | `src/pages/Settings.jsx:6-15`, `17-85`; `src/hooks/useLanguage.jsx:10-15`; `src/i18n/index.js:8`. |

## Global Layout and Cross-Cutting Behavior

- Desktop sidebar registers all navigation entries except Voice; mobile bottom navigation promotes Voice as the center action. Mobile drawer includes the full navigation and closes on link selection (`src/data/navigation.js:3-27`, `src/components/layout/DesktopSidebar.jsx:29-52`, `src/components/layout/MobileBottomNav.jsx:12-40`, `src/components/layout/MobileDrawer.jsx:59-77`).
- Header profile name/location/initials are live from `FarmDataProvider`; notification count and acknowledgement are live open-alert operations (`src/components/layout/Header.jsx:6-60`, `src/components/layout/AlertMenu.jsx:5-10`).
- Shared API behavior includes timeout/abort normalization, request IDs, JSON/FormData handling, and farmer header attachment (`src/api/client.js:17-45`).
- Loading, empty, error, and source display primitives exist in `src/components/feedback/ApiState.jsx`; adoption is uneven, especially dashboard subcards and irrigation initial load.
- Legacy business fixtures are not actively imported: a repository search found no active imports of `src/data/dashboard.js`, `src/data/fields.js`, or `src/data/chat.js`. Static image assets and navigation data remain presentation-only.
- `src/pages/PlaceholderPage.jsx` remains dead code from the earlier shell; no current route points to it.

## Key Coverage Gaps

### 1. Reference capabilities exposed by backend but absent from UI

The backend has crop, seed, fertilizer, MSP, and government-scheme recommendation/eligibility contracts. Current frontend routes consume only scheme listing, market summary/trend/compare, and machinery listing. Crop Guide does not call the crop catalog, schemes do not call eligibility, and no route exposes seed/fertilizer/MSP detail. Evidence: `src/api/referenceApi.js:5-11`, `src/pages/FieldTools.jsx:44-48`, `src/pages/GovtSchemes.jsx:39-54`, `CODEX_AI_HARNESS_MERGE_PLAN.md:186-190`.

### 2. Degraded state is not consistently per-source

`FarmDataProvider` uses `Promise.allSettled`, but only profile and fields failures update the shared error; map and alert failures are ignored (`src/context/FarmDataContext.jsx:9-16`). Dashboard repeats this pattern and only calls `setError` for market rejection (`src/pages/Dashboard.jsx:17-20`). This can leave a screen with blank values and no explanation, contrary to the merge contract's requirement to distinguish unavailable, stale, and provider failures (`FRONTEND_BACKEND_MERGE_PLAN.md:5-7`, `77-84`).

### 3. Provider workflows are transport-complete, output-incomplete

Diagnosis, advisor, and voice are real calls, not simulations, but the checked-in backend intentionally has no approved provider configured. The UI must retain the explicit `inconclusive`/`provider_unavailable` states and should not be considered feature-complete until provider configuration and end-to-end tests exist. Backend behavior is documented in `backend/Decisions.md:43-48` and implemented in `backend/app/routers/assistants.py:117-123`, `145-158`, `175-185`.

### 4. Local persistence boundaries are easy to confuse

The finance page uses `localStorage` per farmer key (`src/features/financeStore.js:3-25`), while `src/db/localDatabase.js` describes IndexedDB finance/soil/weather/AI stores and seeds sample transactions (`src/db/localDatabase.js:1-7`, `71-150`). Because the latter is not imported by the current page, it is not the runtime source of finance data. Any future finance slice needs an explicit decision about whether to remove, connect, or deprecate that module before adding backend synchronization.

### 5. Source/freshness coverage is mixed

Weather, market rows, soil observations, diagnosis, machinery, and irrigation generally render source/timestamp metadata. Scheme provenance is a generic UI label rather than record-level freshness (`src/pages/GovtSchemes.jsx:109-111`), market trend uses a hard-coded “Mongo reference data” stamp (`src/pages/CorePages.jsx:43`), and field/crop timeline events do not show source metadata. The roadmap should preserve domain timestamps from API responses where available.

## Proposed Vertical Slices

### Slice 1 — Farmer identity, fields, map, and field detail

**User outcome:** A farmer can save a local profile, create a field at a chosen location, reload it, see it on the farm map, and open a field detail timeline.

**Already present:** Profile/settings, field creation, location picker, list, map summary, detail route, timeline, and approximate GeoJSON creation.

**Close before calling complete:** Add edit/archive only if required by product scope; make map semantics explicit as approximate SVG; add field refresh/ownership error handling; decide whether cycle creation belongs in this slice because the current UI can only read cycles.

**Evidence:** `src/pages/Settings.jsx:15`, `src/pages/MyFields.jsx:21-27`, `src/pages/FieldTools.jsx:33-35`, `src/pages/FieldDetail.jsx:14-20`.

### Slice 2 — Field observations to operational decisions

**User outcome:** A farmer selects a field and sees sourced soil, weather, and irrigation information, then saves an irrigation reminder that appears after reload.

**Already present:** Soil and weather reads, weather alerts, rule-based irrigation plan, reminder create/list, dashboard composition.

**Close before calling complete:** Add per-card/per-request errors, explicit loading in irrigation, optional observation/test entry, dashboard refresh, and consistent freshness/source labels. Add browser coverage for missing coordinates and provider weather failure.

**Evidence:** `src/pages/CorePages.jsx:13-35`, `src/pages/Dashboard.jsx:17-23`, `backend/Flow.md:42-51`.

### Slice 3 — Reference data that supports decisions

**User outcome:** A farmer can inspect dated mandi prices and assumptions, find schemes for their state, check eligibility, and browse nearby machinery rentals.

**Already present:** Market summary/trend/compare, scheme list/search/details, machinery filters/catalog/contact.

**Close before calling complete:** Add scheme eligibility form/result; decide whether to expose market history/MSP; add record-level freshness; preserve “contact only/no booking” until a booking backend exists; add crop catalog/guidance if Crop Guide is intended to be more than a timeline viewer.

**Evidence:** `src/pages/CorePages.jsx:37-44`, `src/pages/GovtSchemes.jsx:39-112`, `src/pages/MachineryRentals.jsx:25-40`, `backend/app/routers/gov_scheme.py:55-63`.

### Slice 4 — Safe provider-assisted workflows

**User outcome:** A farmer can submit a crop image, ask a text question, or record voice and receive either a sourced result or an unmistakable unavailable/inconclusive state.

**Already present:** Real image upload, advisor session/message flow, MediaRecorder audio, typed fallback, provider-safe backend responses, citations rendering.

**Close before calling complete:** Configure and test approved providers; poll diagnosis if asynchronous providers are introduced; consume session stream/history; define content/size/privacy behavior for audio/images; add explicit retry states and confirmation rules for any future write/action. Do not replace current safe fallbacks with demo content.

**Evidence:** `src/context/AIConversationContext.jsx:47-118`, `src/components/features/ai/ConversationView.jsx:8-16`, `backend/app/routers/assistants.py:91-185`, `CODEX_AI_HARNESS_MERGE_PLAN.md:191-215`.

### Slice 5 — Persisted outputs, notifications, and intentionally local finance

**User outcome:** A farmer can generate/review a report, read/acknowledge alerts, and use the private local finance ledger without confusing it with backend farm state.

**Already present:** Report create/list, alert drawer/count/acknowledge, local ledger CRUD, local profit simulator, backend mandi comparison.

**Close before calling complete:** Add report export/detail if needed; provide independent alert loading/error; reconcile or retire unused IndexedDB implementation; document local-storage limits and data portability; design a separate privacy/authentication contract before syncing finance to backend or AI/MCP.

**Evidence:** `src/pages/CorePages.jsx:46-49`, `src/components/layout/AlertMenu.jsx:5-10`, `src/pages/FarmFinance.jsx:53-78`, `CODEX_AI_HARNESS_MERGE_PLAN.md:62-69`, `193-195`.

## Recommended Order and Exit Criteria

1. **Slice 1 first** because all field-aware routes depend on profile/field identity and coordinates.
2. **Slice 2 second** because dashboard, AI context selection, and most operational decisions consume the field/read-model contracts established by Slice 1.
3. **Slice 3 third** because reference data is independently deployable and must remain isolated from farmer SQLite failures.
4. **Slice 4 fourth** because provider credentials, attachment transport, and safety behavior are external gates; build on already stable field context and explicit error primitives.
5. **Slice 5 last** because report/alert polish is cross-cutting and finance requires a deliberate privacy boundary rather than accidental synchronization.

Minimum acceptance checks for the next implementation pass:

- Create profile and field, reload, and verify the same farmer header/field/map/detail data is shown.
- Break one dashboard sub-request and verify the affected card says unavailable without hiding healthy cards.
- Use a profile with no coordinates and verify weather and field creation explain the missing location.
- Create an irrigation reminder and report, reload, and verify both persisted records appear.
- Submit an image, text question, and voice turn with providers unconfigured; verify no fabricated label, transcript, or recommendation appears.
- List schemes for a state and exercise eligibility once the frontend contract is added.
- Confirm finance entries stay local and are not sent through `farmStateApi`.

## Merge-Note Reconciliation

`FRONTEND_BACKEND_MERGE_PLAN.md:11-27` describes the intended parity work and `backend/ChangeLog.md:68-87` records it as integrated. The current source supports that claim for the main farmer-state, weather, market, machinery, diagnosis, advisor, voice, report, and notification paths. It does not yet constitute full feature parity for scheme eligibility, crop-reference guidance, market history/MSP, observation entry, report export, or provider-backed outputs. The distinction should be carried into roadmap status so “endpoint wired” is not treated as “user capability complete.”

The Codex harness plan independently identifies the same boundaries: crop guidance, diagnosis, machinery, and advisor tool coverage remain future work; finance should start as a stateless/local boundary; voice is gated on transport proof (`CODEX_AI_HARNESS_MERGE_PLAN.md:178-195`). Frontend roadmap work should preserve those boundaries and keep the frontend a backend client rather than introducing direct database or MCP dependencies.

## Verification Evidence

- `npm run lint`: passed.
- `npm run build`: passed; Vite emitted only a bundle-size warning for the main JavaScript chunk.
- No application source was modified during this audit; the only output is this research file.
