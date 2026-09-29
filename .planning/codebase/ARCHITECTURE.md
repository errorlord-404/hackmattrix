<!-- refreshed: 2026-08-20 -->
# Architecture

**Analysis Date:** 2026-08-20

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Farmer experience                                                          │
├───────────────────────────────┬─────────────────────────────────────────────┤
│ React/Vite manual application │ Electron-hosted Codex conversation          │
│ `src/`                        │ `desktop/` + `src/context/AIConversation…`   │
└──────────────┬────────────────┴───────────────────┬─────────────────────────┘
               │ HTTP                              │ isolated IPC
               │                                   ▼
               │                    ┌────────────────────────────────────────┐
               │                    │ Codex app-server JSONL client          │
               │                    │ `desktop/codex-harness.cjs`            │
               │                    └──────────────────┬─────────────────────┘
               │                                       │ stdio JSONL
               │                                       ▼
               │                    ┌────────────────────────────────────────┐
               │                    │ Forked Codex CLI / app-server          │
               │                    │ `codex/codex-rs/cli/`                  │
               │                    │ `codex/codex-rs/app-server/`           │
               │                    └──────────────────┬─────────────────────┘
               │                                       │ MCP over stdio
               │                                       ▼
               │                    ┌────────────────────────────────────────┐
               │                    │ KisanSathi Python MCP adapter          │
               │                    │ `agent/src/kisansathi_agent/`          │
               │                    │ launcher: `codex/plugins/kisansathi/`  │
               │                    └──────────────────┬─────────────────────┘
               │                                       │ farmer-scoped HTTP
               ▼                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FastAPI application                                                        │
│ `backend/app/main.py`                                                       │
├──────────────────────────────────┬──────────────────────────────────────────┤
│ Farm-state API (`/v1/*`)         │ Reference/catalog APIs                   │
│ `backend/app/routers/farm_state.py`│ `backend/app/routers/*.py`              │
│ `backend/app/routers/weather.py`  │ ingestion: `backend/app/scraping/`       │
│ `backend/app/routers/assistants.py`│                                          │
└───────────────┬──────────────────┴───────────────────┬──────────────────────┘
                ▼                                      ▼
