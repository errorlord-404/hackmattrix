# Codebase Concerns

**Analysis Date:** 2026-08-20

## Tech Debt

**Farmer state has three competing local-storage implementations:**
- Issue: Operational farm state is stored in server-side per-farmer SQLite by `backend/app/farm_state/store.py`; finance is separately stored in browser `localStorage` by `src/features/financeStore.js`; an unused IndexedDB implementation also defines finance, soil, weather, and AI stores and seeds invented records in `src/db/localDatabase.js`.
- Files: `backend/app/farm_state/store.py`, `src/features/financeStore.js`, `src/db/localDatabase.js`, `src/pages/FarmFinance.jsx`, `src/context/FarmDataContext.jsx`
- Impact: “Local” has incompatible meanings, finance cannot participate in reports/digital-twin history, browser/device changes lose or fork data, and the unused IndexedDB code can be mistaken for implemented offline support.
- Fix approach: Select one authoritative offline store owned by the desktop client, define repositories for profile/fields/cycles/soil/sensors/tasks/finance, and expose sync/event contracts. Remove `src/db/localDatabase.js` if it is not adopted; otherwise migrate `src/features/financeStore.js` into it and eliminate seeded production data.

**SQLite migrations are declarative bootstrap, not an upgrade system:**
- Issue: `FarmStateStore` executes one monolithic `SCHEMA` containing `CREATE TABLE IF NOT EXISTS`, then inserts migration version `1`; there are no ordered migration files, checksums, rollback/backup process, or column-upgrade paths.
- Files: `backend/app/farm_state/store.py`
- Impact: Existing farmer databases cannot safely evolve when columns, constraints, indexes, units, or entity relationships change. `CREATE TABLE IF NOT EXISTS` silently preserves incompatible old tables.
- Fix approach: Move schema versions to ordered migration modules/files, run each migration transactionally, test upgrade paths from every released version, back up before destructive migrations, and reject a database newer than the application.

**Farm-state and MCP modules are monolithic:**
- Issue: `backend/app/routers/farm_state.py` contains roughly 750 physical lines spanning identity profile, fields, crop cycles, soil, sensors, irrigation, alerts, dashboard, and reports; `agent/src/kisansathi_agent/tools.py` contains roughly 750 lines and dozens of tools; `backend/app/routers/assistants.py` combines image diagnosis, deprecated advisor sessions, STT, TTS, translation, and voice turns.
- Files: `backend/app/routers/farm_state.py`, `agent/src/kisansathi_agent/tools.py`, `backend/app/routers/assistants.py`
- Impact: Unrelated agents will collide in the same files, domain invariants drift, review is difficult, and targeted tests require broad fixtures.
- Fix approach: Split by bounded domains while preserving route/tool names: profile/fields, crop cycles/tasks, soil/sensors, irrigation/alerts, reports, crop health, and voice. Keep shared response/idempotency utilities in narrow modules.

**Frontend source is compressed beyond maintainable review size:**
- Issue: Major screens place entire render trees on one or a few lines. Maximum observed line lengths are about 4,625 characters in `src/pages/Dashboard.jsx`, 4,483 in `src/pages/FieldDetail.jsx`, 3,422 in `src/pages/CorePages.jsx`, and 3,204 in `src/pages/MachineryRentals.jsx`.
- Files: `src/pages/Dashboard.jsx`, `src/pages/FieldDetail.jsx`, `src/pages/CorePages.jsx`, `src/pages/MachineryRentals.jsx`, `src/pages/FieldTools.jsx`, `src/pages/FarmFinance.jsx`
- Impact: Diffs are opaque, merge conflicts affect whole screens, accessibility review is difficult, and unit testing individual states requires mocking page-scale components.
- Fix approach: Add Prettier or Biome, expand JSX, extract domain hooks and reusable sections, and land mechanical formatting separately from behavioral changes.

**Central CRUD and conversion logic is duplicated:**
- Issue: Reference routers repeat ObjectId parsing, document-to-response conversion, full-collection reads, updates, and deletes.
- Files: `backend/app/routers/crop.py`, `backend/app/routers/disease.py`, `backend/app/routers/farmer.py`, `backend/app/routers/fertilizer.py`, `backend/app/routers/gov_scheme.py`, `backend/app/routers/market_price.py`, `backend/app/routers/msp.py`, `backend/app/routers/seed.py`, `backend/app/routers/machinery_rental.py`
- Impact: Authentication, pagination, provenance validation, error envelopes, and auditing will be inconsistent across domains.
- Fix approach: Extract small typed repository and response/error helpers without hiding domain-specific queries. Retain explicit routers and schemas so API contracts remain readable.

