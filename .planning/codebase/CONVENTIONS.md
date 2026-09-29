# Coding Conventions

**Analysis Date:** 2026-08-20

## Naming Patterns

**Files:**
- Use PascalCase `.jsx` filenames for React pages and components: `src/pages/MyFields.jsx`, `src/pages/FarmFinance.jsx`, and `src/components/features/ai/ConversationView.jsx`.
- Use camelCase `.js` filenames for frontend services, stores, constants, and contexts: `src/services/hostedCatalogService.js`, `src/features/financeStore.js`, and `src/context/AIConversationContext.jsx`.
- Use lowercase snake_case for Python modules: `backend/app/routers/farm_state.py`, `backend/app/services/seed_mutator.py`, and `agent/src/kisansathi_agent/backend_client.py`.
- Keep Mongo reference-data domains aligned across `backend/app/models/<domain>.py`, `backend/app/schemas/<domain>.py`, and `backend/app/routers/<domain>.py`; examples are `backend/app/models/market_price.py`, `backend/app/schemas/market_price.py`, and `backend/app/routers/market_price.py`.
- Use `.test.jsx` for colocated Vitest tests (`src/components/features/ai/ConversationView.test.jsx`), `test_*.py` for pytest (`backend/tests/test_farm_state.py`, `agent/tests/test_tools.py`), and `*.test.cjs` for Node tests (`tests/desktop/codex-harness.test.cjs`).
- Treat `codex/` as an independently governed upstream source tree. Follow `codex/AGENTS.md` and crate-local conventions for files under `codex/codex-rs/`; do not apply frontend/backend conventions there.

**Functions:**
- Use camelCase for JavaScript functions and hooks: `createAppRouter` in `src/routes/index.jsx`, `useFarmData` in `src/context/FarmDataContext.jsx`, and `normaliseNotification` in `desktop/codex-harness.cjs`.
- Prefix React hooks with `use` and context providers with `<Domain>Provider`: `useLanguage` in `src/hooks/useLanguage.jsx`, `FarmDataProvider` in `src/context/FarmDataContext.jsx`, and `AIConversationProvider` in `src/context/AIConversationContext.jsx`.
- Use snake_case for Python functions and route handlers: `get_irrigation_plan` in `backend/app/routers/farm_state.py` and `get_weather_for_field` in `agent/src/kisansathi_agent/tools.py`.
- Prefix module-private Python conversion, parsing, and repository helpers with `_`: `_field_response` and `_parse_datetime` in `backend/app/routers/farm_state.py`, `_market_record` in `backend/app/scraping/sources.py`.
- Use action-oriented names for MCP writes and query-oriented names for reads. Existing examples are `record_irrigation_event`, `update_profile`, `get_soil_health`, and `list_fields` in `agent/src/kisansathi_agent/tools.py`.

**Variables:**
- Use camelCase for JavaScript state, props, and locals (`selectedFieldId`, `pendingAction`, `harnessStatus`) in `src/context/AIConversationContext.jsx`.
- Use snake_case for Python locals and parameters (`farmer_state`, `idempotency_key`, `rain_probability`) in `backend/app/routers/market_price.py` and `backend/app/routers/farm_state.py`.
- Use UPPER_SNAKE_CASE for module constants: `DB_NAME` and `DB_VERSION` in `src/db/localDatabase.js`, `_READ_ONLY` and `_WRITE` in `agent/src/kisansathi_agent/server.py`, and `SCHEMA` in `backend/app/farm_state/store.py`.

**Types:**
- Name Pydantic schemas as `<Domain>Create`, `<Domain>Update`, `<Domain>Response`, or a precise operation result; see `backend/app/schemas/farm_state.py` and `backend/app/schemas/market_price.py`.
- Name Beanie documents as singular PascalCase nouns (`Crop`, `MSP`, `IngestionRun`) under `backend/app/models/`.
- Use dataclasses for small internal immutable results where serialization is not the primary role; `MoistureRuleResult` in `backend/app/farm_state/rules.py` is the current pattern.
- Use built-in generics (`list[str]`, `dict[str, Any]`) in new Python 3.11+ code. Some older reference modules still use `typing.List` and `typing.Optional`, such as `backend/app/schemas/gov_scheme.py`; preserve local style during focused changes and normalize only in a dedicated cleanup.

