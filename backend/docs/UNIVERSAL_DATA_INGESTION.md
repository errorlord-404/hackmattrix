# Universal data ingestion

The shared MongoDB reference database is populated only from traceable official sources.

## Sources and field boundaries

| Collection | Source | Imported fields | Deliberately not inferred |
|---|---|---|---|
| `market_prices` | AGMARKNET daily mandi feed through data.gov.in | state, district, mandi, commodity, variety, grade, observation date, min/max/modal price | arrival quantity (the feed does not expose it) |
| `msps` | Press Information Bureau MSP releases | crop, variety where published, season, marketing year, MSP per quintal | procurement centres (not in the releases) |
| `crops` | Commodity names and current modal prices derived from the same AGMARKNET fetch | name, mean current modal price, season when matched to an MSP crop | water, soil, rotation, and yield facts |
| `marketplace_listings` | Administrator-approved public directory pages with publisher JSON-LD | title, provider/contact/location, published offer fields, listing/source URLs, fetch time | availability, rating, delivery, booking, price validity, or any record not published by the source |

Every imported document stores a stable `source_record_id`, `source`, `source_url`, and `fetched_at`. Re-running ingestion is an idempotent upsert. Manual CRUD records are preserved because they have no source record ID.

Seeds, fertilizer dosage/pricing, disease treatment, and scheme eligibility are not auto-filled by this job: the researched government pages do not provide stable structured feeds matching the existing schemas. Those collections remain available through CRUD and must be populated only from approved domain-specific sources.

Marketplace discovery is deliberately separate from those recommendation catalogs. Configure approved HTTPS directory sources in `MARKETPLACE_DIRECTORY_SOURCES_JSON`, then run `--sources marketplace`. The `gov_schemes` source refreshes the public MahaDBT Farmer Portal catalogue, and `machinery` refreshes both the public Government of India FARMS KisanRath CHC provider feed and dashboard network counts. Provider rows retain source-published contact/cost fields but never imply a booking or current availability. See [MARKETPLACE_DIRECTORY.md](MARKETPLACE_DIRECTORY.md) for the source policy and configuration shape.

## Run locally

First copy `.env.example` to `.env` and replace both placeholder secrets.

### Windows without Docker

From `backend/`, run:

`powershell -ExecutionPolicy Bypass -File scripts/setup_universal_data.ps1`

The script downloads the official MongoDB Community archive into the ignored `.runtime` directory, installs the pinned n8n release there, validates the Python code/tests, populates MongoDB, starts FastAPI, imports and activates the workflow, and starts n8n. Re-running it is safe: source documents are upserted by stable IDs.

### Docker

1. Start MongoDB and n8n:

   `docker compose --env-file .env -f docker-compose.universal-data.yml up -d`

   On a fresh Docker volume, then import and activate the versioned scheduler
   without relying on a shell inside the n8n container:

   `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap_docker_n8n_workflow.ps1`

   The bootstrap preserves an already-imported workflow by default. Use
   `-ForceImport` only when intentionally replacing it with the checked-in
   `n8n/universal-data-sync.json` definition.

2. Start FastAPI from `backend/`:

   `uvicorn app.main:app --reload`

3. Populate immediately:

   `python -m app.scraping --sources market_prices,msp,crops,gov_schemes,machinery,marketplace`

The imported n8n workflow runs every day at 06:30 Asia/Kolkata. It calls the protected `POST /internal/universal-data/sync` endpoint and retries transient failures three times. Ingestion history is available from `GET /internal/universal-data/runs` with the same `X-Ingestion-Token` header.

The setup pins n8n `1.123.72`, the latest v1 release compatible with the project's installed Node 20 runtime (`>=20.19`). n8n v2 currently requires Node `>=22.22`; upgrade Node before moving this pin to v2.

### Windows native-build prerequisite

Some n8n dependencies, including `isolated-vm`, may need a native build on
Windows. If `npm install` fails with `node-gyp ERR! find VS`, install the
**Desktop development with C++** workload for a supported Visual Studio Build
Tools/Community installation, then rerun the setup script. MongoDB, FastAPI,
and a manually triggered ingestion run can still operate without n8n; only the
scheduled workflow remains unavailable.

The data.gov.in API key is optional. If omitted, the scraper reads the public key rendered on the official resource page for that public dataset and keeps it in memory only. Configure your own data.gov.in key for production stability.
