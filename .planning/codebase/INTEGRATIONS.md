# External Integrations

**Analysis Date:** 2026-08-20

## Evidence Classification

- **Functional code:** an integration has an executable client/route and a configuration path in `src/`, `desktop/`, `backend/app/`, `agent/src/`, or `codex/plugins/kisansathi/`.
- **Provider-gated:** executable adapter code exists but requires configuration unavailable from source, such as Sarvam in `backend/app/services/sarvam.py`.
- **Mock/local catalog:** data is hardcoded or seeded locally, such as `src/services/hostedCatalogService.js` and seed finance rows in `src/db/localDatabase.js`; comments naming Apify or hosted scraping do not make those live integrations.
- **Documentation-only:** mentions in `backend/docs/PRD.md` and root planning/audit Markdown files are not counted as integrations without executable code.

## APIs & External Services

**Agent and model runtime:**
- OpenAI Codex app-server - the Electron host spawns an installed `codex app-server --stdio`, starts/resumes threads, sends text/local-image inputs, receives streaming JSON-RPC events, and relays approvals through `desktop/codex-harness.cjs`.
  - SDK/Client: custom Node JSONL client in `desktop/codex-harness.cjs`; native server implementation is the Rust workspace at `codex/codex-rs/app-server/`.
  - Auth: the `codex` executable must already be signed in or configured for a model provider; the farming app does not store an OpenAI API key in `desktop/`.
  - Status: Functional integration contract and desktop tests exist in `tests/desktop/codex-harness.test.cjs`; runtime availability still depends on an external installed Codex binary because `package.json` does not build `codex/codex-rs/`.
- KisanSathi MCP server - Codex receives farmer-scoped tools over local stdio from `agent/src/kisansathi_agent/server.py`, launched by `codex/plugins/kisansathi/run_server.py` and injected per desktop session by `desktop/codex-harness.cjs`.
  - SDK/Client: Python MCP SDK/FastMCP from `agent/pyproject.toml`; HTTP bridge in `agent/src/kisansathi_agent/backend_client.py`.
  - Auth: trusted launcher environment fixes `KISANSATHI_FARMER_ID`; the model cannot supply the farmer ID because it is omitted from tool schemas in `agent/src/kisansathi_agent/server.py`.
  - Status: Functional local adapter with registered read/write tools and unit tests in `agent/tests/`; this is a Python plugin integration, not a Rust farming handler inside `codex/codex-rs/`.
- Upstream Codex model providers - OpenAI Responses/ChatGPT backend, configurable providers, MCP, plugins, and OTLP support exist in the vendored fork through `codex/codex-rs/model-provider/`, `codex/codex-rs/codex-api/`, `codex/codex-rs/login/`, `codex/codex-rs/codex-mcp/`, `codex/codex-rs/plugin/`, and `codex/codex-rs/otel/`.
  - SDK/Client: Rust `reqwest`, WebSocket/SSE, `rmcp`, and OpenTelemetry dependencies declared in `codex/codex-rs/Cargo.toml`.
  - Auth: upstream Codex authentication/configuration, not KisanSathi backend authentication; `desktop/codex-harness.cjs` delegates to the installed CLI.
  - Status: Vendored upstream capability. KisanSathi only exercises app-server plus its injected MCP server in current application code.

**Weather:**
- Open-Meteo forecast API - current, hourly, and five-day daily forecasts are fetched and normalized in `backend/app/services/weather.py`, cached to farmer SQLite, and exposed by `backend/app/routers/weather.py`.
  - SDK/Client: Python standard-library `urllib.request.urlopen` in `backend/app/services/weather.py`.
  - Auth: None; provider selection/timeouts/cache are configured by `WEATHER_PROVIDER`, `WEATHER_TIMEOUT_SECONDS`, and `WEATHER_CACHE_SECONDS` in `backend/app/core/config.py`.
  - Status: Functional live adapter with an explicitly labelled value-empty fixture mode in `backend/app/services/weather.py`; no generic weather-provider interface beyond the configuration branch exists.

