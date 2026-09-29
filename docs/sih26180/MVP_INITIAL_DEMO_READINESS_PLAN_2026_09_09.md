# KisanSathi MVP and Initial Demo Readiness Plan

**Date:** 9 September 2026

**Status:** Implementation plan with verified MVP readiness slice. The current
checkpoint records what is complete and what remains intentionally out of scope.

**Target:** A dependable SIH demonstrator that starts locally in Electron, uses identical FastAPI contracts from React and Codex, and clearly distinguishes local demo, cached, unavailable and live/provider-backed data.

## 1. MVP outcome

The MVP is ready when a judge can launch one command, select or create a farm on a real map, see a complete demo farmer state, discover nearby source-attributed services, ask the Codex-backed assistant about that same state, and complete farmer-confirmed digital actions without unexplained empty or error screens.

The vertical proof is:

> farmer identity → selected field and coordinates → SQLite farm state + Mongo reference data → React or Codex tool → source-aware guidance → farmer-confirmed task/record

The demo must not claim production authentication, autonomous physical control, purchase/booking/payment, field-approved vision accuracy, guaranteed scheme eligibility, guaranteed market prices/yield/profit, or complete directory coverage.

## 2. Verified repository state

Implemented foundations:

- React 19/Vite frontend, Electron shell and FastAPI backend.
- Per-farmer SQLite for private farm state; MongoDB for shared crops, schemes, markets and directories.
- Real React Leaflet/OpenStreetMap picker in `src/components/fields/LocationPicker.jsx`.
- Field GeoJSON/centroids, crop cycles, soil/sensors, irrigation guidance, tasks, reminders, alerts, reports and ledger.
- Mongo-backed schemes, machinery, mandi/MSP, crops and approved-source marketplace contracts.
- Idempotent local demo seeds, Python KisanSathi MCP, Codex plugin connection and Sarvam settings.
- Review-only TFLite crop-health demo and device-authenticated observation ingestion, both without physical actuation.

### Screenshot diagnosis

| Screen | Verified cause | Required fix |
|---|---|---|
| Government schemes | The renderer defaults to backend port 8000, while the known demo stack uses 8001 unless Vite receives the correct environment. The generic fetch wrapper collapses all network failures into one message. | One canonical launcher/runtime config; component health; distinguish API down, Mongo down, empty, stale and filtered-to-zero. |
| Machinery rentals | The UI splits a display string. Demo profile is `Pune, Maharashtra (local demo)` but Mongo seed is `Pune` / `Maharashtra`; exact equality filters out the valid row. | Structured location, normalization, selected-field coordinates and nearby fallback. |
| Marketplace | Same fragile parsing/exact match. Ingestion is intentionally empty unless approved sources or demo seeds are loaded. Current listing contract has no usable geospatial search. | Seed/preflight assurance, provider coordinates, bounded nearby API and connected map/list view. |
| Farm Map | Field creation uses a real map, but `GeoMap` in `src/pages/FieldTools.jsx` manually reprojects GeoJSON onto a decorative SVG. Every label uses fixed `x=130,y=120`. | Reuse Leaflet, fit real GeoJSON, calculate centroids, validate geometry and preserve list fallback. |

## 3. Product and architecture decisions

### One structured location contract

Do not derive operational filters from `profile.location`; it is display text. Add a shared contract containing `display_name`, `village`, `district`, `state`, `postal_code`, `latitude`, `longitude`, `source`, `precision` and `observed_at`. Fields also retain `boundary_geojson` and centroid.

Farmer coordinates remain in farmer-scoped SQLite. Shared provider coordinates remain in Mongo. A selected field overrides profile fallback for weather and nearby searches. The model never chooses farmer identity.

### One reusable map system

Build these React Leaflet components:

