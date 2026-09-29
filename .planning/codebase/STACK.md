# Technology Stack

**Analysis Date:** 2026-08-20

## Scope and Evidence Boundary

- This map covers the application root (`package.json`, `src/`, `desktop/`), the Python backend (`backend/`), the MCP adapter (`agent/`), and the vendored Codex fork (`codex/`).
- Treat executable source and manifests as authoritative. Product claims in `README.md`, `backend/docs/PRD.md`, `IMPLEMENTATION_AUDIT.md`, and the merge-plan Markdown files are documentation, not implementation evidence.
- The current farming integration into the Codex fork is the untracked Python plugin launcher at `codex/plugins/kisansathi/run_server.py`; no KisanSathi-specific Rust crate or Rust handler is present in `codex/codex-rs/`.
- Generated/local directories such as `dist/`, `node_modules/`, `.pytest_cache/`, and the SQLite/upload data under `backend/data/` are runtime artifacts, not source-of-truth implementations.

## Languages

**Primary:**
- JavaScript/JSX (ECMAScript modules) - React renderer in `src/`, Vite configuration in `vite.config.js`, and CommonJS Electron host files in `desktop/`.
- Python 3.11+ for the MCP package - declared by `agent/pyproject.toml`; the installed audit runtime is Python 3.12.10.
- Python 3 for the FastAPI service - application code lives in `backend/app/` and dependencies are pinned in `backend/requirements.txt`; the backend manifest does not declare a minimum Python version.
- Rust 2024 edition with toolchain 1.95.0 - the Codex workspace is declared in `codex/codex-rs/Cargo.toml` and `codex/codex-rs/rust-toolchain.toml`.

**Secondary:**
- SQL (SQLite dialect) - per-farmer schema and queries are embedded in `backend/app/farm_state/store.py`.
- CSS/Tailwind CSS - global renderer styling is in `src/index.css`; Tailwind is registered through `vite.config.js`.
- JSON - translations in `src/i18n/en.json`, `src/i18n/hi.json`, and `src/i18n/mr.json`; n8n workflow in `backend/n8n/universal-data-sync.json`; npm lock data in `package-lock.json`.
- TOML - Rust workspace/crate manifests under `codex/codex-rs/`, Codex plugin example configuration at `agent/config/codex.mcp.example.toml`, and agent packaging at `agent/pyproject.toml`.
- YAML - local MongoDB/n8n infrastructure at `backend/docker-compose.universal-data.yml`; upstream Codex automation and configuration remain under `codex/`.
- PowerShell/shell/Python build scripts - application ingestion setup at `backend/scripts/setup_universal_data.ps1` and upstream build tooling under `codex/scripts/` and `codex/justfile`.

## Runtime

**Environment:**
- Browser/Vite renderer - `src/main.jsx` mounts the React application defined by `src/App.jsx`.
- Electron 43.4.0 - `desktop/main.cjs` loads the Vite dev server or `dist/index.html` and exposes a sandboxed IPC bridge from `desktop/preload.cjs`.
- Node.js - the application root does not declare an engine in `package.json`; the audit host has Node 20.20.2. The vendored Codex root requires Node `>=22` in `codex/package.json`, so the audit host does not satisfy that nested workspace requirement.
- Python/Uvicorn - `backend/app/main.py` is the ASGI entry point and `uvicorn==0.52.3` is pinned in `backend/requirements.txt`.
- Python stdio MCP server - `agent/src/kisansathi_agent/__main__.py` starts the FastMCP server configured by `agent/src/kisansathi_agent/server.py`.
- Native Codex app-server - `desktop/codex-harness.cjs` spawns `codex app-server --stdio`; it expects an installed/signed-in `codex` binary and does not compile `codex/codex-rs/` as part of the app build.
- MongoDB 8.0 and n8n 1.123.72 - local container versions are pinned in `backend/docker-compose.universal-data.yml`.

**Package Manager:**
- npm 10.8.2 on the audit host - application dependencies are locked by npm lockfile v3 at `package-lock.json`.
- pip/setuptools - backend pins are in `backend/requirements.txt`; the installable agent uses setuptools in `agent/pyproject.toml`. Neither Python component has a resolved lockfile.
- Cargo - `codex/codex-rs/Cargo.lock` is present for the Rust workspace; the declared toolchain is 1.95.0 in `codex/codex-rs/rust-toolchain.toml` while the audit host has Rust/Cargo 1.97.1.
- pnpm 10.33.0 is declared by `codex/package.json` and lockfile v9 is present at `codex/pnpm-lock.yaml`; the audit host has pnpm 11.19.0, outside the declared package-manager version.
- Bazel/Bzlmod and Nix are additional upstream Codex build paths through `codex/MODULE.bazel`, `codex/BUILD.bazel`, `codex/flake.nix`, and `codex/justfile`.

## Frameworks