**Voice and translation:**
- Sarvam AI - speech-to-text, text-to-speech, and translation adapters are implemented in `backend/app/services/sarvam.py` and routes are exposed by `backend/app/routers/assistants.py`.
  - SDK/Client: Python standard-library HTTP/multipart implementation in `backend/app/services/sarvam.py`.
  - Auth: `SARVAM_API_KEY`; base URL, timeout, STT/TTS/translation models, speaker, pace, sample rate, and codec are defined in `backend/app/core/config.py`.
  - Status: Provider-gated. Routes return explicit `provider_unavailable`/`inconclusive` states when configuration or network access is absent in `backend/app/routers/assistants.py`.
  - Desktop path: `desktop/main.cjs` proxies audio/translation/synthesis to FastAPI; `src/context/AIConversationContext.jsx` uses the Electron bridge when present and the browser FastAPI client otherwise.

**Maps and geocoding:**
- OpenStreetMap tile service and Nominatim search - interactive map tiles, browser geolocation, map clicks, markers, and text geocoding are implemented in `src/components/fields/LocationPicker.jsx`.
  - SDK/Client: Leaflet/React Leaflet plus browser `fetch` in `src/components/fields/LocationPicker.jsx`.
  - Auth: None in source; requests are made directly from the renderer.
  - Status: Functional prototype integration. There is no server proxy, rate-limit cache, configured identifying user agent, offline tile source, or satellite imagery provider in `src/components/fields/LocationPicker.jsx`.

**Official Indian agricultural data:**
- data.gov.in / AGMARKNET market prices - the current daily mandi resource is fetched, paginated, validated, normalized, and bulk-upserted by `backend/app/scraping/sources.py` and `backend/app/scraping/service.py`.
  - SDK/Client: Python `urllib.request`; persistence uses PyMongo `UpdateOne` in `backend/app/scraping/service.py`.
  - Auth: `DATA_GOV_IN_API_KEY` from `backend/app/core/config.py`; code includes a fragile fallback that scrapes a public resource-page key in `backend/app/scraping/sources.py`.
  - Status: Functional ingestion code with source URLs, observed/fetched timestamps, stable source IDs, rejection counts, and tests in `backend/tests/test_universal_data_sources.py`; live success requires network access and MongoDB.
- Press Information Bureau MSP releases - Kharif/Rabi HTML tables are fetched and parsed into MSP records by `backend/app/scraping/sources.py` and ingested by `backend/app/scraping/service.py`.
  - SDK/Client: Python standard-library HTML parser and `urllib.request` in `backend/app/scraping/sources.py`.
  - Auth: None; source URLs and marketing year are configured by `MSP_KHARIF_URL`, `MSP_RABI_URL`, and `MSP_MARKETING_YEAR` in `backend/app/core/config.py`.
  - Status: Functional parser/ingestion code with fixture-based tests in `backend/tests/test_universal_data_sources.py`; HTML layout changes remain an external fragility.
- n8n scheduler - manual and daily triggers call the authenticated universal-data sync endpoint through `backend/n8n/universal-data-sync.json`; local runtime is defined in `backend/docker-compose.universal-data.yml`.
  - SDK/Client: n8n HTTP Request node calling `POST /internal/universal-data/sync`, implemented by `backend/app/routers/ingestion.py`.
  - Auth: `X-Ingestion-Token` checked with constant-time comparison against `SCRAPER_WEBHOOK_TOKEN` in `backend/app/routers/ingestion.py`.
  - Status: Implemented local orchestration configuration. n8n is not part of the root app process and must be started/imported via `backend/docker-compose.universal-data.yml` or `backend/scripts/setup_universal_data.ps1`.

**Application API boundaries:**
- React renderer to FastAPI - typed-by-convention browser clients in `src/api/farmStateApi.js` and `src/api/referenceApi.js` call the shared request wrapper in `src/api/client.js`.
  - SDK/Client: browser `fetch`, AbortController timeout, JSON/FormData handling, `X-Request-ID`, and optional `X-Farmer-ID` in `src/api/client.js`.
  - Auth: no token/session auth; farmer-scoped requests send a client-controlled `X-Farmer-ID` derived from localStorage or `VITE_DEMO_FARMER_ID` in `src/api/client.js`.
  - Status: Functional local API integration, but the identity boundary is prototype-only.