- `FarmBoundaryMap`: polygons, centroids, fit bounds and selected field.
- `NearbyServicesMap`: selected field boundary/marker, provider markers and radius.
- `LocationPicker`: preserve current pin/search/GPS workflow; later proxy/cache geocoding through FastAPI.
- `MapFallbackList`: remains usable without map tiles or geolocation.

Marketplace and machinery must open around the selected field. One field selector updates the map, list ordering, distance and agent context.

### One domain authority

React and Codex call the same FastAPI routes. Do not put farming logic in Electron, React, prompts or Codex Rust. MCP wraps bounded task APIs and preserves source, freshness, assumptions, warnings and confirmation semantics.

### Field deployable means graceful degradation

The local Electron app keeps fields, tasks, observations, ledger and cached geometry usable without internet. New map tiles or shared data may be unavailable; the UI shows last successful retrieval and a list/cached fallback. No language-model response may directly actuate equipment.

## 4. Target runtime

```text
Electron supervisor
  ├─ safe runtime configuration + diagnostics
  ├─ React renderer
  │    ├─ farmer/field context
  │    ├─ farm and nearby-services maps
  │    ├─ lifecycle screens
  │    └─ native-language voice/text assistant
  ├─ Codex app-server → KisanSathi Python MCP
  └─ FastAPI :8001 (domain authority)
       ├─ farmer-scoped SQLite
       ├─ shared MongoDB
       ├─ approved ingestion/geocoding/provider adapters
       ├─ review-only crop-health inference
       └─ device observation ingestion (no actuation)
```

## 5. Ordered implementation plan

Each work packet is an atomic commit. Preserve the dirty worktree and update `backend/ChangeLog.md`, `backend/Decisions.md` and `backend/Flow.md` whenever their rules require it.

### Wave 0 — Protect and baseline

1. Record branch, HEAD, status, diff stat and active ports.
2. Create a recoverable, non-destructive checkpoint for tracked and untracked work.
3. Run backend, agent, UI, lint, build and desktop test baselines.
4. Inventory every frontend adapter path against OpenAPI.

Done when the starting state is recoverable and baseline failures are separated from new work. Never use reset/clean/checkout-overwrite.

### Wave 1 — Canonical one-command launcher and health model (P0)

Likely files: `package.json`, `desktop/main.cjs`, `desktop/preload.cjs`, `desktop/codex-harness.cjs`, `src/api/client.js`, `src/pages/Settings.jsx`, `backend/app/main.py`, `backend/app/routers/farm_state.py`, a new launcher script and tests.

1. Define one runtime source for backend URL, reference URL, farmer ID and Codex endpoint. Electron exposes only safe public values; secrets remain process-only.
2. Add `npm run demo:check` and `npm run demo:desktop`: verify/start Mongo, seed idempotently, start FastAPI on one fixed port, await health, then start renderer and Electron/Codex.
3. Detect occupied ports/stale services. Attach to a compatible healthy instance or stop only launcher-owned child processes.
4. Return component health for API, SQLite, Mongo, seed/catalog counts, Codex and optional providers.
5. Add in-app diagnostics with retry and a demo-only “Load demo data”.
6. Preserve HTTP status, backend error code, request ID and retryability in UI errors.

Acceptance:

- Fresh start and restart work from one documented command.
- Wrong URL is a configuration mismatch, not “no records”.
- Mongo failure leaves SQLite screens usable.
- Repeated seed/start does not duplicate records.

### Wave 2 — Structured location and geospatial APIs (P0)

Likely files: farmer schemas/store/router, marketplace and machinery models/schemas/routers, seed/migration scripts, `FarmDataContext.jsx` and `LocationPicker.jsx`.

1. Add structured village/district/state/display fields with backward-compatible SQLite migration.
2. Normalize administrative values at write/query boundaries; strip demo annotations from operational values, not from the farmer-visible label.
3. Add provider GeoJSON point or latitude/longitude, service radius, geocode provenance, verification status and last-seen time.
4. Add Mongo `2dsphere` indexes and bounded endpoints:
   - `GET /marketplace/nearby?lat=&lon=&radius_km=&listing_type=&limit=`
   - `GET /machinery-rentals/nearby?lat=&lon=&radius_km=&category=&limit=`