**Core:**
- React 19.2.8 and React DOM 19.2.8 - renderer entry and component tree in `src/main.jsx`, `src/App.jsx`, `src/pages/`, and `src/components/`.
- React Router DOM 7.18.2 - browser routing and Electron hash routing are selected in `src/routes/index.jsx`.
- Electron 43.4.0 - desktop process isolation, IPC, local image handling, backend proxying, and Codex process management in `desktop/main.cjs`, `desktop/preload.cjs`, and `desktop/codex-harness.cjs`.
- FastAPI 0.141.1 / Starlette 1.6.0 - REST application and routers in `backend/app/main.py` and `backend/app/routers/`.
- Pydantic 2.13.4 / pydantic-settings 2.15.0 - request/response contracts under `backend/app/schemas/` and environment configuration in `backend/app/core/config.py`.
- Beanie 2.0.0, Motor 3.7.1, and PyMongo 4.17.0 - MongoDB reference-data models in `backend/app/models/`, initialization in `backend/app/core/database.py`, and bulk ingestion in `backend/app/scraping/service.py`.
- MCP Python SDK `>=1.29,<1.30` with FastMCP - farmer-scoped tool registration in `agent/src/kisansathi_agent/server.py`.
- Codex Rust workspace - `codex/codex-rs/Cargo.toml` contains the CLI, TUI, app-server, core, MCP, plugin, model-provider, sandbox, state, thread-store, and extension crates; the application currently consumes the installed app-server through `desktop/codex-harness.cjs`.

**Testing:**
- Vitest 4.1.11 with jsdom 29.1.1 and Testing Library 16.3.2 - renderer test configuration in `vitest.config.js` and current component test at `src/components/features/ai/ConversationView.test.jsx`.
- Node built-in test runner - Electron harness/IPC contracts in `tests/desktop/codex-harness.test.cjs` and `tests/desktop/preload-contract.test.cjs` run through `package.json`.
- pytest 8+ for the agent - optional dev dependency and test discovery in `agent/pyproject.toml`, with tests in `agent/tests/`.
- pytest for the backend - discovery in `backend/pytest.ini` and tests in `backend/tests/`; pytest is not pinned in `backend/requirements.txt`, so it must be installed separately.
- Rust `just test`, `cargo-insta`, `wiremock`, and `pretty_assertions` are upstream Codex test conventions and dependencies documented by `codex/AGENTS.md` and crate manifests under `codex/codex-rs/`.

**Build/Dev:**
- Vite 8.2.1 and `@vitejs/plugin-react` 6.0.5 - root dev server/build commands in `package.json` and build configuration in `vite.config.js`.
- Tailwind CSS 4.3.3 with `@tailwindcss/vite` 4.3.3 - renderer CSS pipeline configured in `vite.config.js` and used from `src/index.css`.
- ESLint 10.8.1 with React Hooks/Refresh plugins - root lint command in `package.json` and rules in `eslint.config.js`.
- Concurrently 9.2.4, wait-on 9.0.1, and cross-env 10.1.0 - Electron/Vite orchestration in the `desktop:dev` script in `package.json`.
- Uvicorn 0.52.3 with httptools, watchfiles, websockets, and AnyIO support - backend serving dependencies in `backend/requirements.txt`.
- just 1.58.0, Cargo, Bazel/Bzlmod, pnpm, and Nix - upstream Codex developer workflows are rooted at `codex/justfile`, `codex/MODULE.bazel`, `codex/package.json`, and `codex/flake.nix`.

## Key Dependencies

**Critical:**
- `react`, `react-dom`, and `react-router-dom` - all farmer-facing screens and navigation under `src/` depend on them; versions are declared in `package.json` and resolved in `package-lock.json`.
- `electron` - the only implemented bridge from the farmer UI to Codex app-server and Sarvam/backend voice endpoints is in `desktop/`.
- `fastapi`, `pydantic`, `beanie`, `motor`, and `pymongo` - the central reference API and MongoDB persistence are implemented in `backend/app/` and pinned by `backend/requirements.txt`.
- Python `sqlite3` standard library - per-farmer operational state, migrations, idempotency records, weather cache, image metadata, and reports are implemented by `backend/app/farm_state/store.py`.
- `mcp`, `httpx`, and `pydantic` - the Python MCP adapter validates launcher configuration and proxies typed tool calls to FastAPI through `agent/src/kisansathi_agent/`.
- Rust `tokio`, `reqwest`, `serde`, `rmcp`, `sqlx`, `ratatui`, `clap`, and `tracing` - core async, HTTP, protocol, persistence, TUI, CLI, and telemetry building blocks are declared centrally in `codex/codex-rs/Cargo.toml`.

**Infrastructure:**
- Leaflet 1.9.4 and React Leaflet 5.0.0 - OpenStreetMap field selection/search UI in `src/components/fields/LocationPicker.jsx`.
- i18next 26.3.6 and react-i18next 17.0.11 - local English, Hindi, and Marathi resources configured by `src/i18n/index.js` and surfaced through `src/hooks/useLanguage.jsx`.
- Framer Motion 13.1.0, Lucide React 1.31.0, and Recharts 3.10.1 - UI motion, icons, and charts used throughout `src/components/` and `src/pages/`.
- Browser IndexedDB/localStorage - a separate prototype finance/soil/cache layer exists in `src/db/localDatabase.js`; current finance state instead uses farmer-keyed localStorage in `src/features/financeStore.js`.
- Docker Compose - local MongoDB/n8n services and persistent volumes are defined in `backend/docker-compose.universal-data.yml`; the FastAPI backend and Electron app are not containerized there.