**Configuration and operational gates are incomplete:**
- Issue: The project has a backend `.env.example` and local setup script, but no root CI workflow, backend/agent type checking, Python linting, coverage gate, production readiness endpoint, or deployment migration gate.
- Files: `backend/.env.example`, `backend/scripts/setup_universal_data.ps1`, `backend/app/main.py`, `backend/pytest.ini`, `agent/pyproject.toml`, `package.json`
- Impact: A clean environment can pass no automated cross-stack gate, dependency warnings accumulate, and Mongo being unavailable still allows startup in a degraded state without a separate readiness contract.
- Fix approach: Add CI under `.github/workflows/`, reproducible environment setup, `/ready`, dependency health checks, schema migration verification, Ruff/mypy or Pyright, frontend coverage, and security scans.

**Project-specific farming integration lives beside a full upstream fork without an explicit compatibility gate:**
- Issue: KisanSathi integrates through `codex/plugins/kisansathi/`, `agent/`, and `desktop/codex-harness.cjs`, while `codex/` is a very large upstream source tree with its own build/test rules. No root command verifies the plugin against the checked-in app-server protocol.
- Files: `codex/plugins/kisansathi/run_server.py`, `agent/src/kisansathi_agent/server.py`, `desktop/codex-harness.cjs`, `codex/AGENTS.md`, `package.json`
- Impact: Updating the fork can break JSONL methods, event names, approvals, or plugin startup while project tests continue passing against fakes.
- Fix approach: Keep agricultural logic outside `codex/codex-rs/core/`, pin a known app-server contract, add a real app-server smoke/contract test, and document the upstream update/rebase procedure.

## Known Bugs

**Irrigation advice can use weather from the wrong field:**
- Symptoms: `_irrigation_plan` selects the latest `weather_snapshots` row without latitude/longitude filtering, even though one farmer can have multiple fields.
- Files: `backend/app/routers/farm_state.py`, `backend/app/routers/weather.py`
- Trigger: Fetch weather for field B after recording moisture for field A, then request `/v1/fields/{field-a}/irrigation-plan`; field A can use field B's rain probability.
- Workaround: Do not treat rain-aware irrigation advice as field-specific until the snapshot query filters on field A's centroid or stores `field_id`.

**Sensor NPK/pH readings are displayed but excluded from soil interpretation:**
- Symptoms: `get_soil_health` loads latest `sensor_readings` into `observations`, but `latest_values` is populated only from the latest `soil_tests` row before calling `soil_interpretation`.
- Files: `backend/app/routers/farm_state.py`, `backend/app/farm_state/rules.py`
- Trigger: Record only a low nitrogen or abnormal pH sensor reading and call `/v1/fields/{field_id}/soil-health`; the response can report `within_screening_ranges` while returning the abnormal observation.
- Workaround: Use a laboratory/manual soil test for current interpretation; do not rely on sensor-only soil status.

**Agronomic thresholds ignore measurement units:**
- Symptoms: `SensorReadingCreate.unit` accepts any non-empty string, but moisture alerts and irrigation compare raw values to `30`, `35`, and `40`; soil nitrogen is compared to `280` without a stored unit.
- Files: `backend/app/schemas/farm_state.py`, `backend/app/routers/farm_state.py`, `backend/app/farm_state/rules.py`, `backend/app/farm_state/store.py`
- Trigger: Send moisture as fraction (`0.25`) or soil nitrogen in a unit other than the assumed convention; the system makes a numerically valid but semantically wrong recommendation.
- Workaround: Only ingest moisture as percent and NPK using the undocumented expected lab convention; validate externally.

**Crop stages accept arbitrary strings:**
- Symptoms: `initial_stage` and stage updates are free-form strings rather than the intended lifecycle enum, and the irrigation rule only recognizes exact lowercase values for flowering/fruiting/grain filling.
- Files: `backend/app/schemas/farm_state.py`, `backend/app/routers/farm_state.py`, `backend/app/farm_state/rules.py`
- Trigger: Record `Grain Filling`, `grain_filling`, a localized stage, or a typo; crop history accepts it and stage-specific irrigation behavior may not apply.
- Workaround: Use the exact English strings recognized by `irrigation_rule`.