5. Return distance and fallback mode. District-only records remain explicitly “distance unavailable”.
6. Add a deliberate repair command for demo data; never rewrite real user locations silently.

Acceptance: the demo annotation cannot become a state filter; selected-field coordinates take precedence; results are bounded and distance-sorted; cross-farmer location isolation passes.

### Wave 3 — Real farm map (P0)

Likely files: `src/pages/FieldTools.jsx`, new `src/components/maps/FarmBoundaryMap.jsx`, `MapFallbackList.jsx`, styles and tests.

1. Replace the decorative SVG with `MapContainer`, `TileLayer`, `GeoJSON` and centroids.
2. Fit all valid field bounds and recenter on selection without unwanted zoom resets.
3. Style polygons by selected/alert/status state and place labels/popups at their actual centroids.
4. Validate Polygon/MultiPolygon records; isolate invalid geometry instead of inventing a polygon.
5. Preserve a complete list and cached geometry when tiles fail.

Acceptance: Pune fields render at real coordinates, labels do not overlap by construction, multiple polygons remain selectable, and bad geometry cannot break the page.

### Wave 4 — Map-connected marketplace and machinery (P0)

Likely files: `Marketplace.jsx`, `MachineryRentals.jsx`, new `NearbyServicesMap.jsx`, shared field/location selector, reference API client and tests.

1. Show selected field/profile fallback and “searching near …”.
2. Add Map/List toggle. Draw the selected field plus provider markers; marker and result-card selection remain synchronized.
3. Add radius, type/category, query and district-only filters; keep reproducible filter state in the URL.
4. Cluster co-located markers and fit farm + results. Do not send the private farm pin to listing sources.
5. Display distance, source, freshness, verification, price unit and missing availability.
6. Render distinct states: API down, Mongo down, directory unconfigured, ingestion never run, zero filter results, stale cache and valid results.
7. Keep call/source actions user-driven. No booking, guarantee or transaction.

Acceptance: current demo records appear for the selected demo field; map/card selection works; reset recovers from zero results; records without provenance are never shown as verified.

### Wave 5 — Schemes and reference truthfulness (P1)

1. Query by normalized structured state.
2. Add source URL, fetched/verified time and demo/live classification.
3. Wire eligibility as explicit-input screening only.
4. Say “potentially relevant”, link official sources and never imply approval/submission.
5. Show last-known cached schemes with age during temporary provider/Mongo failure.

Acceptance: Maharashtra demo schemes load; backend unavailable differs from no result; every visible record has provenance.

### Wave 6 — Codex farmer harness parity (P1)

Likely files: `agent/kisansathi_mcp/*`, `codex/plugins/kisansathi/*`, desktop harness and integration tests.

1. Add/verify bounded tools for field context, farm map, nearby machinery, marketplace, schemes and component health.
2. Launcher owns farmer/field context. Model arguments never accept farmer ID, credentials, SQL, paths or policy controls.
3. Preserve source, freshness, distance assumptions, warnings and degraded status.
4. Treat listing/provider content as untrusted data.
5. Prove “find tractors near Upper Field” returns the same semantics as the UI and explains zero results.
6. Persistent writes remain approval-gated and farmer-confirmed.

Acceptance: real stdio test proves plugin load, tool list, representative read, approved task write, cancel and surfaced backend failure. Codex failure does not break non-AI screens.

### Wave 7 — Field resilience and safety shell (P1/P2)

1. Cache bounded last-known reference responses with source/freshness.
2. Show device last-seen, CRC/validation and power status on field detail.
3. Add append-only audit records for confirmed writes, device packets and refreshes.
4. OS-protect secrets; never store API keys in renderer localStorage or tool results.
5. Add SQLite backup/export/recovery.
6. Design any later controller with manual override, flow feedback, limits and emergency stop; do not enable it in this MVP.
7. Keep Wokwi evidence separate from real calibration and field tests.

