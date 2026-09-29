# Codebase Structure

**Analysis Date:** 2026-08-20

## Directory Layout

```text
[project-root]/
├── src/                                  # React/Vite farmer renderer
│   ├── api/                              # HTTP client and endpoint façades
│   ├── components/
│   │   ├── features/ai/                  # Chat, voice, and harness status UI
│   │   ├── feedback/                     # Loading/error/empty/provenance UI
│   │   ├── fields/                       # Leaflet field location picker
│   │   └── layout/                       # Responsive navigation/application shell
│   ├── constants/                        # Legacy/page translation constants
│   ├── context/                          # Farm and Codex conversation state
│   ├── data/                             # Navigation, images, and legacy fixtures
│   ├── db/                               # Unused IndexedDB/localStorage prototype
│   ├── features/                         # Live browser-local finance store
│   ├── hooks/                            # Language provider/hook
│   ├── i18n/                             # English, Hindi, Marathi resources
│   ├── pages/                            # Route-level farmer workflows
│   ├── routes/                           # Browser/hash router declaration
│   ├── services/                         # Unused hardcoded hosted-catalog prototype
│   ├── App.jsx                           # Provider composition
│   ├── main.jsx                          # React DOM entry point
│   └── index.css                         # Tailwind theme/global styles
├── desktop/                              # Electron host and Codex JSONL bridge
│   ├── main.cjs                          # Main-process composition root/IPC
│   ├── preload.cjs                       # Sandboxed renderer contract
│   ├── codex-harness.cjs                 # `codex app-server --stdio` client
│   └── README.md                         # Desktop operation/verification guide
├── agent/                                # Python farm MCP adapter package
│   ├── config/                           # Example Codex MCP configuration
│   ├── skills/kisansathi/                # Standalone farm skill guidance
│   ├── src/kisansathi_agent/             # FastMCP server/tools/backend boundary
│   ├── tests/                            # Python adapter unit tests
│   ├── pyproject.toml                    # Package/dependency configuration
│   └── README.md                         # Tool inventory and local setup
├── backend/                              # FastAPI farm/reference application
│   ├── app/
│   │   ├── core/                         # Settings and MongoDB/Beanie startup
│   │   ├── farm_state/                   # Per-farmer SQLite schema/store/rules
│   │   ├── models/                       # MongoDB reference Beanie documents
│   │   ├── routers/                      # REST transport by domain
│   │   ├── schemas/                      # Pydantic request/response contracts
│   │   ├── scraping/                     # Government-source ingestion pipeline
│   │   ├── services/                     # Domain/provider adapters
│   │   └── main.py                       # ASGI composition root
│   ├── automation/                       # Automation workspace (currently empty)
│   ├── data/                             # Runtime SQLite/upload artifacts
│   ├── docs/                             # Backend/product/provider documentation
│   ├── n8n/                              # Universal-data workflow definition
│   ├── scripts/                          # Data setup script
│   ├── tests/                            # Backend pytest suite
│   ├── AGENTS.md                         # Backend-local contribution constraints
│   ├── requirements.txt                  # Backend dependency pins
│   └── docker-compose.universal-data.yml # Ingestion automation stack
├── codex/                                # Full checked-in OpenAI Codex fork
│   ├── codex-rs/                         # Multi-crate Rust workspace
│   │   ├── cli/                          # `codex` command entry point
│   │   ├── app-server/                   # Desktop-facing JSON-RPC server
│   │   ├── app-server-protocol/          # Shared/generated protocol types
│   │   ├── core/                         # Agent loop, sessions, tools, MCP
│   │   ├── core-plugins/                 # Plugin manifest/marketplace loading
│   │   ├── plugin/                       # Runtime plugin abstractions
│   │   └── ...                           # Supporting Codex crates
│   ├── plugins/kisansathi/               # Farm plugin manifest/skill/launcher
│   ├── codex-cli/                        # npm distribution wrapper
│   ├── sdk/                              # Python/TypeScript SDKs
│   ├── docs/                             # Upstream Codex documentation
│   └── scripts/, tools/, third_party/    # Upstream development support
├── tests/desktop/                        # Node tests for Electron/Codex bridge
├── public/                               # Vite-served static assets
├── dist/                                 # Generated Vite renderer bundle
├── .planning/                            # GSD plans, research, and maps
├── index.html                            # Vite HTML entry
├── package.json                          # Web/Electron scripts/dependencies
├── vite.config.js                        # Vite/Tailwind/asset config
├── vitest.config.js                      # Renderer unit-test config
├── eslint.config.js                      # Frontend lint config
├── IMPLEMENTATION_AUDIT.md               # Repository audit artifact
├── CODEX_AI_HARNESS_MERGE_PLAN.md        # Harness integration plan artifact
├── MCP_AGENT_IMPLEMENTATION_PLAN.md      # MCP implementation plan artifact
├── FRONTEND_BACKEND_MERGE_PLAN.md        # UI/backend integration plan artifact
└── README.md                             # Legacy native-Rust tool guidance
```