┌───────────────────────────────┐       ┌─────────────────────────────────────┐
│ Farmer-scoped SQLite files    │       │ MongoDB shared reference catalog   │
│ `backend/app/farm_state/store.py`│     │ `backend/app/models/`              │
│ `backend/data/farm_state/`    │       │ `backend/app/core/database.py`      │
└───────────────────────────────┘       └─────────────────────────────────────┘
```

The repository is a modular monolith around one FastAPI process, plus a local desktop agent boundary. The React renderer and the MCP adapter are two clients of the same backend. The Codex fork remains a general-purpose harness: KisanSathi capabilities enter through an external MCP plugin rather than native farming handlers in `codex/codex-rs/core/src/tools/handlers/`.

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| React composition root | Mount providers and the route tree | `src/main.jsx`, `src/App.jsx` |
| Manual farmer application | Render dashboard, fields, map, soil, weather, irrigation, market, schemes, finance, machinery, reports, settings, and assistant pages | `src/routes/index.jsx`, `src/pages/` |
| Farm data context | Load profile, fields, map summaries, and alerts; expose profile/field/alert mutations | `src/context/FarmDataContext.jsx` |
| Conversation context | Own Codex thread state, streamed messages, tool events, approvals, image fallback, voice capture, translation, and speech playback | `src/context/AIConversationContext.jsx` |
| Browser API boundary | Add request IDs and farmer headers, normalize errors, and split farm-state/reference base URLs | `src/api/client.js`, `src/api/farmStateApi.js`, `src/api/referenceApi.js` |
| Electron security boundary | Create the sandboxed window and expose a narrow IPC contract | `desktop/main.cjs`, `desktop/preload.cjs` |
| Codex JSONL client | Spawn `codex app-server --stdio`, start/resume threads, send turns, normalize notifications, and bridge approvals | `desktop/codex-harness.cjs` |
| Codex fork | Provide the general agent loop, app-server protocol, model integration, MCP routing, skills, approvals, thread persistence, and plugin infrastructure | `codex/codex-rs/cli/`, `codex/codex-rs/app-server/`, `codex/codex-rs/core/`, `codex/codex-rs/plugin/`, `codex/codex-rs/core-plugins/` |
| KisanSathi plugin package | Declare the local skill/MCP capability and launch the shared Python package | `codex/plugins/kisansathi/.codex-plugin/plugin.json`, `codex/plugins/kisansathi/.mcp.json`, `codex/plugins/kisansathi/run_server.py` |
| Python MCP adapter | Register 47 task-oriented read/write tools and convert tool calls to farmer-scoped backend HTTP requests | `agent/src/kisansathi_agent/server.py`, `agent/src/kisansathi_agent/tools.py` |
| Tool contract boundary | Bind farmer identity from the trusted launcher, generate request/idempotency IDs, bound model-visible payloads, and normalize tool envelopes | `agent/src/kisansathi_agent/config.py`, `agent/src/kisansathi_agent/backend_client.py`, `agent/src/kisansathi_agent/result.py` |
| FastAPI composition root | Start reference persistence in degraded-safe mode, configure CORS, and register every router | `backend/app/main.py` |
| Farm digital-twin slice | Persist per-farmer profile, fields, crop cycles, soil, observations, irrigation, reminders, alerts, diagnoses, reports, and advisor records | `backend/app/farm_state/store.py`, `backend/app/routers/farm_state.py`, `backend/app/routers/assistants.py` |
| Deterministic farm rules | Interpret soil measurements and screen irrigation needs without activating equipment | `backend/app/farm_state/rules.py` |
| External data adapters | Fetch Open-Meteo weather and Sarvam translation/STT/TTS | `backend/app/services/weather.py`, `backend/app/services/sarvam.py` |
| Shared reference catalog | Persist crops, diseases, fertilizers, schemes, market prices, MSP, seeds, machinery rentals, farmers, and ingestion runs in MongoDB | `backend/app/models/`, `backend/app/core/database.py` |
| Universal-data ingestion | Fetch/parse government market and MSP sources, normalize records, and bulk upsert MongoDB documents | `backend/app/scraping/sources.py`, `backend/app/scraping/service.py`, `backend/app/routers/ingestion.py` |
| Device-private finance store | Persist the UI finance ledger in `localStorage`; a second unused IndexedDB implementation also exists | `src/features/financeStore.js`, `src/db/localDatabase.js` |

## Pattern Overview

**Overall:** Layered local-first farm application with an external agent adapter (ports-and-adapters at the Codex boundary).

**Key Characteristics:**

- Keep deterministic farm state and calculations outside the language model. The model orchestrates named MCP tools from `agent/src/kisansathi_agent/server.py`; tools call backend capabilities in `agent/src/kisansathi_agent/tools.py`.
- Keep the renderer unprivileged. `desktop/preload.cjs` exposes only session, chat, voice, approval, clarification, and event operations while `desktop/main.cjs` retains filesystem, process, and backend access.
- Use one FastAPI deployment for farmer state, reference catalogs, weather, provider adapters, and ingestion. Persistence is split by data ownership, not by separate deployed services.
- Bind farmer identity outside model arguments. `desktop/main.cjs` supplies `KISANSATHI_FARMER_ID`; `agent/src/kisansathi_agent/config.py` requires it; `agent/src/kisansathi_agent/backend_client.py` forwards it as `X-Farmer-ID`.
- Treat MCP tools as wrappers rather than farm-domain owners. The stable result/action envelope lives in `agent/src/kisansathi_agent/result.py`; farm data and rules live under `backend/app/`.
- Preserve upstream Codex seams. No KisanSathi module is present under `codex/codex-rs/core/src/tools/handlers/`; `desktop/codex-harness.cjs` injects `mcp_servers.kisansathi.*` through CLI `-c` overrides for its child process only.

## Layers

**Presentation layer:**

- Purpose: Present manual workflows and a conversational workflow to the farmer.
- Location: `src/pages/`, `src/components/`, `src/routes/index.jsx`.
- Contains: React route pages, responsive shell components, field-location picker, API states, chat UI, and multilingual strings.
- Depends on: `src/context/`, `src/api/`, `src/features/financeStore.js`, React Router, Leaflet, i18next.
- Used by: Browser-hosted Vite builds and the Electron renderer.

**Client application-state layer:**

- Purpose: Coordinate shared farm data, language, and Codex conversation state across pages.
- Location: `src/context/FarmDataContext.jsx`, `src/context/AIConversationContext.jsx`, `src/hooks/useLanguage.jsx`.
- Contains: Network loading/mutation flows, active field selection, Codex session/thread state, streamed assistant drafts, voice/image actions, and approval prompts.
- Depends on: `src/api/`, `window.kisanHarness`, i18next, browser storage/media APIs.
- Used by: `src/pages/` and `src/components/`.

**Browser transport layer:**

- Purpose: Isolate backend URLs, headers, timeouts, request serialization, and error shapes from page components.
- Location: `src/api/client.js`, `src/api/farmStateApi.js`, `src/api/referenceApi.js`.
- Contains: `apiRequest()`, `ApiError`, farmer ID resolution, farm-state endpoint methods, and reference endpoint methods.
- Depends on: Browser `fetch`, `localStorage`, and Vite environment variables.
- Used by: Context providers and route pages.

**Desktop host layer:**

- Purpose: Securely host the renderer and operate local Codex/backend capabilities unavailable to a normal browser tab.
- Location: `desktop/main.cjs`, `desktop/preload.cjs`, `desktop/codex-harness.cjs`.
- Contains: BrowserWindow setup, IPC handlers, health checks, media validation/temp files, app-server lifecycle, JSONL protocol handling, and event normalization.
- Depends on: Electron, an installed/signed-in `codex` executable, Python, the KisanSathi plugin launcher, and FastAPI.
- Used by: `src/context/AIConversationContext.jsx` through `window.kisanHarness`.

**Codex harness layer:**

- Purpose: Run the agent/model loop, thread lifecycle, tool calls, approvals, skills, plugins, and MCP connections.
- Location: `codex/codex-rs/cli/src/main.rs`, `codex/codex-rs/app-server/`, `codex/codex-rs/core/`, `codex/codex-rs/core/src/tools/`, `codex/codex-rs/plugin/`, `codex/codex-rs/core-plugins/`.
- Contains: Rust workspace crates for CLI commands, app-server JSON-RPC, core sessions/threads, built-in tools, MCP clients, plugin discovery, and persistence.
- Depends on: The wider workspace declared in `codex/codex-rs/Cargo.toml` and external model/provider configuration.
- Used by: `desktop/codex-harness.cjs`, which launches `codex app-server --stdio`.

**Farm agent adapter layer:**

- Purpose: Expose farm-specific tools without coupling farm business logic to the Codex fork.
- Location: `agent/src/kisansathi_agent/`, `codex/plugins/kisansathi/`.
- Contains: FastMCP server construction, read/write annotations, backend client, tool/result envelopes, and local plugin metadata/skill instructions.
- Depends on: MCP Python SDK, HTTPX, trusted environment configuration, and FastAPI endpoint contracts.
- Used by: Codex as an MCP server over stdio.

**HTTP application layer:**

- Purpose: Validate requests, map them to storage/provider operations, and return typed farm/reference responses.
- Location: `backend/app/main.py`, `backend/app/routers/`, `backend/app/schemas/`.
- Contains: ASGI lifecycle, CORS, router composition, Pydantic DTOs, CRUD endpoints, derived dashboards/plans, assistant/provider routes, and ingestion triggers.
- Depends on: `backend/app/farm_state/`, `backend/app/services/`, `backend/app/scraping/`, and `backend/app/models/`.
- Used by: React API clients and the Python MCP adapter.

**Domain/service layer:**

- Purpose: Hold deterministic calculations and replaceable external/provider policies.
- Location: `backend/app/farm_state/rules.py`, `backend/app/services/`, `backend/app/scraping/`.
- Contains: Soil interpretation, irrigation screening, net-realisation calculation, catalog mutations/recommendations, weather normalization, Sarvam calls, and government-data ingestion.
- Depends on: Typed inputs, settings, standard HTTP clients, and persistence models.
- Used by: Backend routers.

**Persistence layer:**

- Purpose: Keep farmer-operational state isolated while sharing reference catalogs.
- Location: `backend/app/farm_state/store.py`, `backend/app/models/`, `backend/app/core/database.py`.
- Contains: One SQLite file per sanitized farmer key plus Beanie documents registered against MongoDB.
- Depends on: SQLite, Motor, Beanie, and settings from `backend/app/core/config.py`.
- Used by: Farm-state dependencies/routers and reference routers/ingestion.

## Data Flow

### Manual Farm Screen Request Path

1. `src/main.jsx:7` mounts `App`, whose providers wrap the router in `src/App.jsx:8`.
2. `src/context/FarmDataContext.jsx:9` loads profile, fields, map summaries, and alerts through `src/api/farmStateApi.js`.
3. `src/api/client.js:18` adds `X-Request-ID`; farmer-scoped calls also receive `X-Farmer-ID` from local configuration.
4. `backend/app/main.py:43` registers `backend/app/routers/farm_state.py`, whose handlers resolve a store through `backend/app/farm_state/dependencies.py:8`.
5. `backend/app/farm_state/store.py:365` opens `backend/data/farm_state/<farmer>.sqlite3`, enforces foreign keys, initializes the schema, and executes the query.
6. The typed JSON response returns through the API client to context/page state and renders with explicit loading/error/empty UI from `src/components/feedback/ApiState.jsx`.

### Codex Conversation and Tool Path

1. `src/context/AIConversationContext.jsx` calls the narrow `window.kisanHarness` bridge exported by `desktop/preload.cjs`.
2. `desktop/main.cjs` forwards the IPC operation to `CodexHarness` while retaining child-process and filesystem authority in the main process.
3. `desktop/codex-harness.cjs:115` spawns `codex app-server --stdio` and injects the KisanSathi MCP command, working directory, environment, approval mode, and timeouts with per-process CLI overrides.
4. `desktop/codex-harness.cjs:28` initializes app-server and starts or resumes a Codex thread; `desktop/codex-harness.cjs:91` sends a turn with field/language metadata.
5. Codex discovers the injected MCP server and invokes a tool registered in `agent/src/kisansathi_agent/server.py:29`.
6. `agent/src/kisansathi_agent/tools.py:25` or `agent/src/kisansathi_agent/tools.py:48` calls the HTTP boundary in `agent/src/kisansathi_agent/backend_client.py:48`, which supplies trusted farmer/request/idempotency headers.
7. FastAPI reads or mutates SQLite/MongoDB/provider state, and `agent/src/kisansathi_agent/result.py` converts the response to a bounded tool envelope with warnings, provenance, and write-action refresh hints.
8. Codex produces an English response; app-server notifications are normalized by `desktop/codex-harness.cjs`, streamed to React, translated through `/v1/translate`, and optionally synthesized through `/v1/voice/synthesize`.

### Crop Image Path

1. The desktop chat sends bytes through `desktop/preload.cjs`; `desktop/main.cjs` validates JPEG/PNG/WebP and size, writes a temporary image, and passes a local-image input to Codex.
2. Codex can reason over the image and call farm tools. The React context falls back to `farmStateApi.createDiagnosis()` when a vision turn cannot start.
3. `backend/app/routers/assistants.py:105` validates and stores the upload plus diagnosis request/record in the farmer SQLite database.
4. With `DIAGNOSIS_PROVIDER=unconfigured`, the persisted result is explicitly provider-unavailable/inconclusive; no production diagnosis model is implemented.

### Voice and Translation Path

1. `src/context/AIConversationContext.jsx` captures browser audio and sends it through Electron IPC.
2. `desktop/main.cjs` proxies bytes to `backend/app/routers/assistants.py:248`; `backend/app/services/sarvam.py` calls Sarvam when configured.
3. Non-English text is translated to English before `turn/start`; completed English assistant text is translated back to the selected `en-IN`, `hi-IN`, or `mr-IN` language code and optionally synthesized.
4. The backend `/v1/voice/turns` endpoint is a separate compatibility path and currently returns a fixed “advisor not configured” response after transcription rather than invoking Codex.

### Universal Reference Data Flow

1. A caller invokes `backend/app/routers/ingestion.py:33` or the CLI entry `backend/app/scraping/__main__.py`.
2. `backend/app/scraping/sources.py` fetches data.gov.in market records and PIB MSP pages, with source-specific parsing and stable IDs.
3. `backend/app/scraping/service.py` normalizes and bulk-upserts `MarketPrice`, `MSP`, and derived `Crop` documents while recording an `IngestionRun`.
4. Reference routers expose MongoDB-backed catalog/history/summary/trend/comparison responses to both `src/api/referenceApi.js` and the MCP tools.

**State Management:**

- Authoritative farmer operational state is a server-hosted, farmer-keyed SQLite file created by `backend/app/farm_state/store.py`; the current header is an isolation key, not authentication.
- Shared agricultural reference state is in MongoDB through Beanie documents in `backend/app/models/`.
- React keeps transient UI state in hooks/contexts. Codex thread IDs and UI preferences persist in `localStorage` through `src/context/AIConversationContext.jsx`.
- The finance ledger is separately persisted in browser `localStorage` by `src/features/financeStore.js`, so it is not part of the backend digital twin or MCP-visible state.
- Codex conversation and thread persistence are owned by the Codex app-server, not by the deprecated SQLite advisor-session endpoints.

## Key Abstractions

**Farmer-scoped store:**

- Purpose: Give each sanitized farmer key an isolated SQLite file and relational schema.
- Examples: `backend/app/farm_state/store.py`, `backend/app/farm_state/dependencies.py`.
- Pattern: Request-scoped repository opened from the `X-Farmer-ID` header and closed after the FastAPI dependency yields.

**Reference document domain:**

- Purpose: Model shared crop/catalog/market data independently from farmer operational state.
- Examples: `backend/app/models/crop.py`, `backend/app/models/market_price.py`, `backend/app/models/msp.py`, `backend/app/models/machinery_rental.py`.
- Pattern: Beanie document + Pydantic schema + APIRouter, registered centrally in `backend/app/core/database.py` and `backend/app/main.py`.

**KisanSathi tool:**

- Purpose: Present one safe, task-oriented farm capability to the model.
- Examples: registrations in `agent/src/kisansathi_agent/server.py`; implementations in `agent/src/kisansathi_agent/tools.py`.
- Pattern: FastMCP annotation → thin adapter method → `BackendClient` → stable `tool_result()` / `write_action()` envelope.

**Codex desktop session:**

- Purpose: Maintain one child app-server, active thread, active turn, pending JSONL requests, and temporary media set.
- Examples: `desktop/codex-harness.cjs`.
- Pattern: EventEmitter-based JSON-RPC/JSONL client behind Electron IPC.

**Farm-state response provenance:**

- Purpose: Keep source, observation time, fetch time, freshness, confidence, warnings, recommendations, and unavailable states visible.
- Examples: `backend/app/schemas/farm_state.py`, `agent/src/kisansathi_agent/result.py`.
- Pattern: Typed Pydantic response nested in a bounded MCP result envelope.

## Entry Points

**Web renderer:**

- Location: `index.html`, `src/main.jsx`.
- Triggers: Vite development server, preview server, or built renderer load.
- Responsibilities: Mount React and load the application provider/router tree.

**Electron application:**

- Location: `desktop/main.cjs` (declared by `package.json`).
- Triggers: `npm run desktop`, `npm run desktop:dev`, or `npm run desktop:build`.
- Responsibilities: Create the secure window, load Vite or `dist/index.html`, own IPC, proxy voice/provider calls, and manage the Codex harness.

**FastAPI service:**

- Location: `backend/app/main.py`.
- Triggers: An ASGI server imports `app`.
- Responsibilities: Initialize MongoDB when available, remain operational in degraded reference mode, register middleware/routes, and expose `/health`.

**Universal-data CLI:**

- Location: `backend/app/scraping/__main__.py`.
- Triggers: Python module execution.
- Responsibilities: Run selected market/MSP ingestion sources outside an HTTP request.

**Python MCP server:**

- Location: `agent/src/kisansathi_agent/__main__.py`.
- Triggers: Console/module execution or `codex/plugins/kisansathi/run_server.py`.
- Responsibilities: Load trusted settings, create the HTTP client, build FastMCP registrations, and serve over stdio.

**Codex CLI/app-server:**

- Location: `codex/codex-rs/cli/src/main.rs`.
- Triggers: `codex app-server --stdio` from `desktop/codex-harness.cjs`.
- Responsibilities: Run thread/turn/model/tool orchestration and connect to the injected MCP server.

## Architectural Constraints

- **Threading:** React/Electron use JavaScript event loops; FastAPI reference operations are async, while farmer SQLite route functions perform synchronous per-request SQLite work. Provider calls based on `urllib` are shifted to threads with `asyncio.to_thread` in weather/Sarvam paths.
- **Global state:** React providers hold client state; `backend/app/core/config.py` creates module-global `settings`; `backend/app/main.py` creates module-global `app`; the Electron main process creates one module-global `CodexHarness`; `src/db/localDatabase.js` creates an eager singleton even though no production page imports it.
- **Farmer isolation:** `X-Farmer-ID` selects the SQLite filename in `backend/app/farm_state/dependencies.py`. It is explicitly not authentication; do not treat it as a production identity boundary.
- **Database availability:** MongoDB startup failure does not stop FastAPI. Farm-state/voice/weather routes can remain available while reference routes may fail; `/health` reports `degraded`.
- **Write approval:** MCP write tools are annotated non-read-only in `agent/src/kisansathi_agent/server.py`; the desktop injects `default_tools_approval_mode="writes"` and starts turns with `approvalPolicy: "on-request"`. Manual HTTP UI mutations do not pass through Codex approval.
- **Physical safety:** Current tools only read state, calculate, or persist records. `record_irrigation_event` does not operate a pump; no device command channel exists.
- **Harness extension:** Use the external MCP/plugin seam in `agent/` and `codex/plugins/kisansathi/`. Native KisanSathi Rust handlers are absent, and current application integration does not depend on modifying `codex/codex-rs/core/src/tools/handlers/`.
- **Circular imports:** No application-layer circular import chain was detected. Keep routers dependent on domain/store/services, not on React, Electron, or MCP modules.
- **Desktop routing:** Use browser history for HTTP(S) renderer URLs and hash history for production `file://` loads, as selected in `src/routes/index.jsx`.