### Wave 8 — Demo hardening and release gate (P0 before presentation)

1. Deterministic fixture: one farmer, two non-overlapping fields, crop stage, sensor history, tasks/alerts, three schemes, three machinery providers, two records per demonstrated marketplace type, three mandi prices and MSP.
2. Label every synthetic record `local demo — not live`.
3. Add a confirmed reset limited to the explicit demo identity/databases.
4. Run Electron UAT at 1366×768 and 1920×1080.
5. Drill Mongo down, backend down, tile down, Codex down and optional provider down.
6. Record screenshots, commands, commit hashes and limitations.

Release gate: lint/build/UI/desktop/backend/agent tests pass; fresh start and restart pass; the four screenshot defects have reproducible closure evidence; crop-health remains review-only without real independent release evidence.

## 6. Test matrix

Contract tests:

- every frontend path exists in OpenAPI with success and validation coverage;
- location normalization covers annotations, case, whitespace, missing district, ambiguous text and invalid coordinates;
- nearby queries cover radius, ordering, missing coordinates and limits;
- error envelopes expose request ID/stable code/retryability;
- SQLite cross-farmer isolation and shared Mongo-read boundaries.

UI/E2E tests:

- Polygon/MultiPolygon, invalid geometry, no tiles and keyboard/list fallback;
- marketplace/machinery marker-card sync, selected field, radius and reset;
- schemes unreachable vs Mongo unavailable vs no match vs cached stale;
- launch → field map → soil/device → irrigation record;
- selected field → nearby provider map;
- schemes → official source/disclaimer;
- voice/text → Codex → same selected-field result;
- provider failure leaves local state usable.

## 7. Six-person ownership

| Owner | Ownership for this plan |
|---|---|
| Varuna | Power, sensor calibration evidence, enclosure/BOM |
| Anwaar | ESP32/RS485 firmware, Wokwi export, packet/CRC/device status |
| Prachi | Shared Leaflet map components, responsive map/list and field selector |
| Harshwardhan | Reference-screen states, diagnostics UX, accessibility/demo UAT |
| Aman | Health/location/nearby APIs, Mongo geospatial schema/index, ingestion and seeds |
| Pranav | Canonical launcher, Electron/Codex/MCP parity, integration/release evidence |

Pranav currently has the greatest integration load. Refactor ownership so Aman owns backend data contracts and Prachi owns the reusable map system; Pranav integrates stable interfaces instead of implementing both layers.

## 8. Priority and definition of done

Initial-demo must-have: Waves 0–4, scheme state correction, existing Codex handshake plus nearby read parity, and Wave 8. Cached references, complete translations and richer device panels are should-have. Survey-grade boundaries, production auth/sync, field-evaluated ML, calibrated root-zone water balance and bounded non-agent actuation are later pilot work.

The MVP is done when the farmer, field, coordinates, source records, screen and AI tool all refer to the same entities and failure states. A screen silently emptied by parsing a display string is a release blocker. A map without a list/offline fallback is incomplete. A Codex answer that cannot reproduce the UI’s source semantics is unacceptable.

Begin implementation with Wave 0 and Wave 1. Do not start new model training or physical-control work during this slice.

## 9. Current implementation status

The initial-demo must-have slice is implemented through the launcher, map,
nearby discovery, schemes, Codex parity, diagnostics, bounded reference cache,
audit/export, deterministic fixtures, reset, and contract/test gates. The
remaining items are pilot/production work rather than blockers for the local
SIH demonstrator: live provider ingestion operations, production identity and
authentication, full offline sync, calibrated hardware actuation, and
field-evaluated crop-health release evidence. Native Electron screenshot
capture was unavailable in the current desktop automation environment and is
called out in the checkpoint rather than being represented as completed visual
evidence.