**Government scheme “eligibility” ignores supplied criteria:**
- Symptoms: `MongoGovSchemeMutator.check_scheme_eligibility` assigns `eligibility_criteria` to `_` and filters only by state/nationwide applicability.
- Files: `backend/app/services/gov_scheme_mutator.py`, `backend/app/routers/gov_scheme.py`, `backend/app/schemas/gov_scheme.py`
- Trigger: Submit criteria that conflict with a scheme's eligibility; the scheme remains in the result.
- Workaround: Present results as scheme discovery, not an eligibility determination.

**Mandi comparison mixes current and historical records and can overstate precision:**
- Symptoms: `compare_mandis` loads every record matching exact crop name, applies configured flat defaults when cost inputs are omitted, performs no latest-per-mandi selection or freshness limit, and sorts all results as comparable.
- Files: `backend/app/routers/market_price.py`, `backend/app/services/market.py`, `backend/app/models/market_price.py`
- Trigger: Ingest multiple days for one mandi and compare the crop; stale and duplicate mandi observations appear as separate ranked choices.
- Workaround: Supply explicit costs and manually select a fresh observation; do not interpret the first row as a verified sale recommendation.

**Unknown frontend routes have no explicit not-found screen:**
- Symptoms: The route tree has no catch-all route or error element.
- Files: `src/routes/index.jsx`, `src/pages/PlaceholderPage.jsx`
- Trigger: Navigate to an undefined path in the browser or desktop hash route.
- Workaround: Return through navigation; `src/pages/PlaceholderPage.jsx` exists but is not wired as a 404.

**Verified build and test warnings remain unresolved:**
- Symptoms: `npm run build` succeeds but warns about a 639.50 kB minified chunk; backend tests warn about deprecated Starlette/httpx TestClient integration; agent tests warn about an unresolved Pydantic Settings forward reference; both Python suites warn about unset pytest-asyncio loop scope.
- Files: `vite.config.js`, `src/routes/index.jsx`, `backend/pytest.ini`, `backend/requirements.txt`, `agent/pyproject.toml`, `agent/src/kisansathi_agent/server.py`
- Trigger: Run the commands documented in `.planning/codebase/TESTING.md`.
- Workaround: None required for the current checks to pass, but dependency upgrades can turn these warnings into failures.

## Security Considerations

**Farmer identity is spoofable and defaults to a shared tenant:**
- Risk: Any caller chooses a farmer database through `X-Farmer-ID`; missing headers fall back to `demo`. The code explicitly states this is not authentication.
- Files: `backend/app/farm_state/dependencies.py`, `src/api/client.js`, `desktop/main.cjs`, `agent/src/kisansathi_agent/config.py`
- Current mitigation: `safe_farmer_key` in `backend/app/farm_state/store.py` prevents path traversal and restricts characters, and desktop binds a fixed farmer ID outside model tool arguments.
- Recommendations: Authenticate users/devices, derive farmer identity from a verified subject, remove the production demo fallback, authorize every field/resource lookup, and test cross-tenant access.

**Central reference data is publicly writable and destructive:**
- Risk: Crop, disease, fertilizer, scheme, market, MSP, seed, machinery, and central farmer CRUD routes have no authentication or role checks.
- Files: `backend/app/routers/crop.py`, `backend/app/routers/disease.py`, `backend/app/routers/fertilizer.py`, `backend/app/routers/gov_scheme.py`, `backend/app/routers/market_price.py`, `backend/app/routers/msp.py`, `backend/app/routers/seed.py`, `backend/app/routers/machinery_rental.py`, `backend/app/routers/farmer.py`
- Current mitigation: Pydantic validation and ObjectId checking only; ingestion routes separately validate `X-Ingestion-Token` in `backend/app/routers/ingestion.py`.
- Recommendations: Make public catalog routes read-only, restrict mutations to an authenticated ingestion/admin principal, add audit records and optimistic concurrency, and remove/deprecate unused public delete endpoints.

**CORS is unrestricted while credentials are enabled:**
- Risk: `allow_origins=["*"]`, all methods, and all headers are combined with `allow_credentials=True`.
- Files: `backend/app/main.py`
- Current mitigation: None beyond browser CORS behavior.
- Recommendations: Configure explicit origins, methods, and headers per environment; disable credentials until authenticated browser flows exist; add CORS contract tests.

**Uploaded crop images and farmer SQLite databases are unencrypted local files:**
- Risk: Diagnosis images are written below `FARM_STATE_UPLOAD_DIR`, and farmer state is stored as plain SQLite files below `FARM_STATE_DB_DIR`; there is no retention, encryption, permission hardening, backup, or deletion policy.
- Files: `backend/app/routers/assistants.py`, `backend/app/farm_state/store.py`, `backend/app/core/config.py`, `backend/data/farm_uploads/`, `backend/data/farm_state/`
- Current mitigation: Upload size and magic-byte/type validation, random identifiers, and safe farmer path keys.
- Recommendations: Store uploads outside the repository, enforce owner-only filesystem permissions, encrypt sensitive data/backups, implement retention and user deletion, strip image metadata, and never commit runtime databases/uploads.