- MCP server to FastAPI - every farming tool is normalized through `agent/src/kisansathi_agent/backend_client.py` and registered with read/write annotations in `agent/src/kisansathi_agent/server.py`.
  - SDK/Client: `httpx.AsyncClient` with bounded timeouts/response size from `agent/src/kisansathi_agent/config.py`.
  - Auth: trusted `X-Farmer-ID` header injected by `agent/src/kisansathi_agent/backend_client.py`; write requests use idempotency metadata from `agent/src/kisansathi_agent/result.py` and are approval-gated by Codex configuration in `desktop/codex-harness.cjs`.
  - Status: Functional local bridge with mocked HTTP tests in `agent/tests/test_backend_client.py` and `agent/tests/test_tools.py`.

**Media and catalogs:**
- Unsplash images - remote field/catalog image URLs are referenced in `src/data/images.js` and `src/services/hostedCatalogService.js`.
  - SDK/Client: browser image loading; no Unsplash SDK or API request exists in `src/`.
  - Auth: None.
  - Status: Static demo assets, not a data integration.
- Apify - named only in comments in `src/services/hostedCatalogService.js` and planning documents; no Apify dependency, HTTP client, actor ID, webhook, or credential setting exists in `package.json`, `backend/app/`, or `backend/app/core/config.py`.
  - SDK/Client: Not detected.
  - Auth: Not applicable.
  - Status: Not implemented; all exported hosted catalog arrays in `src/services/hostedCatalogService.js` are hardcoded mock data.

## Data Storage

**Databases:**
- MongoDB central reference database - initialized by `AsyncIOMotorClient` and Beanie in `backend/app/core/database.py`.
  - Connection: `MONGODB_URL`, `DATABASE_NAME`, and connection timeout in `backend/app/core/config.py`.
  - Client: Beanie/Motor/PyMongo from `backend/requirements.txt`.
  - Registered documents: farmer, crop, disease, fertilizer, market price, government scheme, MSP, seed, ingestion run, and machinery rental models in `backend/app/models/`.
  - Availability behavior: backend startup catches Mongo failures and reports degraded reference-data status while keeping farmer SQLite endpoints available in `backend/app/main.py`.
- Per-farmer SQLite operational databases - one sanitized farmer-key database file is managed by `FarmStateStore` in `backend/app/farm_state/store.py`.
  - Connection: directory is `FARM_STATE_DB_DIR` from `backend/app/core/config.py`; farmer selection comes from the `X-Farmer-ID` dependency in `backend/app/farm_state/dependencies.py`.
  - Client: Python standard-library `sqlite3` in `backend/app/farm_state/store.py`.
  - Stored domains: profile/preferences, fields/GeoJSON, crop cycles/stages, tasks, soil tests, sensors/observations, irrigation plans/events, reminders, weather, diagnoses/images/disease events, advisor history, recommendations, alerts, reports, and idempotency records in the `SCHEMA` constant in `backend/app/farm_state/store.py`.
- Browser IndexedDB/localStorage - `src/db/localDatabase.js` defines finance, soil, weather-cache, and offline-AI stores with seeded demo rows; `src/features/financeStore.js` separately persists farmer-keyed finance rows in localStorage.
  - Connection: browser-origin local storage only; it is not synchronized with SQLite or MongoDB.
  - Client: native browser APIs in `src/db/localDatabase.js` and `src/features/financeStore.js`.
  - Status: Prototype/local-only and partly duplicated; do not treat it as the same database as `backend/app/farm_state/store.py`.

**File Storage:**
- Local diagnosis uploads - validated JPEG/PNG/WebP bytes are written beneath `FARM_STATE_UPLOAD_DIR/<farmer>/` by `backend/app/routers/assistants.py`; metadata/checksums are stored in SQLite by `backend/app/farm_state/store.py`.
- Temporary crop images - Electron writes renderer-supplied bytes under the OS temp directory before sending a `localImage` item to Codex and removes them in `desktop/main.cjs` and `desktop/codex-harness.cjs`.
- Local renderer assets - `public/` and remote URLs in `src/data/images.js`; no S3, Azure Blob, GCS, Cloudinary, or other object-storage client is present in application manifests.

**Caching:**
- Weather snapshots are cached per farmer/location in the SQLite `weather_snapshots` table and bounded by `WEATHER_CACHE_SECONDS` in `backend/app/routers/weather.py`.
- Browser weather/offline-AI object stores exist in `src/db/localDatabase.js`, but current API clients in `src/api/` do not use them as a transparent offline cache.
- No Redis/Memcached dependency exists in `backend/requirements.txt`, `agent/pyproject.toml`, or `package.json`.