## Code Style

**Formatting:**
- Frontend JavaScript generally uses two spaces, single quotes, trailing semicolons in newer files, and default exports for primary components. Match the file-local style because no Prettier or Biome configuration exists in the root.
- Keep JSX readable across multiple lines. Do not copy the current compressed one-line style found in `src/pages/Dashboard.jsx`, `src/pages/FieldDetail.jsx`, `src/pages/CorePages.jsx`, and `src/pages/MachineryRentals.jsx`; these files contain individual lines between roughly 3,200 and 4,625 characters and should be expanded when materially edited.
- Python uses four-space indentation, type annotations on public service/tool functions, and blank lines between import groups and definitions. Representative files are `agent/src/kisansathi_agent/backend_client.py` and `backend/app/services/sarvam.py`.
- No backend formatter is configured in `backend/requirements.txt` or `backend/pytest.ini`. Do not claim Black/Ruff enforcement; match adjacent code and keep changes small.
- Rust formatting and lint workflow under `codex/codex-rs/` is controlled by `codex/AGENTS.md`: run its prescribed `just fmt`, scoped `just fix`, and `just test -p <crate>` commands for Rust changes.

**Linting:**
- Run `npm run lint` for root React/Electron JavaScript. `eslint.config.js` applies ESLint recommended, React Hooks, and React Refresh rules and intentionally ignores `dist` and the separate `codex` tree.
- The current ESLint scope is `**/*.{js,jsx}`; CommonJS files in `desktop/*.cjs` and `tests/desktop/*.cjs` are not linted by `eslint.config.js`.
- No Python linter, formatter, type checker, or import sorter is configured for `backend/` or `agent/`. Use pytest as behavior verification, but do not treat it as a static-quality gate.

## Import Organization

**Order:**
1. Standard-library imports (`datetime`, `pathlib`, `sqlite3`) in Python and `node:*` modules in CommonJS.
2. Third-party dependencies (`fastapi`, `pydantic`, `react`, `lucide-react`).
3. Project imports (`app.*`, `kisansathi_agent.*`, then relative frontend modules).
4. Side-effect stylesheet imports last at application entry points, as in `src/main.jsx`.

**Path Aliases:**
- Not detected in root `vite.config.js` or application imports. Use relative imports in `src/`, such as `../api/referenceApi.js` in `src/pages/FarmFinance.jsx`.
- Use absolute package imports beginning with `app.` in `backend/app/`, and relative imports within the `kisansathi_agent` package in `agent/src/kisansathi_agent/`.

## Error Handling

**Patterns:**
- Let Pydantic validate FastAPI payload shapes and range constraints in `backend/app/schemas/farm_state.py`; raise `HTTPException` at the router boundary for missing resources, conflicts, unsupported media, and provider failures in `backend/app/routers/`.
- Return structured error details with a stable `code` and human-readable `message` for operational failures where the MCP layer needs to classify retryability; examples are weather and idempotency errors in `backend/app/routers/weather.py` and `backend/app/routers/farm_state.py`.
- Map HTTP timeouts, transport errors, backend error envelopes, and invalid JSON into `BackendError` in `agent/src/kisansathi_agent/backend_client.py`; do not expose arbitrary backend response bodies to the model.
- Return bounded tool-result envelopes from `agent/src/kisansathi_agent/result.py` and preserve `warnings`, `request_id`, retryability, provenance, and action refresh metadata.
- In React, capture asynchronous errors into component/context state and render `ErrorState` from `src/components/feedback/ApiState.jsx`. Existing examples are `src/pages/GovtSchemes.jsx`, `src/pages/FieldTools.jsx`, and `src/context/AIConversationContext.jsx`.
- Keep unavailable external providers explicit. `backend/app/services/weather.py` and `backend/app/routers/assistants.py` return unavailable/inconclusive states rather than fabricated weather, diagnosis, speech, or translation output.

## Logging

**Framework:** Standard output/error only; no structured application logging dependency is configured for project-specific code.