**Runtime farmer data is not ignored by the repository:**
- Risk: `.gitignore` ignores environments and runtime binaries but does not ignore `backend/data/farm_state/` or `backend/data/farm_uploads/`; current runtime artifacts exist under those paths.
- Files: `.gitignore`, `backend/data/farm_state/demo.sqlite3`, `backend/data/farm_uploads/demo/`
- Current mitigation: None detected.
- Recommendations: Ignore runtime data directories, remove committed/staged samples through a recoverable migration if applicable, provide synthetic fixtures under explicit test paths, and scan git history before public release.

**Electron IPC validates only selected payloads:**
- Risk: Image/audio sizes and media types are checked in `desktop/main.cjs`, but session options, text metadata, approval results, translation bodies, and synthesis bodies pass from renderer to harness/backend with minimal main-process schema validation.
- Files: `desktop/main.cjs`, `desktop/preload.cjs`, `desktop/codex-harness.cjs`
- Current mitigation: `contextIsolation`, disabled `nodeIntegration`, sandboxing, a narrow preload API, and model-side tool approval; these are asserted in `tests/desktop/preload-contract.test.cjs`.
- Recommendations: Validate every IPC payload with schemas, cap text/metadata sizes, allow-list approval results and language codes, and add malicious-renderer contract tests.

**Action safety depends partly on instructions rather than a durable policy record:**
- Risk: The desktop base prompt tells the model to ask before writes, and MCP tools carry `_WRITE` annotations, but backend write endpoints accept direct calls without confirmation records or authorization.
- Files: `desktop/codex-harness.cjs`, `agent/src/kisansathi_agent/server.py`, `backend/app/routers/farm_state.py`
- Current mitigation: Codex approval mode `writes`, explicit read/write annotations, idempotency keys, and no pump/payment/machinery actuation tool.
- Recommendations: Enforce action levels server-side, create confirmation/audit records bound to actor/action/payload/expiry, require hardware safety interlocks for future Level 3 actions, and never rely on prompt text alone.

## Performance Bottlenecks

**Reference list and recommendation queries are unbounded:**
- Problem: Most Mongo routes/services call `.to_list()` without limit, cursor, deterministic sort, or projection.
- Files: `backend/app/routers/crop.py`, `backend/app/routers/disease.py`, `backend/app/routers/farmer.py`, `backend/app/routers/fertilizer.py`, `backend/app/routers/gov_scheme.py`, `backend/app/routers/market_price.py`, `backend/app/routers/msp.py`, `backend/app/routers/seed.py`, `backend/app/services/seed_mutator.py`, `backend/app/services/fertilizer_mutator.py`
- Cause: Collection-shaped response APIs and incomplete query indexes.
- Improvement path: Add cursor pagination and hard limits, normalize search keys, create compound indexes for actual filters/sorts, and bound MCP-facing results independently.

**The frontend ships one oversized main chunk:**
- Problem: The verified Vite build emits a 639.50 kB minified JavaScript chunk (190.86 kB gzip) and a chunk-size warning.
- Files: `src/routes/index.jsx`, `package.json`, `vite.config.js`
- Cause: All route pages and heavy libraries such as Leaflet, Recharts, and Framer Motion are imported eagerly.
- Improvement path: Lazy-load route groups and heavy visualization/map code, define stable loading boundaries, and enforce bundle budgets in CI.

**SQLite connection/schema setup happens on every farm-state request:**
- Problem: `get_farm_store` creates a new `FarmStateStore`; its constructor opens SQLite and runs the entire `SCHEMA` script before each request.
- Files: `backend/app/farm_state/dependencies.py`, `backend/app/farm_state/store.py`
- Cause: Request-scoped connection ownership combined with bootstrap-as-migration.
- Improvement path: Run migrations once, use a bounded connection/session strategy, enable/test WAL and busy handling if concurrent writes remain server-side, and move local ownership to the desktop when offline architecture is implemented.

**Multi-step farm mutations commit each statement separately:**
- Problem: `FarmStateStore.execute` commits immediately, while routes perform a domain write, alert/stage-event write, and idempotency record as separate commits.
- Files: `backend/app/farm_state/store.py`, `backend/app/routers/farm_state.py`, `backend/app/routers/assistants.py`
- Cause: Repository helpers expose auto-commit primitives rather than a unit-of-work boundary.
- Improvement path: Wrap each command and its side effects/idempotency record in one SQLite transaction; add failure-injection tests proving rollback.

