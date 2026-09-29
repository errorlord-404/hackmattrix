# MVP implementation checkpoint — 9 September 2026

This checkpoint records the implementation completed after
`MVP_INITIAL_DEMO_READINESS_PLAN_2026_09_09.md`. It is intentionally separate
from the existing dirty session files so a later agent can resume safely.

## Completed in this slice

- Added `src/lib/location.js` to normalize display locations and select field
  coordinates without treating `Pune, Maharashtra (local demo)` as a state.
- Added `FarmBoundaryMap` using Leaflet/OpenStreetMap, backend GeoJSON,
  computed centroids, fit-to-bounds and safe invalid-geometry handling.
- Added `NearbyServicesMap` for selected-farm/provider markers, radius circle,
  marker-card selection and map/list workflows.
- Added marketplace and machinery nearby API clients and connected both screens
  to a selected field/profile location, radius and Map/List mode.
- Extended shared Mongo listing/rental contracts with optional coordinates,
  service radius, geocode provenance, verification time and sparse geospatial
  index declarations.
- Added bounded `/marketplace/nearby` and `/machinery-rentals/nearby` endpoints
  with distance sorting and explicit no-coordinate fallback behavior.
- Normalized machinery/marketplace administrative filters.
- Fixed `/gov-schemes/by-state/{state}` for the installed Beanie version and
  made nationwide demo records match normalized state searches.
- Added Pune coordinates to the local demo machinery and marketplace records.
- Added `npm run demo:desktop`, backed by `scripts/start-demo.ps1`, which
  starts/validates Mongo, idempotently seeds demo data, starts FastAPI on 8001,
  starts Vite with matching URLs and launches Electron with Codex context.
- Added Codex MCP tools `find_nearby_machinery` and
  `find_nearby_marketplace_listings`. They accept only a farmer-owned
  `field_id`, read coordinates from backend state and never accept raw model
  coordinates.
- Added farmer-scoped `/v1/diagnostics`, safe `X-Request-ID` response
  correlation, and a Settings readiness panel with SQLite/reference counts and
  degraded-component disclosure.
- Added a confirmation-gated, demo-identity-only Settings action that can load
  or repair the local farmer fixture without touching shared reference data.
- Added append-only local audit events, a bounded farmer JSON export, and a
  Settings download action for recovery evidence.
- Added bounded browser-side last-known reference caching. Stale catalog data
  is marked with age and a verify-before-acting warning when the backend is down.
- Added `get_component_health` to the Codex harness with the same diagnostics
  contract used by Settings.
- Fixed launcher ordering so FastAPI starts before farmer seeding; custom
  `-BackendUrl` values now seed the selected service rather than a hard-coded
  port. Added `-ResetDemo` and `npm run demo:check` for deterministic local
  fixture reset/readiness checks.
- Expanded the local fixture to two non-overlapping fields, three machinery
  records, and twelve marketplace records (two per demonstrated listing type),
  all explicitly labelled as non-live.

## Evidence

- `npm run lint`: passed with no warnings.
- `npm run build`: passed; existing Vite bundle-size warning remains.
- `npm run test:ui -- --run`: 11 files, 18 tests passed.
- `npm run test:desktop`: 6 tests passed.
- `python -m pytest backend/tests -q`: 51 passed after the geo, diagnostics, audit/export and demo-loader contract tests; only existing dependency
  deprecation warning.
- `python -m pytest agent/tests -q`: 12 passed; only existing settings/deprecation warnings.
- PowerShell AST parse of `scripts/start-demo.ps1`: passed.
- Isolated launcher UAT on backend `8015` and renderer `5175`: backend health and renderer routes returned
  HTTP 200, Electron launched, and Ctrl+C cleaned the owned backend/renderer process trees and ports.
- Fresh custom-port launcher UAT with `-ResetDemo` on backend `8022`:
  `npm run demo:check` reported two fields, three machinery records, twelve
  marketplace records, three schemes, and one open demo task; the owned process
  tree and ports were cleaned on exit.
- The launcher now attaches to an existing compatible `/health` service and
  refuses to overwrite an occupied incompatible backend port.
- `npm run demo:contracts`: 53 literal frontend adapter path shapes matched
  the FastAPI OpenAPI route shapes.
- Renderer smoke through the app shell: Leaflet farm map loaded; marketplace Map/List mode showed the
  seeded provider and distance; schemes loaded three Maharashtra reference cards.
- Fresh backend smoke on port 8013 with seeded Mongo:
  - `/health`: `status=ok`, `farm_state=available`, `reference_database=available`.
  - `/gov-schemes/by-state/Maharashtra`: 3 records.
  - `/machinery-rentals/nearby?lat=18.5204&lon=73.8567&radius_km=25`: 1 demo
    rental at `0.0 km`.
  - `/marketplace/nearby?lat=18.5204&lon=73.8567&radius_km=25`: 1 demo
    listing at `0.0 km`.

## Known limitations

- The repository is intentionally dirty. Existing changes in `FieldTools.jsx`,
  `Marketplace.jsx`, `MachineryRentals.jsx`, backend modules and documentation
  predate this checkpoint. Do not reset, clean or overwrite them.
- The current nearby implementation calculates Haversine distance over a
  bounded Mongo result set. The declared 2dsphere indexes are preparation for
  a native `$near` query after ingestion volume justifies it.
- Existing seeded provider records are local-demo references, not live stock,
  prices, availability or verified providers. `-ResetDemo` deletes only the
  selected farmer's SQLite file and records carrying the explicit demo marker.
- Native Electron visual screenshot capture is not available through the current
  browser automation surface; the launcher lifecycle and the same renderer routes
  were validated in an isolated Electron run.
- Physical actuation, production authentication, offline mobile sync beyond
  bounded reference caching, and field-released crop-health inference remain
  out of scope for this MVP slice.

## Next task

Run a fresh `npm run demo:desktop` UAT and verify the four screenshot workflows
in Electron. Keep the same structured location and provenance contracts; do not
reintroduce display-string parsing in a new client.