## Anti-Patterns

### Duplicate device-local persistence boundaries

**What happens:** `src/features/financeStore.js` is the live finance ledger, while `src/db/localDatabase.js` independently defines IndexedDB finance, soil, and weather stores and seeds demo records but is not imported by application pages.
**Why it's wrong:** Two incompatible local persistence models can diverge, create misleading seeded state, and obscure which data participates in the farm digital twin.
**Do this instead:** Treat `src/features/financeStore.js` as the current finance authority until one explicit migration replaces it; do not add new callers to `src/db/localDatabase.js` without reconciling ownership and migration behavior.

### Documentation-driven native Rust farming placement

**What happens:** `README.md` tells contributors to add KisanSathi handlers under a native Rust path, but the functional integration is the Python MCP adapter in `agent/` launched by `codex/plugins/kisansathi/` and injected by `desktop/codex-harness.cjs`.
**Why it's wrong:** Following the stale path would duplicate tool contracts and couple farm-domain releases to the entire Codex Rust workspace.
**Do this instead:** Add farm tools in `agent/src/kisansathi_agent/server.py` and `agent/src/kisansathi_agent/tools.py`, backed by typed endpoints in `backend/app/`; modify Rust only for a demonstrated general harness requirement.

### Treating a farmer header as authentication

**What happens:** Browser code can choose `X-Farmer-ID`, and `backend/app/farm_state/dependencies.py` uses it directly to select a farmer database.
**Why it's wrong:** Any network client can request another farmer key; file separation provides local partitioning, not authenticated authorization.
**Do this instead:** Keep this boundary restricted to the local/demo deployment. Put authenticated subject-to-farmer mapping ahead of `get_farm_store()` before exposing the service to untrusted networks.