## Fragile Areas

**Idempotency is non-atomic with the protected mutation:**
- Files: `backend/app/farm_state/store.py`, `backend/app/routers/farm_state.py`, `backend/app/routers/assistants.py`
- Why fragile: Lookup, domain writes, side effects, and `idempotency_records` insertion are separate commits. A crash can persist the action without the replay record, and concurrent same-key requests can race into a primary-key error after duplicating effects.
- Safe modification: Reserve/check the key and execute the mutation plus stored response in one `BEGIN IMMEDIATE` transaction; scope keys by route/action and preserve original status codes.
- Test coverage: `backend/tests/test_farm_state.py` covers sequential replay and conflict, not concurrency or crash rollback.

**Irrigation and soil rules are screening constants presented near operational workflows:**
- Files: `backend/app/farm_state/rules.py`, `backend/app/routers/farm_state.py`, `src/pages/CorePages.jsx`
- Why fragile: Fixed thresholds do not account for crop variety, soil texture, rooting depth, evapotranspiration, sensor calibration, units, irrigation efficiency, or water availability.
- Safe modification: Keep rules explicitly advisory, introduce validated unit-bearing inputs and crop/soil profiles, cite rule versions, and require agronomist review before any automation.
- Test coverage: `backend/tests/test_farm_state.py` covers one low-moisture path and read-only behavior; no boundary matrix or unit/calibration tests exist.

**Weather cache and alert freshness semantics can diverge:**
- Files: `backend/app/routers/weather.py`, `backend/app/routers/farm_state.py`, `backend/app/services/weather.py`
- Why fragile: `get_weather` enforces `WEATHER_CACHE_SECONDS`, but `get_weather_alerts` accepts the latest matching snapshot without the same age check, while irrigation reads the latest snapshot for any location.
- Safe modification: Centralize field/location-specific cache selection and freshness validation in one weather repository/service.
- Test coverage: `backend/tests/test_farm_state.py` checks provider-unavailable behavior only, not stale or cross-field cache selection.

**MCP tool catalog is large relative to behavioral coverage:**
- Files: `agent/src/kisansathi_agent/server.py`, `agent/src/kisansathi_agent/tools.py`, `agent/tests/test_tools.py`
- Why fragile: Dozens of tools are registered, but tests exercise only selected calls and annotations; route drift, parameter serialization, response bounding, and action metadata can break silently.
- Safe modification: Generate/validate a tool contract matrix, split tools by domain, and add parameterized contract tests for every registration.
- Test coverage: `agent/tests/test_tools.py` has eight tests for a catalog of roughly forty-five registered tools.

**Localization has multiple sources of truth:**
- Files: `src/constants/translations.js`, `src/constants/pageTranslations.js`, `src/i18n/en.json`, `src/i18n/hi.json`, `src/i18n/mr.json`, `src/data/localizedContent.js`, `src/pages/VoiceAssistant.jsx`
- Why fragile: UI strings are split between i18next resources, constant maps, page-local objects, and hard-coded English JSX. Translation completeness and key parity cannot be checked centrally.
- Safe modification: Consolidate user-facing copy into one i18n system, preserve provider language codes separately, and add key-parity/render tests for English, Hindi, and Marathi.
- Test coverage: Only `src/components/features/ai/ConversationView.test.jsx` asserts a Hindi message and English interpretation; route-wide localization is untested.

**Deprecated advisor routes remain callable and are represented as write tools:**
- Files: `backend/app/routers/assistants.py`, `agent/src/kisansathi_agent/server.py`, `agent/src/kisansathi_agent/tools.py`
- Why fragile: FastAPI marks advisor session/message/stream endpoints deprecated while MCP still registers `create_advisor_session` and `ask_farm_advisor`; the real desktop harness is intended to own reasoning.
- Safe modification: Remove the duplicate backend advisor flow after clients migrate, or define one authoritative orchestration path and compatibility sunset tests.
- Test coverage: `agent/tests/test_tools.py` tests the deprecated route shape only through mocked HTTP.

## Scaling Limits

**Per-farmer SQLite is server-local, not offline client-local:**
- Current capacity: One SQLite file per header-selected farmer is created beneath the backend process filesystem by `backend/app/farm_state/store.py`.
- Limit: Horizontal backend replicas do not share files; farmers cannot access state offline unless the server runs on their device; no sync, conflict resolution, revision, encryption, or backup protocol exists.
- Scaling path: Move the authoritative operational store into the desktop client or use a real authenticated central operational database; define append-only changes, revisions, sync cursors, conflict rules, queued writes, and encrypted backups.

