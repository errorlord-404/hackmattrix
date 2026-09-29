# Initial-demo failure drills

Run these checks before a presentation. They are deliberately scoped to the
local demo identity and do not claim production availability.

## Backend unavailable

```powershell
npm run demo:check -- -BackendUrl http://127.0.0.1:6553 -FarmerId demo
```

Expected result: non-zero exit with `Demo backend check failed`; the renderer
must show a retryable service error rather than an empty catalog.

## Mongo/reference unavailable

Start FastAPI with an invalid `MONGODB_URL` and a free port, then run
`npm run demo:check` against that port. Expected result: farm-state diagnostics
remain available, `reference_database` is degraded, and SQLite-backed screens
remain usable. Never present cached/demo references as live.

## Codex unavailable

Launch the Electron shell with `CODEX_BINARY` unset or unavailable. Expected
result: Settings reports Codex unavailable while manual field, soil, task and
ledger screens remain usable.

## Map tiles unavailable

Block OpenStreetMap tile requests in the browser/network layer. Expected result:
the farm and nearby-service maps show the tile warning, while List View remains
available with the same backend records.

## Reset and repeatability

```powershell
npm run demo:desktop -- -ResetDemo
npm run demo:check
```

Expected fixture: two non-overlapping fields, three machinery records, twelve
marketplace records, three schemes, and farmer-local tasks/soil/sensor data.