## Directory Purposes

**`src/`:**

- Purpose: Browser/Electron renderer for all farmer-facing workflows.
- Contains: React routes/pages, contexts, API clients, responsive components, localization, and device-local finance state.
- Key files: `src/main.jsx`, `src/App.jsx`, `src/routes/index.jsx`, `src/context/FarmDataContext.jsx`, `src/context/AIConversationContext.jsx`.

**`src/api/`:**

- Purpose: Keep transport mechanics and backend endpoint names out of presentation components.
- Contains: Common fetch/error/header behavior plus farm-state and reference API method maps.
- Key files: `src/api/client.js`, `src/api/farmStateApi.js`, `src/api/referenceApi.js`.

**`src/components/features/ai/`:**

- Purpose: Present Codex conversation, voice controls, tool activity, approval/clarification prompts, and harness readiness.
- Contains: `ConversationView`, `VoiceButton`, `HarnessStatusCard`, and the renderer unit test.
- Key files: `src/components/features/ai/ConversationView.jsx`, `src/components/features/ai/HarnessStatusCard.jsx`.

**`src/components/feedback/`:**

- Purpose: Standardize live API loading, failure, empty, and provenance states.
- Contains: Small presentational components.
- Key files: `src/components/feedback/ApiState.jsx`.

**`src/components/fields/`:**

- Purpose: Select a field point from GPS, OpenStreetMap search, or direct map interaction.
- Contains: React-Leaflet map and Nominatim lookup logic.
- Key files: `src/components/fields/LocationPicker.jsx`.

**`src/components/layout/`:**

- Purpose: Provide shared responsive chrome and farmer alerts.
- Contains: Desktop sidebar/header, mobile header/drawer/bottom navigation, application shell, alert menu.
- Key files: `src/components/layout/AppShell.jsx`, `src/components/layout/Header.jsx`, `src/components/layout/AlertMenu.jsx`.

**`src/context/`:**

- Purpose: Own cross-route farm and conversation state.
- Contains: Backend farm-data synchronization and Electron/Codex conversation orchestration.
- Key files: `src/context/FarmDataContext.jsx`, `src/context/AIConversationContext.jsx`.

**`src/data/`:**

- Purpose: Hold navigation/static presentation assets and retained legacy fixture modules.
- Contains: Navigation definitions, farm image lookup, and older dashboard/chat/field/localized content modules.
- Key files: `src/data/navigation.js`, `src/data/images.js`; `src/data/dashboard.js`, `src/data/chat.js`, and `src/data/fields.js` are not live data authorities.

**`src/features/`:**

- Purpose: Hold feature-specific client logic that is not a generic context or component.
- Contains: The current farmer-keyed browser `localStorage` finance ledger.
- Key files: `src/features/financeStore.js`.