**No device identity or telemetry protocol exists:**
- Current capacity: `sensor_devices` and `sensor_readings` tables exist, and HTTP/MCP can record readings; no firmware, MQTT/HTTP gateway, device credentials, sequence numbers, acknowledgements, calibration workflow, or offline queue is present.
- Limit: Real IoT telemetry cannot be authenticated, deduplicated reliably, or safely connected to pump control.
- Scaling path: Define device/farmer/farm/field/sensor identity, signed telemetry envelopes, monotonically increasing sequence IDs, calibration metadata, command acknowledgements, watchdog/manual override, and simulator tests.
- Files: `backend/app/farm_state/store.py`, `backend/app/schemas/farm_state.py`, `backend/app/routers/farm_state.py`

**Reference Mongo and operational SQLite have no synchronization or referential contract:**
- Current capacity: Crop names, fertilizer crop names, crop-cycle crop names, and market crop names are free text in separate stores.
- Limit: Renames, localization, duplicates, and offline catalog revisions cannot be reconciled; recommendations cannot reliably join shared agronomy to a farmer crop cycle.
- Scaling path: Introduce stable reference IDs plus versioned snapshots, canonical units/names, local catalog cache versions, and explicit fallback behavior when a reference record is unavailable.
- Files: `backend/app/models/crop.py`, `backend/app/models/market_price.py`, `backend/app/schemas/farm_state.py`, `backend/app/farm_state/store.py`

## Dependencies at Risk

**Backend tests rely on undeclared development packages:**
- Risk: `backend/requirements.txt` pins runtime packages but does not declare pytest, pytest-asyncio, or a supported test-client package even though `backend/tests/` imports pytest behavior and FastAPI TestClient.
- Impact: A clean backend environment may not run the documented suite; installed global packages produced current deprecation warnings.
- Migration plan: Add a backend `pyproject.toml` or dev requirements lock with Python version, pytest, async test configuration, and compatible TestClient dependencies.
- Files: `backend/requirements.txt`, `backend/pytest.ini`, `backend/tests/`

**Python dependency state is split and warning-prone:**
- Risk: Backend uses a fully pinned requirements file without hashes/lock metadata, while agent uses broad compatible ranges and no committed resolver lock; current runs emit Starlette/Pydantic/pytest-asyncio warnings.
- Impact: Clean installations can resolve different transitive versions and turn warnings into runtime/test failures.
- Migration plan: Standardize on locked environments, declare Python 3.11+ consistently, resolve warnings, and add automated dependency updates with contract tests.
- Files: `backend/requirements.txt`, `agent/pyproject.toml`, `backend/pytest.ini`

**Root Node runtime is not pinned:**
- Risk: `package.json` and `package-lock.json` exist, but no `.nvmrc`, `.node-version`, or `engines` field defines the supported Node/npm version; Electron 43 and Vite 8 have modern runtime requirements.
- Impact: Contributors and CI can fail before tests or produce incompatible desktop builds.
- Migration plan: Declare Node/npm engines, commit a runtime-version file, use `npm ci`, and test supported Windows/Linux/macOS desktop targets.
- Files: `package.json`, `package-lock.json`

**Full Codex fork maintenance surface is large:**
- Risk: `codex/` contains a complete multi-crate/multi-SDK upstream repository with Bazel/Cargo/npm tooling, while the farming product depends on only app-server/plugin integration.
- Impact: Fork updates and security patches are costly; accidental core modifications can create long-lived divergence.
- Migration plan: Keep farming code in `agent/`, `desktop/`, and `codex/plugins/kisansathi/`; track upstream revision, minimize patches, and automate compatibility/rebase checks.
- Files: `codex/codex-rs/Cargo.toml`, `codex/MODULE.bazel`, `codex/AGENTS.md`, `codex/plugins/kisansathi/`

## Missing Critical Features

**No production authentication, authorization, or farmer onboarding identity:**
- Problem: Profile fields exist, but verified phone/email login, device binding, consent, roles, farmer isolation, and account recovery do not.
- Blocks: Safe multi-user deployment, private farm data, financial workflows, purchases, and hardware actions.
- Files: `backend/app/farm_state/dependencies.py`, `backend/app/routers/farmer.py`, `src/pages/Settings.jsx`