### Split conversational authority

**What happens:** Codex app-server owns the live assistant flow, while deprecated `/v1/advisor/sessions` routes and SQLite advisor tables remain callable and return provider-unavailable placeholder behavior.
**Why it's wrong:** Two session/message authorities can produce inconsistent histories and encourage new code to attach to the wrong conversation path.
**Do this instead:** Use `desktop/codex-harness.cjs` plus Codex thread IDs for conversation state. Limit deprecated advisor endpoints to compatibility until removed through a deliberate migration.

### Approximate geometry presented through two map implementations

**What happens:** `src/components/fields/LocationPicker.jsx` uses live OpenStreetMap tiles and a point marker, `src/pages/MyFields.jsx` converts the point into an approximate square, and `src/pages/FieldTools.jsx` renders stored polygons on a schematic SVG rather than a geographic tile map.
**Why it's wrong:** The displayed field outline is not a surveyed boundary and the farm-map visualization can appear geographically authoritative while only normalizing coordinates into a local canvas.
**Do this instead:** Preserve the `approximate_point_buffer` quality marker, and use `boundary_geojson` consistently through a real geographic map component when editing or displaying boundaries.

### Broad FastAPI composition root

**What happens:** `backend/app/main.py` hosts operational state, reference catalogs, ingestion, external weather, translation/voice, diagnosis persistence, and deprecated advisor endpoints.
**Why it's wrong:** The single process is appropriate for this MVP, but unbounded router-level business logic will make provider and persistence changes hard to isolate.
**Do this instead:** Keep one deployment while moving reusable decisions into `backend/app/farm_state/`, `backend/app/services/`, or `backend/app/scraping/`; routers should remain typed transport adapters.