**`src/db/`:**

- Purpose: Retain an IndexedDB prototype for finance, soil logs, and weather cache.
- Contains: Database initialization, demo seeding, CRUD, and localStorage fallback.
- Key files: `src/db/localDatabase.js`; no current application module imports this singleton.

**`src/i18n/` and `src/hooks/`:**

- Purpose: Configure UI localization and expose the selected language.
- Contains: i18next setup, English/Hindi/Marathi JSON resources, and `LanguageProvider`/`useLanguage`.
- Key files: `src/i18n/index.js`, `src/i18n/en.json`, `src/i18n/hi.json`, `src/i18n/mr.json`, `src/hooks/useLanguage.jsx`.

**`src/pages/`:**

- Purpose: Implement each navigable farmer workflow.
- Contains: Dashboard, fields/detail/map, crop guide, soil, weather, irrigation, pest/disease upload, market, schemes, finance, machinery, AI/voice, reports, and settings.
- Key files: `src/pages/Dashboard.jsx`, `src/pages/CorePages.jsx`, `src/pages/FieldTools.jsx`, `src/pages/AIAssistant.jsx`, `src/pages/FarmFinance.jsx`.

**`desktop/`:**

- Purpose: Add a privileged local host around the web renderer without exposing Node or the Codex child process to React.
- Contains: Electron lifecycle, sandboxed IPC contract, backend health/media proxy, and private Codex app-server client.
- Key files: `desktop/main.cjs`, `desktop/preload.cjs`, `desktop/codex-harness.cjs`, `desktop/README.md`.

**`agent/`:**

- Purpose: Translate stable, task-oriented KisanSathi MCP calls into backend HTTP operations.
- Contains: Python package, 47 read/write tool registrations, backend client, result envelope, tool implementations, tests, skill guidance, and example configuration.
- Key files: `agent/src/kisansathi_agent/server.py`, `agent/src/kisansathi_agent/tools.py`, `agent/src/kisansathi_agent/backend_client.py`, `agent/src/kisansathi_agent/result.py`, `agent/pyproject.toml`.

**`backend/app/core/`:**

- Purpose: Hold process-wide backend infrastructure configuration.
- Contains: Pydantic settings and Mongo/Beanie initialization.
- Key files: `backend/app/core/config.py`, `backend/app/core/database.py`.

**`backend/app/farm_state/`:**

- Purpose: Implement the current farmer-scoped digital-twin persistence and deterministic soil/irrigation screening.
- Contains: SQLite schema/store, request dependency, idempotency utilities, and farm rules.
- Key files: `backend/app/farm_state/store.py`, `backend/app/farm_state/dependencies.py`, `backend/app/farm_state/rules.py`.

**`backend/app/models/`:**

- Purpose: Define shared MongoDB catalog and ingestion documents.
- Contains: Beanie models for farmer, crop, disease, fertilizer, government scheme, market price, MSP, seed, machinery rental, and ingestion run.
- Key files: `backend/app/models/crop.py`, `backend/app/models/market_price.py`, `backend/app/models/msp.py`, `backend/app/models/ingestion_run.py`.

**`backend/app/schemas/`:**

- Purpose: Define public HTTP contracts independently from storage implementation.
- Contains: Domain create/update/response DTOs and the complete farm-state/provider response family.
- Key files: `backend/app/schemas/farm_state.py`, `backend/app/schemas/market_price.py`, `backend/app/schemas/ingestion.py`.

**`backend/app/routers/`:**

- Purpose: Expose HTTP transport endpoints by domain.
- Contains: Farm-state, assistant/voice/diagnosis, weather, ingestion, and MongoDB reference/catalog endpoints.
- Key files: `backend/app/routers/farm_state.py`, `backend/app/routers/assistants.py`, `backend/app/routers/weather.py`, `backend/app/routers/ingestion.py`, `backend/app/routers/market_price.py`.