**Digital twin is partial and lacks core lifecycle entities:**
- Problem: Fields, crop cycles, soil, sensors, irrigation, reminders, alerts, diagnosis, reports, and limited history exist in `backend/app/farm_state/store.py`; inventory, equipment ownership/maintenance, fertilizer/pesticide applications, expenses, harvest lots, grades, storage lots, logistics, sales, insurance, credit, scheme applications, and result/lesson feedback are absent.
- Blocks: A persistent harvest-to-harvest farm copilot and accurate profit/traceability history.
- Files: `backend/app/farm_state/store.py`, `backend/app/schemas/farm_state.py`, `src/features/financeStore.js`

**Crop planning/recommendation engine is not implemented:**
- Problem: Central crop records and seed/fertilizer catalog filters exist, but there is no next-crop optimizer combining rotation, soil, season, weather, water, budget, market price, risk, and expected net profit.
- Blocks: The first-stage decision flow described by the product vision.
- Files: `backend/app/models/crop.py`, `backend/app/services/seed_mutator.py`, `backend/app/services/fertilizer_mutator.py`, `agent/src/kisansathi_agent/tools.py`

**Nutrient deficit and fertilizer dose engine is absent:**
- Problem: Soil screening checks only pH and nitrogen thresholds; it does not calculate crop requirement minus soil availability, product nutrient composition, dose, area conversion, application stage, split schedule, or safety constraints.
- Blocks: Trustworthy N/P/K/organic-carbon/EC guidance and cost-aware procurement.
- Files: `backend/app/farm_state/rules.py`, `backend/app/schemas/farm_state.py`, `backend/app/services/fertilizer_mutator.py`

**Predictive irrigation and physical IoT control are absent:**
- Problem: Current logic is a read-only moisture/rain screening rule. There is no evapotranspiration/water-balance model, soil texture/root depth, forecast amount, pump capacity, relay service, command acknowledgement, manual override, or safety interlock.
- Blocks: Smart-plug pump automation and safe predictive water management.
- Files: `backend/app/farm_state/rules.py`, `backend/app/routers/farm_state.py`, `agent/src/kisansathi_agent/server.py`

**Crop health inference is a provider placeholder:**
- Problem: Image upload/persistence exists, but unconfigured diagnosis returns `inconclusive`; there is no deployed disease/pest model, symptom+weather+stage fusion, regional outbreak data, model version, class metrics, treatment validation, or expert escalation.
- Blocks: Real disease/pest diagnosis and safe treatment workflows.
- Files: `backend/app/routers/assistants.py`, `backend/app/core/config.py`, `backend/tests/test_farm_state.py`, `src/pages/FieldTools.jsx`

**Marketplace, booking, and vendor aggregation are catalog-only:**
- Problem: Machinery listings can be searched and contacted, but vendor aggregation, availability quotes, normalized units, booking, payment, cancellation, ratings verification, seeds/fertilizer procurement, and logistics search are absent.
- Blocks: Cheapest-real-cost procurement and action completion.
- Files: `backend/app/routers/machinery_rental.py`, `src/pages/MachineryRentals.jsx`, `agent/src/kisansathi_agent/tools.py`

**Harvest, grading, storage, logistics, sale, and profit lifecycle is absent:**
- Problem: Market history/comparison and a browser ledger exist, but harvest readiness, lot creation, vision grading, packaging, spoilage/storage decision, warehouse inventory, transport quotes, sale records, realized profit, and season learning are not implemented.
- Blocks: The post-harvest half of the lifecycle and “sell now/store/other market” decisions.
- Files: `backend/app/routers/market_price.py`, `src/pages/FarmFinance.jsx`, `src/features/financeStore.js`, `backend/app/farm_state/store.py`

**Disaster management is limited to simple rain-probability alerts:**
- Problem: There is no before/during/after disaster workflow, location-specific multi-hazard model, preparation tasks, emergency contacts, damage assessment, claim evidence, or recovery plan.
- Blocks: Predict → warn → prepare, event-time guidance, and post-event recovery/insurance support.
- Files: `backend/app/routers/weather.py`, `backend/app/farm_state/store.py`, `src/components/layout/AlertMenu.jsx`

**Farm mapping is approximate and satellite analytics are absent:**
- Problem: The UI creates a point-buffer polygon and stores GeoJSON, but there is no surveyed boundary editing, geometry validation beyond basic Polygon shape, area calculation from geometry, satellite provider abstraction, imagery dates/cloud masks, NDVI/vegetation indices, overlays, or sensor map placement.
- Blocks: A credible farm digital twin map and remote crop monitoring.
- Files: `src/components/fields/LocationPicker.jsx`, `src/pages/MyFields.jsx`, `src/pages/FieldTools.jsx`, `backend/app/schemas/farm_state.py`

