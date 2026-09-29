# Initial prototype readiness — 6 September 2026

## Decision

**Yes — ready for a limited, software-assisted initial prototype.**

The usable demo scope is:

```text
Farmer profile/field/crop state
  -> manual or API-posted soil observations
  -> source-aware weather and deterministic irrigation screening
  -> alerts, reminders and reports
  -> Codex CLI / desktop conversation using the same farmer-scoped API
```

**No — not ready to claim a field-deployable SIH D1 system.** Hardware
telemetry ingestion, device authentication/calibration, offline Android
runtime, CNN/deep-learning crop diagnosis, and any physical irrigation control
are intentionally deferred.

## Evidence by limited-prototype capability

| Capability | Status | Evidence |
| --- | --- | --- |
| Farmer-isolated farm state | Ready | Per-`X-Farmer-ID` SQLite store; FastAPI tests cover isolation and writes. |
| React frontend → API | Ready for local demo | API client sends farmer identity; UI lint, tests and production build pass. |
| Soil/irrigation screening | Ready as decision support | Current observations, soil health and deterministic irrigation-advice routes work; no equipment-control route exists. |
| Weather/alerts | Ready when provider/network is available | Explicit provider-unavailable path is tested; results preserve source/freshness. |
| Codex/MCP | Ready for local use | 60+ tools registered, stdio `tools/list` tested, real Codex app-server starts, and a live MCP `get_farm_overview` call completed against FastAPI. |
| Shared reference features | Setup-dependent | MongoDB is required for crops, markets, MSP, schemes, machinery and marketplace reference data. The live audit ran with Mongo unavailable, so these must be seeded/configured before demonstration. |
| Voice/local-language provider | Optional and setup-dependent | Sarvam wrappers return explicit unavailable/inconclusive states until credentials/provider access are configured. |
| Disease/pest image diagnosis | Deferred | Upload workflow is safe, but no validated model artifact is present; results are inconclusive. |
| IoT hardware/device status | Deferred | No device-authenticated ingestion endpoint, firmware source or calibration evidence exists yet. |
| Pump/valve actuation | Explicitly prohibited | The MCP server can only explain or record an irrigation event. |

## Demo preparation gate

Before presenting the limited prototype, the operator must:

1. Start MongoDB and FastAPI; use `/health` to confirm both `farm_state` and
   `reference_database` are available.
2. Seed/reference-ingest the crops, market/MSP/scheme and marketplace data that
   the selected demo actually uses; do not present empty data as a live market.
3. Create one demo farmer and field, then post only clearly labelled manual or
   fixture observations with source and observation time.
4. Install the MCP adapter, set a trusted farmer identity in the launcher, and
   start the Codex desktop or CLI session.
5. Demonstrate a safe path: field → observation → weather/irrigation advice →
   farmer-confirmed reminder/report. Do not demonstrate automatic irrigation,
   diagnosis accuracy, a booking, procurement, export, or guaranteed profit.

## Live verification performed

On this checkpoint a temporary FastAPI server on `127.0.0.1:8765` returned:

```text
/health: status=degraded, farm_state=available, reference_database=unavailable
MCP tools/call get_farm_overview: completed successfully
```

This proves the current farmer-state path works end-to-end without MongoDB. It
does **not** prove a reference-data demo is ready until MongoDB is running and
seeded.

## Recommendation

Use the product now for a **local software prototype / SIH concept demo**.
Call it “farm-state, weather and irrigation decision support with Codex tools,”
not “field-deployable autonomous smart farming.” Promote it to the D1 claim
only after the deferred evidence gates in the PRD and team plan are passed.