## Configuration

**Environment:**
- Backend settings are centralized in `backend/app/core/config.py`; it reads `backend/.env` at runtime. The file exists, but its contents were not inspected.
- Mongo/reference data uses `MONGODB_URL`, `DATABASE_NAME`, and `MONGODB_CONNECT_TIMEOUT_MS` from `backend/app/core/config.py`.
- Farmer SQLite/uploads use `FARM_STATE_DB_DIR` and `FARM_STATE_UPLOAD_DIR` from `backend/app/core/config.py`; the current local data roots are `backend/data/farm_state/` and `backend/data/farm_uploads/`.
- Weather uses `WEATHER_PROVIDER`, `WEATHER_TIMEOUT_SECONDS`, and `WEATHER_CACHE_SECONDS` from `backend/app/core/config.py`.
- Sarvam voice/translation uses `SARVAM_API_KEY`, `SARVAM_BASE_URL`, model/speaker/codec options, and `SARVAM_TIMEOUT_SECONDS` from `backend/app/core/config.py`.
- Official ingestion uses `DATA_GOV_IN_API_KEY`, `SCRAPER_WEBHOOK_TOKEN`, MSP source URLs/year, and universal-data paging/timeouts from `backend/app/core/config.py`.
- Frontend API routing and demo identity use `VITE_FARM_STATE_API_URL`, `VITE_REFERENCE_API_URL`, and `VITE_DEMO_FARMER_ID` in `src/api/client.js`.
- Desktop/Codex launch uses `KISANSATHI_BACKEND_URL`, `KISANSATHI_FARMER_ID`, `KISANSATHI_PYTHON`, `CODEX_BINARY`, and `ELECTRON_RENDERER_URL` in `desktop/main.cjs` and `desktop/codex-harness.cjs`.
- MCP adapter limits use `KISANSATHI_BACKEND_URL`, `KISANSATHI_FARMER_ID`, `KISANSATHI_TIMEOUT_SECONDS`, and `KISANSATHI_MAX_RESPONSE_BYTES` in `agent/src/kisansathi_agent/config.py`.

**Build:**
- Root renderer/desktop scripts are in `package.json`; Vite, Vitest, and ESLint configuration are `vite.config.js`, `vitest.config.js`, and `eslint.config.js`.
- Backend dependency/test configuration is `backend/requirements.txt` and `backend/pytest.ini`; no backend Dockerfile or application launch script is present.
- Agent packaging and console entry point are defined in `agent/pyproject.toml`; example Codex MCP configuration is `agent/config/codex.mcp.example.toml`.
- Codex build configuration is split across `codex/codex-rs/Cargo.toml`, `codex/codex-rs/Cargo.lock`, `codex/justfile`, `codex/MODULE.bazel`, `codex/BUILD.bazel`, `codex/package.json`, `codex/pnpm-lock.yaml`, and `codex/flake.nix`.

## Platform Requirements

**Development:**
- Use Node/npm for the root UI/desktop commands in `package.json`; the currently installed dependency tree is represented by `package-lock.json`.
- Use Python 3.11+ for the agent because `agent/pyproject.toml` enforces it; use a Python version compatible with pinned FastAPI/Pydantic packages in `backend/requirements.txt` for the backend.
- Run MongoDB for reference endpoints initialized by `backend/app/core/database.py`; the backend intentionally starts in degraded mode if MongoDB is unavailable, as implemented in `backend/app/main.py`.
- Install the local MCP package from `agent/pyproject.toml`, run the FastAPI backend, and provide an installed authenticated Codex executable for the Electron workflow in `desktop/codex-harness.cjs`.
- Use Docker when running the optional local MongoDB/n8n stack in `backend/docker-compose.universal-data.yml`.
- Use the exact Rust 1.95.0 toolchain, Node `>=22`, and pnpm 10.33.0 declared in `codex/codex-rs/rust-toolchain.toml` and `codex/package.json` when building the nested Codex fork.

**Production:**
- Deployment target is not detected for the application: there is no root hosting manifest, backend Dockerfile, Electron packager configuration, or application CI workflow alongside `package.json` and `backend/`.
- The current operational shape is a local Electron app (`desktop/`) plus local Codex binary (`desktop/codex-harness.cjs`), local FastAPI service (`backend/app/main.py`), local per-farmer SQLite files (`backend/app/farm_state/store.py`), and a reachable MongoDB (`backend/app/core/database.py`).
- `npm run build` creates the static renderer under `dist/`, but `package.json` has no installer/signing/auto-update pipeline for Electron.
- The backend has no production ASGI process manager, TLS termination, authentication middleware, backup job, or cloud infrastructure definition in `backend/`; these are deployment gaps, not implicit framework features.

---

*Stack analysis: 2026-08-20*