**Offline-first sync is absent:**
- Problem: There is no service worker/desktop queue, reference cache versioning, queued API writes, reconnect reconciliation, conflict resolution, or sync observability. `src/db/localDatabase.js` is unused and does not implement sync.
- Blocks: Reliable operation for farmers with intermittent connectivity.
- Files: `src/db/localDatabase.js`, `src/api/client.js`, `backend/app/farm_state/store.py`

**Observability and decision audit are incomplete:**
- Problem: There is no structured backend log pipeline, trace propagation middleware, metrics, health dashboards, model inference logs, telemetry audit, or durable link from recommendation inputs/version to farmer action/outcome.
- Blocks: Debugging, safety review, source accountability, and learning across seasons.
- Files: `backend/app/main.py`, `agent/src/kisansathi_agent/backend_client.py`, `desktop/codex-harness.cjs`, `backend/app/farm_state/store.py`

## Test Coverage Gaps

**React farmer application is almost entirely untested:**
- What's not tested: Dashboard, fields, map, crop guide, soil, weather, irrigation, pest/disease upload, market, schemes, finance, machinery, AI/voice state machines, reports, settings, routing, accessibility, offline/error/loading/empty states, and Hindi/Marathi parity.
- Files: `src/routes/index.jsx`, `src/pages/`, `src/context/FarmDataContext.jsx`, `src/context/AIConversationContext.jsx`
- Risk: The hackathon journey can fail or misrepresent stale/unavailable data despite a green one-test UI suite.
- Priority: High

**Central Mongo APIs and ingestion lack database integration coverage:**
- What's not tested: CRUD authorization/validation, Mongo startup/readiness, Beanie indexes, pagination, all source upserts, ingestion retries/partial failures, duplicate source IDs, and unavailable database behavior.
- Files: `backend/app/core/database.py`, `backend/app/models/`, `backend/app/routers/crop.py`, `backend/app/routers/market_price.py`, `backend/app/routers/ingestion.py`, `backend/app/scraping/service.py`
- Risk: Reference catalogs can corrupt, duplicate, disappear, or remain publicly mutable without detection.
- Priority: High

**Farm-state tests cover only a narrow subset of schema and commands:**
- What's not tested: Field patch/delete, crop-cycle creation/stage validation, soil interpretation matrix, cross-field weather bug, stale weather, sensor unit handling, reminders, alert transitions, dashboards, report snapshots, upload cleanup, concurrency, transaction rollback, and migration upgrades.
- Files: `backend/app/routers/farm_state.py`, `backend/app/routers/weather.py`, `backend/app/routers/assistants.py`, `backend/app/farm_state/store.py`, `backend/app/farm_state/rules.py`
- Risk: Partial state, unsafe recommendations, and schema incompatibility can go unnoticed.
- Priority: High

**Most MCP tools are contract-untested:**
- What's not tested: Every registered tool's exact schema, route, query/body serialization, error mapping, bounded output, annotations, confirmation semantics, and refresh metadata.
- Files: `agent/src/kisansathi_agent/server.py`, `agent/src/kisansathi_agent/tools.py`, `agent/src/kisansathi_agent/result.py`
- Risk: Codex can receive malformed or oversized results, call stale routes, or treat a write as read-only.
- Priority: High

**No real cross-stack end-to-end journey exists:**
- What's not tested: React/Electron → app-server JSONL → MCP plugin → FastAPI → SQLite/Mongo/provider response, including approval, translation, recovery, and state refresh.
- Files: `src/context/AIConversationContext.jsx`, `desktop/codex-harness.cjs`, `codex/plugins/kisansathi/run_server.py`, `agent/src/kisansathi_agent/server.py`, `backend/app/main.py`
- Risk: Each layer passes against local fakes while integration fails in the demo.
- Priority: High

**No ML, IoT, security, performance, or disaster simulation suites exist:**
- What's not tested: Model accuracy/calibration/abstention, device authentication/telemetry replay/control safety, tenant authorization/CORS, bundle/API load, offline sync conflicts, disaster alert correctness, harvest grading, or market/storage economics.
- Files: `backend/app/routers/assistants.py`, `backend/app/routers/farm_state.py`, `backend/app/main.py`, `src/routes/index.jsx`
- Risk: These capabilities are either absent or cannot be productionized safely without measurable gates.
- Priority: High

---

*Concerns audit: 2026-08-20*