**Patterns:**
- Electron emits renderer load, console, process, and Codex diagnostics through `console.error` and harness events in `desktop/main.cjs` and `desktop/codex-harness.cjs`.
- The frontend logs only local IndexedDB initialization/fallback failures in `src/db/localDatabase.js`.
- Backend operational logging, correlation middleware, and persistent audit logging are not established in `backend/app/`; preserve `X-Request-ID` at the MCP client boundary in `agent/src/kisansathi_agent/backend_client.py`, but do not imply end-to-end correlation currently exists.
- Never log secrets, full voice/image payloads, arbitrary provider bodies, or farmer financial records. The redaction expectation is tested in `agent/tests/test_backend_client.py`.

## Comments

**When to Comment:**
- Explain safety and ownership boundaries, not syntax. Good examples are the authentication disclaimer in `backend/app/farm_state/dependencies.py`, the read-only irrigation note in `backend/app/routers/farm_state.py`, and the renderer isolation rationale in `desktop/codex-harness.cjs`.
- Clearly label compatibility shims, provider-unavailable behavior, approximate geometry, demo defaults, and deprecated endpoints in the file that implements them.
- Do not use comments or documentation as evidence that a feature works. Validate runtime code and tests in `backend/tests/`, `agent/tests/`, `tests/desktop/`, or `src/**/*.test.jsx`.

**JSDoc/TSDoc:**
- Sparse. Use short JSDoc for non-obvious public classes or cross-process contracts, as in `desktop/codex-harness.cjs`; do not add boilerplate comments to self-explanatory React components.
- Python docstrings are sparse but appropriate for trust boundaries and repository abstractions, such as `get_farm_store` in `backend/app/farm_state/dependencies.py` and `FarmStateStore` in `backend/app/farm_state/store.py`.

## Function Design

**Size:**
- Keep route handlers focused on validation, one service/repository operation, and response conversion. Extract domain rules to `backend/app/farm_state/rules.py` and external-provider logic to `backend/app/services/`.
- Do not extend the existing monoliths `backend/app/routers/farm_state.py` (about 750 physical lines), `agent/src/kisansathi_agent/tools.py` (about 750 physical lines), or `backend/app/routers/assistants.py` (about 350 physical lines) with unrelated features; split by bounded domain before adding substantial behavior.
- Keep React render functions compositional. Extract page sections from compressed modules such as `src/pages/CorePages.jsx` and `src/pages/FieldTools.jsx` when adding behavior or tests.

**Parameters:**
- Receive validated Pydantic models as `payload`, dependencies through `Depends`, and explicit typed query/path/header parameters in FastAPI routes; see `backend/app/routers/farm_state.py`.
- Keep `farmer_id` out of MCP tool arguments. It is launcher-bound in `agent/src/kisansathi_agent/config.py` and sent as `X-Farmer-ID` by `agent/src/kisansathi_agent/backend_client.py`.
- Destructure React props and use `on<Action>` names for callbacks, as in `src/components/fields/LocationPicker.jsx` and `src/pages/MyFields.jsx`.

**Return Values:**
- FastAPI handlers must declare `response_model` and return validated response objects or compatible dictionaries in `backend/app/routers/`.
- MCP tools must return the common result shapes constructed by `tool_success`, `tool_error`, and related helpers in `agent/src/kisansathi_agent/result.py`; bound list/context output before returning it to Codex.
- Cross-process Electron methods return small serializable objects, not child processes, Node handles, or filesystem access. The exposed surface is limited in `desktop/preload.cjs` and asserted in `tests/desktop/preload-contract.test.cjs`.

## Module Design

**Exports:**
- Use default exports for the main React component in one-component files and named exports for contexts, hooks, API objects, shared helpers, or files containing multiple page components.
- Backend router modules expose a module-level `router` and register it once in `backend/app/main.py`.
- MCP registration is centralized in `agent/src/kisansathi_agent/server.py`; implement tool behavior in `agent/src/kisansathi_agent/tools.py` or a new domain module, not inside registration calls.

**Barrel Files:**
- Python `__init__.py` files under `backend/app/` and `agent/src/kisansathi_agent/` are package markers, not re-export barrels.
- No frontend barrel convention is used. Import directly from the defining module.
- Preserve `codex/` public crate surfaces and module privacy rules from `codex/AGENTS.md`; avoid adding farming behavior directly to `codex/codex-rs/core/` when the existing MCP plugin boundary under `codex/plugins/kisansathi/` is sufficient.

---

*Convention analysis: 2026-08-20*