## Authentication & Identity

**Auth Provider:**
- Farmer application authentication: None.
  - Implementation: browser code selects `X-Farmer-ID` from localStorage/defaults in `src/api/client.js`; MCP identity is trusted launcher configuration in `agent/src/kisansathi_agent/config.py`; FastAPI accepts the header through `backend/app/farm_state/dependencies.py`.
  - Constraint: this provides local data partitioning, not verified identity, authorization, or tenant security.
- Codex authentication: delegated to the installed Codex binary spawned by `desktop/codex-harness.cjs` and implemented by upstream crates such as `codex/codex-rs/login/` and `codex/codex-rs/keyring-store/`.
- Ingestion authentication: shared webhook token only, enforced by `backend/app/routers/ingestion.py`; no general API JWT/session middleware is registered in `backend/app/main.py`.
- Browser CORS: wildcard origins/methods/headers with credentials enabled in `backend/app/main.py`; this is development configuration and not a substitute for authentication.

## Monitoring & Observability

**Error Tracking:**
- No Sentry, Datadog, Rollbar, or equivalent application error-tracking SDK is present in `package.json`, `backend/requirements.txt`, or `agent/pyproject.toml`.

**Logs:**
- Electron writes renderer/process diagnostics to stderr/console and relays Codex stderr as diagnostic events in `desktop/main.cjs` and `desktop/codex-harness.cjs`.
- FastAPI/Uvicorn provides framework logs via dependencies in `backend/requirements.txt`; application modules under `backend/app/` do not configure structured logging or a centralized sink.
- The MCP bridge can request `LOG_FORMAT=json` when spawning Codex in `desktop/codex-harness.cjs`, but the KisanSathi Python package itself has no observability exporter in `agent/src/kisansathi_agent/`.
- The vendored Codex fork supports tracing and OTLP through `codex/codex-rs/otel/` and dependencies in `codex/codex-rs/Cargo.toml`; the farming application does not configure an OTLP destination in tracked root/desktop code.
- Ingestion run status, counts, source URLs, and errors are persisted as `IngestionRun` documents through `backend/app/models/ingestion_run.py` and returned by `backend/app/routers/ingestion.py`.

## CI/CD & Deployment

**Hosting:**
- Application hosting is not configured alongside `package.json`, `backend/`, `agent/`, or `desktop/`; no Vercel/Netlify/Railway manifest, backend Dockerfile, Kubernetes manifest, or cloud IaC is present.
- Local MongoDB/n8n infrastructure is available through `backend/docker-compose.universal-data.yml`; that compose file does not run FastAPI, Electron, or Codex.
- Electron packaging/signing is not configured in `package.json`; `desktop:build` only builds Vite output and opens Electron.

**CI Pipeline:**
- No application-specific CI workflow was detected for root `package.json`, `backend/`, or `agent/`.
- The vendored Codex repository contains its own upstream build/test ecosystem under `codex/.github/`, `codex/justfile`, `codex/MODULE.bazel`, and `codex/codex-rs/`; it is not wired as a KisanSathi release pipeline.

## Environment Configuration

**Required env vars:**
- `KISANSATHI_FARMER_ID` - required by the standalone MCP server in `agent/src/kisansathi_agent/config.py`; Electron supplies a `demo` default in `desktop/main.cjs`.
- `KISANSATHI_BACKEND_URL` - optional local backend override used by `desktop/main.cjs`, `desktop/codex-harness.cjs`, and `agent/src/kisansathi_agent/config.py`; defaults to loopback port 8000.
- `CODEX_BINARY` and `KISANSATHI_PYTHON` - optional executable overrides in `desktop/codex-harness.cjs`.
- `MONGODB_URL` and `DATABASE_NAME` - central reference database settings in `backend/app/core/config.py`; local defaults exist, but reference endpoints degrade without a reachable MongoDB.
- `SARVAM_API_KEY` - required only to enable implemented Sarvam voice/translation calls in `backend/app/services/sarvam.py`.
- `SCRAPER_WEBHOOK_TOKEN` - required to authorize the ingestion routes in `backend/app/routers/ingestion.py`.
- `DATA_GOV_IN_API_KEY` - recommended for official market ingestion in `backend/app/scraping/sources.py`; an unreliable public-page discovery fallback exists.
- `VITE_FARM_STATE_API_URL`, `VITE_REFERENCE_API_URL`, and `VITE_DEMO_FARMER_ID` - optional renderer overrides in `src/api/client.js`.
- `N8N_ENCRYPTION_KEY` and backend/token configuration are consumed by the local n8n compose/workflow in `backend/docker-compose.universal-data.yml` and `backend/n8n/universal-data-sync.json`; values must remain outside source control.