**`backend/app/services/`:**

- Purpose: Hold reusable provider/domain policies behind routers.
- Contains: Weather and Sarvam adapters, market net-realisation calculation, and seed/fertilizer/scheme mutators.
- Key files: `backend/app/services/weather.py`, `backend/app/services/sarvam.py`, `backend/app/services/market.py`, `backend/app/services/seed_mutator.py`.

**`backend/app/scraping/`:**

- Purpose: Own universal reference-data acquisition and normalization.
- Contains: data.gov.in/PIB source adapters, HTML table parsing, stable source IDs, bulk upsert orchestration, and a CLI entry point.
- Key files: `backend/app/scraping/sources.py`, `backend/app/scraping/service.py`, `backend/app/scraping/__main__.py`.

**`backend/data/`:**

- Purpose: Store runtime farmer SQLite databases and uploaded diagnosis images.
- Contains: `backend/data/farm_state/<farmer>.sqlite3` and `backend/data/farm_uploads/<farmer>/...`.
- Key files: `backend/data/farm_state/demo.sqlite3`; contents are runtime state, not source definitions.

**`backend/n8n/` and `backend/scripts/`:**

- Purpose: Configure and bootstrap universal-data synchronization outside the request application.
- Contains: n8n workflow JSON and a PowerShell setup script.
- Key files: `backend/n8n/universal-data-sync.json`, `backend/scripts/setup_universal_data.ps1`, `backend/docker-compose.universal-data.yml`.

**`backend/tests/`:**

- Purpose: Verify farm-state behavior, market rules, Sarvam adapters, and universal-data parsing.
- Contains: Pytest modules.
- Key files: `backend/tests/test_farm_state.py`, `backend/tests/test_market_rules.py`, `backend/tests/test_sarvam.py`, `backend/tests/test_universal_data_sources.py`.

**`codex/plugins/kisansathi/`:**

- Purpose: Package the farm skill and Python MCP launcher for the Codex plugin model.
- Contains: Plugin manifest, MCP server declaration, skill text, launcher, and usage README.
- Key files: `codex/plugins/kisansathi/.codex-plugin/plugin.json`, `codex/plugins/kisansathi/.mcp.json`, `codex/plugins/kisansathi/run_server.py`, `codex/plugins/kisansathi/skills/kisansathi/SKILL.md`.

**`codex/codex-rs/`:**

- Purpose: Provide the full general-purpose Codex runtime that the desktop harness launches.
- Contains: More than one hundred Rust workspace members for CLI, app server/protocol/transport, core agent behavior, tools, MCP, plugins, models, state, sandboxing, TUI, and supporting infrastructure.
- Key files: `codex/codex-rs/Cargo.toml`, `codex/codex-rs/cli/src/main.rs`, `codex/codex-rs/app-server/src/lib.rs`, `codex/codex-rs/core/src/lib.rs`, `codex/codex-rs/core/src/tools/registry.rs`, `codex/codex-rs/plugin/src/lib.rs`.

**`.planning/`:**

