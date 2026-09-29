# Local MongoDB shared-reference setup

The backend uses MongoDB only for **shared reference data** (crop catalogue,
schemes, market/MSP reference rows, seed/fertilizer reference rows and public
directory records). Farmer-owned fields, sensor readings, diagnosis history,
ledger and other personal data remain in the farmer-scoped SQLite store.

## Start the local database

From `backend`:

```powershell
docker compose -f docker-compose.universal-data.yml up -d mongodb
docker compose -f docker-compose.universal-data.yml ps
```

The compose service exposes MongoDB only on `127.0.0.1:27017` and persists it
in the named Docker volume `mongodb_data`. It is intentionally not exposed to
the LAN.

If Docker reports that `dockerDesktopLinuxEngine` is unavailable, start Docker
Desktop and wait until its engine reads **Running**, then rerun the commands.

## Populate an implementation/demo catalogue

```powershell
python scripts/seed_local_reference_data.py
python scripts/seed_demo_farmer_state.py
```

The script is idempotent. It inserts/updates records marked
`local_demo_seed_not_live`. Numeric mandi/MSP rows are illustrative UI data,
not a live feed or official value. Scheme records link to official portals but
do not determine eligibility. Replace these records through a source-attributed
ingestion pipeline before a field deployment.

`seed_demo_farmer_state.py` separately populates the local SQLite store of the
`demo` farmer with clearly labelled field, soil, sensor, task, reminder and
ledger fixtures. It does not change any other farmer store and must never be
used with a real farmer identity.

## Start or restart the backend

The backend connects to MongoDB during startup. After MongoDB is ready, restart
the backend or the combined demo launcher so `/health` reports
`reference_database: "available"`:

```powershell
npm run demo:tflite
```

## Verify without exposing secrets

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
Invoke-RestMethod http://127.0.0.1:8001/gov-schemes
```

Do not commit `.env`, MongoDB dumps, Docker volumes, or real farmer data.