## Error Handling

**Strategy:** Normalize errors at each boundary while preserving explicit unavailable/degraded states instead of inventing agricultural facts.

**Patterns:**

- `src/api/client.js` converts timeout, network, and non-2xx responses into `ApiError`; pages render `LoadingState`, `ErrorState`, or `EmptyState` from `src/components/feedback/ApiState.jsx`.
- Backend routers raise typed `HTTPException` for invalid IDs, missing records, validation failures, and provider failures; Pydantic handles request validation.
- `backend/app/main.py` catches MongoDB initialization failure, records it on `app.state`, and keeps farmer-state routes alive.
- `backend/app/services/weather.py` and `backend/app/services/sarvam.py` wrap provider failures in domain exceptions without exposing secrets.
- `agent/src/kisansathi_agent/backend_client.py` maps HTTP/network errors to `BackendError`; `agent/src/kisansathi_agent/tools.py` returns stable retryable/non-retryable tool errors instead of throwing into the agent loop.
- `desktop/codex-harness.cjs` rejects pending JSONL requests when the child exits, emits recoverable `unavailable` events, and cleans temporary media.

## Cross-Cutting Concerns

**Logging:** FastAPI has no centralized application logging configuration; the Python MCP entry configures basic logging; Electron reports renderer/process diagnostics to stderr and emits Codex diagnostics into chat state; Codex receives `LOG_FORMAT=json` from the harness.