- Purpose: Hold GSD project definition, requirements, roadmap/state, research, notes, and generated codebase maps.
- Contains: Planning artifacts only; it is not loaded by production application code.
- Key files: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`, `.planning/codebase/ARCHITECTURE.md`.

## Key File Locations

**Entry Points:**

- `index.html`: Vite HTML shell.
- `src/main.jsx`: React DOM bootstrap.
- `src/App.jsx`: Provider and router composition.
- `src/routes/index.jsx`: Web/hash route tree.
- `desktop/main.cjs`: Electron main process selected by `package.json`.
- `desktop/codex-harness.cjs`: Child Codex app-server lifecycle and JSONL client.
- `backend/app/main.py`: FastAPI ASGI application.
- `backend/app/scraping/__main__.py`: Universal-data ingestion CLI.
- `agent/src/kisansathi_agent/__main__.py`: Python MCP stdio entry.
- `codex/plugins/kisansathi/run_server.py`: Plugin-owned MCP launcher.
- `codex/codex-rs/cli/src/main.rs`: Rust Codex CLI/app-server entry.

**Configuration:**

- `package.json`: Vite, Electron, lint, build, and test commands.
- `vite.config.js`: React/Tailwind plugins and relative production asset base.
- `vitest.config.js`: Renderer unit-test environment/configuration.
- `eslint.config.js`: Frontend lint rules.
- `backend/requirements.txt`: FastAPI/Beanie/provider/test dependencies.
- `backend/app/core/config.py`: Backend environment-backed settings; environment values are never stored in these maps.
- `backend/pytest.ini`: Backend pytest configuration.
- `agent/pyproject.toml`: MCP adapter packaging, runtime dependencies, and development extras.
- `agent/config/codex.mcp.example.toml`: Example standalone MCP configuration.
- `codex/plugins/kisansathi/.codex-plugin/plugin.json`: Plugin identity/interface/skill declaration.
- `codex/plugins/kisansathi/.mcp.json`: Plugin MCP command declaration.
- `codex/codex-rs/Cargo.toml`: Codex Rust workspace membership and shared dependencies.

**Core Logic:**

- `backend/app/farm_state/store.py`: Digital-twin SQLite schema, farmer file selection, idempotency, and query wrapper.
- `backend/app/routers/farm_state.py`: Farmer profile, field, crop stage, soil, sensor, irrigation, reminder, alert, dashboard, and report API.
- `backend/app/farm_state/rules.py`: Soil and irrigation screening rules.
- `backend/app/routers/assistants.py`: Diagnosis/media persistence and Sarvam/deprecated-advisor endpoints.
- `backend/app/services/weather.py`: Open-Meteo fetch/normalization.
- `backend/app/scraping/service.py`: Government-reference ingestion orchestration.
- `agent/src/kisansathi_agent/server.py`: Model-visible farm tool registry and read/write annotations.
- `agent/src/kisansathi_agent/tools.py`: Tool-to-HTTP mappings and local profit calculation.
- `desktop/codex-harness.cjs`: Codex thread/turn/tool-event integration.
- `src/context/AIConversationContext.jsx`: Renderer-side conversation, media, approval, translation, and speech workflow.

**Testing:**

- `src/components/features/ai/ConversationView.test.jsx`: Chat component behavior.
- `tests/desktop/codex-harness.test.cjs`: JSONL session/turn/approval/recovery behavior.
- `tests/desktop/preload-contract.test.cjs`: Renderer exposure and BrowserWindow security contract.
- `agent/tests/test_backend_client.py`: MCP HTTP-boundary behavior.
- `agent/tests/test_tools.py`: Tool mappings/envelopes/safety behavior.
- `backend/tests/test_farm_state.py`: SQLite farm-state API behavior.
- `backend/tests/test_market_rules.py`: Market calculations.
- `backend/tests/test_sarvam.py`: Sarvam adapter behavior.
- `backend/tests/test_universal_data_sources.py`: Government-data parsing/normalization.
- `codex/codex-rs/*/tests/`: Upstream/fork Rust coverage; keep it separate from KisanSathi application test scope.

## Naming Conventions

**Files:**

- React components and pages use PascalCase `.jsx`: `src/pages/MyFields.jsx`, `src/components/layout/AppShell.jsx`.
- React hooks use the `use` prefix: `src/hooks/useLanguage.jsx`.
- Frontend transport/data/feature modules use camelCase `.js`: `src/api/farmStateApi.js`, `src/features/financeStore.js`.
- Electron/CommonJS modules use kebab-case or role names with `.cjs`: `desktop/codex-harness.cjs`, `desktop/preload.cjs`.
- Python modules use lowercase snake_case: `backend/app/routers/market_price.py`, `agent/src/kisansathi_agent/backend_client.py`.
- Backend reference domains repeat the basename across model/schema/router layers: `backend/app/models/msp.py`, `backend/app/schemas/msp.py`, `backend/app/routers/msp.py`.
- Rust crates use kebab-case directories and snake_case source modules: `codex/codex-rs/app-server/`, `codex/codex-rs/core/src/codex_thread.rs`.
- Tests match their runtime convention: `*.test.jsx`, `*.test.cjs`, or `test_*.py`.

**Directories:**

- Frontend groups primarily by technical role (`api`, `components`, `context`, `pages`) with small feature-specific seams under `features/`.
- Backend groups by application layer (`models`, `schemas`, `routers`, `services`) and isolates the operational store/domain under `farm_state/`.
- Python package code follows `src/<package_name>/` layout under `agent/`.
- Codex application extensions live under `codex/plugins/<plugin_name>/`; shared farm adapter code remains under `agent/`.

## Where to Add New Code

**New farmer-facing feature:**

- Route page: `src/pages/<FeatureName>.jsx`.
- Route registration: `src/routes/index.jsx`.
- Navigation entry: `src/data/navigation.js` when globally navigable.
- Shared feature UI: `src/components/features/<feature>/` for multiple components; colocate a one-off component with its page.
- Backend calls: add named methods to `src/api/farmStateApi.js` or `src/api/referenceApi.js`; do not place raw `fetch()` calls in pages except provider-specific map search in `src/components/fields/LocationPicker.jsx`.
- Shared state: extend `src/context/FarmDataContext.jsx` only for cross-route farm state; keep route-local state in the route component.
- UI translations: update all of `src/i18n/en.json`, `src/i18n/hi.json`, and `src/i18n/mr.json` through the current i18next path.
- Tests: colocate renderer tests as `*.test.jsx` near the component, matching `src/components/features/ai/ConversationView.test.jsx`.

**New farmer operational entity:**

- Schema/storage: add the table/index/migration behavior in `backend/app/farm_state/store.py`.
- HTTP DTO: add Pydantic types to `backend/app/schemas/farm_state.py` or a focused schema module when the domain becomes large.
- HTTP transport: add handlers to `backend/app/routers/farm_state.py` or a focused `/v1` router and register it in `backend/app/main.py`.
- Domain decisions: add deterministic rules in `backend/app/farm_state/` or `backend/app/services/`, not in the router or MCP tool.
- Tests: extend `backend/tests/test_farm_state.py` or add `backend/tests/test_<domain>.py`.
- Preserve farmer selection through `backend/app/farm_state/dependencies.py`; never accept farmer ID as a model-controlled MCP tool argument.

**New shared reference/catalog domain:**

- Persistence: `backend/app/models/<domain>.py`.
- HTTP contract: `backend/app/schemas/<domain>.py`.
- Router: `backend/app/routers/<domain>.py`.
- Registration: `backend/app/core/database.py` and `backend/app/main.py`.
- Source ingestion: `backend/app/scraping/sources.py` for source parsing and `backend/app/scraping/service.py` for normalized upsert orchestration.
- Tests: `backend/tests/test_<domain>.py` and/or `backend/tests/test_universal_data_sources.py`.
- Required backend memory updates: `backend/ChangeLog.md`, plus `backend/Decisions.md` and `backend/Flow.md` when applicable, per `backend/AGENTS.md`.

**New KisanSathi agent tool:**

- Backend capability first: expose a typed endpoint under `backend/app/routers/` backed by storage/service logic.
- Tool implementation: add one method to `agent/src/kisansathi_agent/tools.py`.
- Model-visible registration and safety metadata: add one registration to `agent/src/kisansathi_agent/server.py` with `_READ_ONLY` or `_WRITE`.
- Result shape: return helpers from `agent/src/kisansathi_agent/result.py`; preserve source, freshness, warnings, request ID, bounded data, and write action hints.
- Tests: add endpoint/mapping/error/idempotency cases under `agent/tests/test_tools.py` and `agent/tests/test_backend_client.py`.
- Plugin guidance: update `codex/plugins/kisansathi/skills/kisansathi/SKILL.md` only when the behavioral safety contract changes.
- Do not add native farm business logic under `codex/codex-rs/core/src/tools/handlers/`; the current integration boundary is MCP.

**New desktop/Codex interaction:**

- Privileged operation: implement in `desktop/main.cjs`.
- Minimal renderer surface: expose through `desktop/preload.cjs` and update `tests/desktop/preload-contract.test.cjs`.
- App-server protocol/session behavior: implement in `desktop/codex-harness.cjs` and test in `tests/desktop/codex-harness.test.cjs`.
- Renderer consumption: coordinate through `src/context/AIConversationContext.jsx`, not direct Node access.
- Modify `codex/codex-rs/` only when the existing app-server/MCP/plugin protocol cannot express the capability and add targeted Rust tests in the owning crate.

**New external provider:**

- Settings: declare names/timeouts in `backend/app/core/config.py` without committing values.
- Provider adapter: `backend/app/services/<provider_or_domain>.py`.
- Public transport: a typed backend router/schema contract under `backend/app/routers/` and `backend/app/schemas/`.
- Provider errors: map to explicit unavailable/degraded responses; never silently replace missing agricultural data with fixtures.
- Tests: use injected/mocked transport in a focused `backend/tests/test_<provider>.py`.

**Utilities:**

- Frontend transport utilities: `src/api/`.
- Frontend presentational state components: `src/components/feedback/`.
- Backend cross-router provider/domain utilities: `backend/app/services/`.
- Farmer-store-specific helpers: `backend/app/farm_state/`.
- MCP transport/result utilities: `agent/src/kisansathi_agent/backend_client.py` and `agent/src/kisansathi_agent/result.py`.

## Special Directories

**`codex/`:**

- Purpose: Full forked upstream Codex source plus the local KisanSathi plugin.
- Generated: No (generated schemas/vendor/build outputs exist inside the wider tree).
- Committed: Yes for source; `codex/codex-rs/target/` is a build artifact and should not be treated as source.

**`backend/data/`:**

- Purpose: Local runtime farmer databases and uploaded diagnosis media.
- Generated: Yes.
- Committed: Runtime artifacts are present in the worktree; do not treat them as schema definitions or test fixtures unless explicitly designated.

**`dist/`:**

- Purpose: Production renderer bundle loaded by Electron.
- Generated: Yes, by `npm run build`.
- Committed: Present in the current worktree; edit `src/`, never hand-edit `dist/`.

**`node_modules/`:**

- Purpose: Installed npm dependency tree.
- Generated: Yes.
- Committed: No; never inspect it as application architecture or edit it.

**`.planning/`:**

- Purpose: GSD planning, research, state, notes, and generated repository maps.
- Generated: Mixed; codebase maps/state are workflow-generated, project requirements/roadmap are planning artifacts.
- Committed: Workflow dependent; current files are part of the working project context, not runtime code.

**`codex/plugins/kisansathi/`:**

- Purpose: Local Codex plugin packaging for the shared `agent/` implementation.
- Generated: No.
- Committed: Currently untracked in the live worktree; it is nevertheless the active path hard-coded by `desktop/main.cjs`.

**`src/data/` and `src/services/hostedCatalogService.js`:**

- Purpose: Navigation/assets plus retained fixture/prototype data.
- Generated: No.
- Committed: Yes/current; do not use the hardcoded catalog modules as authoritative farm/reference state.

**`.pytest_cache/`, `.playwright-cli/`, and `codex/codex-rs/target/`:**

- Purpose: Local test/browser/build caches.
- Generated: Yes.
- Committed: No; exclude from architecture and production changes.

---

*Structure analysis: 2026-08-20*