**Secrets location:**
- `backend/.env` exists and is configured as the Pydantic settings file by `backend/app/core/config.py`; its contents were not read or quoted.
- `backend/.env.example` exists as a configuration template; its contents were not read because environment files are excluded from codebase-map inspection.
- Codex credentials are managed by the installed/upstream Codex authentication stack, including `codex/codex-rs/login/` and `codex/codex-rs/keyring-store/`; the desktop bridge in `desktop/codex-harness.cjs` does not copy credentials into the renderer.

## Webhooks & Callbacks

**Incoming:**
- `POST /internal/universal-data/sync` in `backend/app/routers/ingestion.py` is the implemented n8n/manual ingestion webhook; it requires `X-Ingestion-Token` and accepts the bounded source set defined in `backend/app/scraping/service.py`.
- Electron IPC calls are exposed only through the context-isolated API in `desktop/preload.cjs`; handlers in `desktop/main.cjs` cover session/chat/voice/status/approval operations.
- Codex app-server JSON-RPC server requests and notifications are handled over stdio by `desktop/codex-harness.cjs`, including approvals and user-input requests.
- KisanSathi MCP tool calls arrive over stdio at `agent/src/kisansathi_agent/server.py` and are translated into backend HTTP requests by `agent/src/kisansathi_agent/backend_client.py`.

**Outgoing:**
- FastAPI calls Open-Meteo from `backend/app/services/weather.py`, Sarvam from `backend/app/services/sarvam.py`, data.gov.in and PIB sources from `backend/app/scraping/sources.py`.
- Browser map search/tiles call Nominatim and OpenStreetMap directly from `src/components/fields/LocationPicker.jsx`; static remote imagery is loaded from URLs in `src/data/images.js` and `src/services/hostedCatalogService.js`.
- n8n calls the backend sync endpoint as defined by `backend/n8n/universal-data-sync.json`.
- No SMS, WhatsApp, email, push notification, payment, booking, vendor-contact, MQTT, smart-plug, satellite, logistics, insurance, credit, or object-storage outbound adapter exists in executable application code under `src/`, `desktop/`, `backend/app/`, `agent/src/`, or `codex/plugins/kisansathi/`.

## Explicitly Missing or Mocked Integrations

- Crop diagnosis ML is not integrated: `backend/app/routers/assistants.py` validates/stores images and always records an inconclusive result because `DIAGNOSIS_PROVIDER` defaults to `unconfigured` in `backend/app/core/config.py`; no model artifact was found outside an unrelated Codex SDK notebook.
- The deprecated backend advisor endpoints return a fixed provider-unavailable message in `backend/app/routers/assistants.py`; live agent conversation instead runs through the desktop Codex harness in `desktop/codex-harness.cjs`.
- IoT/sensor ingestion has REST/SQLite data structures in `backend/app/routers/farm_state.py` and `backend/app/farm_state/store.py`, but no firmware, MQTT broker/client, device-authentication adapter, smart relay, or pump-control integration exists in executable application code.
- Satellite/remote-sensing imagery and vegetation-index providers are not present; current maps use OpenStreetMap only in `src/components/fields/LocationPicker.jsx`.
- Machinery and government reference endpoints persist MongoDB data through `backend/app/routers/machinery_rental.py` and `backend/app/routers/gov_scheme.py`, but no external vendor/booking/scheme provider adapter exists; `src/services/hostedCatalogService.js` is hardcoded demo content.
- Notifications are stored as alerts/delivery rows in `backend/app/farm_state/store.py`, but no email/SMS/push delivery provider is implemented in `backend/app/`.

---

*Integration audit: 2026-08-20*