**Validation:** Pydantic schemas in `backend/app/schemas/` validate HTTP shapes; Beanie models validate reference persistence; SQLite CHECK/foreign-key constraints validate selected operational fields; Electron and assistant routes validate media types/sizes; agent settings validate trusted URLs/farmer IDs.

**Authentication:** Not implemented. `X-Farmer-ID` is a temporary local identity selector. Reference catalog routes and ingestion exposure are not protected by user authentication; ingestion supports an optional webhook token in `backend/app/routers/ingestion.py`.

**Localization:** `src/i18n/` and `src/hooks/useLanguage.jsx` provide English/Hindi/Marathi UI resources. Conversation input/output translation is a separate Sarvam-backed runtime path coordinated by `src/context/AIConversationContext.jsx`.

**Provenance and freshness:** Weather, market, soil, tool, and provider responses carry source/time/warning fields through backend schemas and `agent/src/kisansathi_agent/result.py`. Preserve these fields when adding new capabilities.

**Idempotency:** MCP writes hash path and payload in `agent/src/kisansathi_agent/tools.py`; farmer-state write routes persist responses in the `idempotency_records` table from `backend/app/farm_state/store.py`.

**Safety:** Read/write MCP annotations, approval mode, confirmation instructions, media limits, bounded tool output, and the absence of physical-control APIs are deliberate safety boundaries.

---

*Architecture analysis: 2026-08-20*
