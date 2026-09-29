# Testing Patterns

**Analysis Date:** 2026-08-20

## Test Framework

**Runner:**
- Vitest 4.1.11 for React component tests. Config: `vitest.config.js`; discovery is limited to `src/**/*.test.{js,jsx}` in a `jsdom` environment.
- Node's built-in `node:test` runner for Electron desktop/harness contracts under `tests/desktop/`; command is defined in `package.json`.
- pytest for the FastAPI backend under `backend/tests/`. Config: `backend/pytest.ini`, which sets `pythonpath = .` and `testpaths = tests`.
- pytest for the MCP agent under `agent/tests/`. Config: `[tool.pytest.ini_options]` in `agent/pyproject.toml`.
- The upstream Codex fork has extensive Rust, Python SDK, TypeScript SDK, snapshot, protocol, and integration suites under `codex/`. Its authoritative workflow is `codex/AGENTS.md`; that coverage does not validate KisanSathi farming modules in `src/`, `backend/`, `agent/`, or `desktop/`.

**Assertion Library:**
- Vitest `expect` plus Testing Library queries/events in `src/components/features/ai/ConversationView.test.jsx`.
- `node:assert/strict` in `tests/desktop/codex-harness.test.cjs` and `tests/desktop/preload-contract.test.cjs`.
- Plain pytest `assert`, `pytest.raises`, FastAPI `TestClient`, and `httpx.MockTransport` in `backend/tests/` and `agent/tests/`.

**Run Commands:**
```bash
npm run test:ui             # React/Vitest suite
npm run test:desktop        # Electron harness and preload contracts
npm run lint                # Root ESLint static check
npm run build               # Vite production build

cd backend
python -m pytest -q         # FastAPI, farm-state, provider, ingestion, and rule tests

cd agent
python -m pytest -q         # MCP tool and backend-client tests

cd codex/codex-rs
just test -p <crate>        # Required scoped Rust test form; follow `codex/AGENTS.md`
```

## Verified Current Results

**2026-08-20 audit run:**
- `npm run lint`: passed with exit code 0.
- `npm run test:ui`: 1 file and 1 test passed.
- `npm run test:desktop`: 6 tests passed.
- `python -m pytest -q` from `backend/`: 14 tests passed; emitted a Starlette deprecation warning that `httpx` with `starlette.testclient` is deprecated in favor of `httpx2`.
- `python -m pytest -q` from `agent/`: 10 tests passed; emitted a Pydantic Settings `IncompleteFieldDefinitionWarning` while constructing the MCP server.
- Both pytest runs also emitted a `pytest-asyncio` default-loop-scope deprecation warning from the installed environment because the option is not configured in `backend/pytest.ini` or `agent/pyproject.toml`.
- `npm run build`: passed; Vite reported a 639.50 kB minified JavaScript chunk and warned that chunks exceed 500 kB.
- The complete `codex/` fork suite was not run during this mapping pass. No project-specific production code under `codex/codex-rs/` was identified as the KisanSathi test target; integration occurs through `codex/plugins/kisansathi/` and `agent/`.

## Test File Organization

**Location:**
- Co-locate focused React component tests beside the component: `src/components/features/ai/ConversationView.test.jsx`.
- Keep cross-process Electron tests in `tests/desktop/`, parallel to `desktop/`.
- Keep backend tests in `backend/tests/` and MCP-agent tests in `agent/tests/`.
- Keep provider/network parsing tests at the service boundary, as in `backend/tests/test_sarvam.py` and `backend/tests/test_universal_data_sources.py`.

**Naming:**
- React: `<Component>.test.jsx`.
- Node: `<feature>.test.cjs`.
- Python: `test_<domain>.py`, with test functions named `test_<behavior>_<expected_outcome>`.
- Rust under `codex/`: follow sibling `*_tests.rs`, integration-suite, and `insta` snapshot conventions documented in `codex/AGENTS.md`.

**Structure:**
```text
src/
└── components/features/ai/
    ├── ConversationView.jsx
    └── ConversationView.test.jsx

tests/desktop/
├── codex-harness.test.cjs
└── preload-contract.test.cjs

backend/tests/
├── test_farm_state.py
├── test_market_rules.py
├── test_sarvam.py
└── test_universal_data_sources.py

agent/tests/
├── test_backend_client.py
└── test_tools.py
```

## Test Structure

**Suite Organization:**
```python
def test_low_moisture_creates_one_deduplicated_alert_and_plan():
    with TemporaryDirectory() as tmp:
        client = _client(tmp)
        headers = {"X-Farmer-ID": "farmer_a"}
        field = client.post("/v1/fields", headers=headers, json={...}).json()
        response = client.post("/v1/sensor-readings", headers=headers, json={...})
        assert response.status_code == 201
        assert len(client.get("/v1/alerts", headers=headers).json()) == 1
```
Pattern source: `backend/tests/test_farm_state.py`.

```javascript
test('rejects an in-flight request and can recover after app-server exit', async () => {
  const first = makeHarness({ respondTurns: false });
  await first.harness.start();
  const pendingTurn = first.harness.sendText('wait for response');
  first.processes[0].stop(2);
  await assert.rejects(pendingTurn, /Codex app-server stopped/);
});
```
Pattern source: `tests/desktop/codex-harness.test.cjs`.

**Patterns:**
- Arrange isolated dependencies, perform behavior through the public boundary, and assert response/result contracts rather than private implementation details.
- Use `TemporaryDirectory` and per-test farmer IDs to isolate SQLite state in `backend/tests/test_farm_state.py`.
- Close `TestClient` and `BackendClient` instances when a test owns them; agent tests call `await client.aclose()` in `agent/tests/test_tools.py` and `agent/tests/test_backend_client.py`.
- Assert complete small result objects when practical. Desktop tests use `assert.deepEqual` for JSONL responses in `tests/desktop/codex-harness.test.cjs`.
- Test failure/unavailable behavior explicitly, including weather provider failure, malformed app-server output, invalid base64, missing coordinates, and backend-body redaction.

## Mocking

**Framework:**
- `vi.mock`, `vi.fn`, and `vi.hoisted` for React in `src/components/features/ai/ConversationView.test.jsx`.
- Purpose-built `FakeProcess`/`EventEmitter` fakes for the Codex app-server child process in `tests/desktop/codex-harness.test.cjs`.
- `httpx.MockTransport` for MCP-to-backend HTTP in `agent/tests/test_tools.py` and `agent/tests/test_backend_client.py`.
- pytest `monkeypatch` for Sarvam/provider functions and settings in `backend/tests/test_farm_state.py` and `backend/tests/test_sarvam.py`.

**Patterns:**
```python
async def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/v1/weather":
        return httpx.Response(200, json={"provider": "test"})
    return httpx.Response(404, json={"detail": "not found"})

client = BackendClient(settings, transport=httpx.MockTransport(handler))
```
Pattern source: `agent/tests/test_tools.py`.

```javascript
vi.mock('../../../context/AIConversationContext.jsx', () => ({
  useAIConversation: () => ({ messages: [...], speakMessage: mocks.speakMessage }),
}));
```
Pattern source: `src/components/features/ai/ConversationView.test.jsx`.

**What to Mock:**
- External network/provider calls, Mongo-backed repositories when testing pure selection logic, Codex child processes, microphone/media APIs, and time-sensitive boundaries.
- Mock Sarvam at `backend/app/services/sarvam.py`, weather at `backend/app/services/weather.py`, and HTTP at `agent/src/kisansathi_agent/backend_client.py`, not deep inside response-conversion logic.

**What NOT to Mock:**
- SQLite schema, foreign-key isolation, idempotency behavior, rule evaluation, Pydantic validation, HTTP status/error envelopes, MCP result bounding, and Electron preload exposure.
- Do not mock `FarmStateStore` in core farm-state integration tests; use a temporary real SQLite file as in `backend/tests/test_farm_state.py`.
- Do not use the runtime sample data in `src/data/` or seeded records in `src/db/localDatabase.js` as test fixtures; define explicit test-owned inputs.

## Fixtures and Factories

**Test Data:**
```python
def _boundary() -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[[73.8, 18.5], [73.81, 18.5], [73.81, 18.51], [73.8, 18.5]]],
    }
```
Pattern source: `backend/tests/test_farm_state.py`.

```javascript
class FakeProcess extends EventEmitter {
  receive(line) {
    const message = JSON.parse(line);
    if (message.method === 'initialize') this.reply(message.id, { serverInfo: { name: 'fake-codex' } });
  }
}
```
Pattern source: `tests/desktop/codex-harness.test.cjs`.

**Location:**
- Small helpers remain in the test module (`_client`, `_boundary`, `make_client`, `makeHarness`).
- No shared cross-suite fixture/factory directory currently exists.
- `backend/data/farm_state/demo.sqlite3` and `backend/data/farm_uploads/demo/` are runtime artifacts, not test fixtures, and must not be used as authoritative test data.

## Coverage

**Requirements:** None enforced for KisanSathi. No coverage package, threshold, artifact, or CI gate is configured in `package.json`, `backend/pytest.ini`, or `agent/pyproject.toml`.

**View Coverage:**
```bash
# Not currently available as a repository command.
# Add Vitest coverage and pytest-cov dependencies/configuration before defining these commands.
```

**Current breadth:**
- React: one component behavior only (`src/components/features/ai/ConversationView.test.jsx`).
- Desktop: JSONL lifecycle/recovery/approval and preload security contracts (`tests/desktop/`).
- Backend: selected SQLite isolation/idempotency/irrigation/diagnosis/weather/voice flows, Sarvam payload contracts, universal-data parsing/workflow shape, and one net-realisation formula (`backend/tests/`).
- MCP agent: selected weather, result bounding, error redaction, tool registration, HTTP verbs/idempotency, a small subset of specialized calls, and binary validation (`agent/tests/`).
- The majority of React routes, central Mongo CRUD, ingestion execution, and registered MCP tools have no direct behavior test.

## Test Types

**Unit Tests:**
- Pure market arithmetic in `backend/tests/test_market_rules.py` against `backend/app/services/market.py`.
- Source normalization/parsing in `backend/tests/test_universal_data_sources.py` against `backend/app/scraping/sources.py`.
- MCP output bounding and client error mapping in `agent/tests/test_tools.py` and `agent/tests/test_backend_client.py`.

**Integration Tests:**
- FastAPI `TestClient` plus real temporary SQLite in `backend/tests/test_farm_state.py`.
- MCP tool layer plus mocked HTTP transport in `agent/tests/test_tools.py`.
- Electron harness plus a fake JSONL child process in `tests/desktop/codex-harness.test.cjs`.
- No integration test currently starts MongoDB, exercises Beanie CRUD/ingestion against a real database, or spans React → Electron → Codex → MCP → FastAPI → SQLite.

**E2E Tests:**
- Not used for KisanSathi. There is no root Playwright/Cypress config or browser-driven farmer journey test.
- Upstream Codex has its own integration/e2e assets under `codex/`, but they do not exercise KisanSathi's end-to-end lifecycle.

## Common Patterns

**Async Testing:**
```python
def run(coro):
    return asyncio.run(coro)

def test_weather_uses_coordinates_from_the_selected_field() -> None:
    async def scenario() -> None:
        client = make_client(handler)
        result = await KisanSathiTools(client).get_weather_for_field("field-1")
        assert result["status"] == "ok"
        await client.aclose()
    run(scenario())
```
Pattern source: `agent/tests/test_tools.py`. Preserve this local pattern unless the suite deliberately adopts `pytest-asyncio` fixtures consistently.

**Error Testing:**
```python
with pytest.raises(BackendError) as raised:
    await client.get("/v1/weather")
assert raised.value.code == "weather_provider_unavailable"
assert "secret" not in str(raised.value)
assert raised.value.retryable is True
```
Pattern source: `agent/tests/test_backend_client.py`.

## Required Additions

- Add route/component tests for every screen in `src/routes/index.jsx`, especially empty, loading, unavailable, offline, validation, and unknown-field states.
- Add Mongo integration tests for all public reference CRUD routes and `backend/app/scraping/service.py`, including index uniqueness, unavailable Mongo behavior, pagination, source provenance, and ingestion authorization.
- Add contract tests that enumerate every registration in `agent/src/kisansathi_agent/server.py` and exercise every tool's success, backend error, timeout, result-size bound, and write annotation/idempotency behavior.
- Add multi-step SQLite transaction tests for crop-stage updates, sensor-reading alert creation, report creation, and idempotency record persistence in `backend/app/routers/farm_state.py`.
- Add security tests for spoofed/missing `X-Farmer-ID`, central write authorization once implemented, restricted CORS, upload file cleanup, Electron IPC argument validation, and action confirmation.
- Add one farmer-journey E2E suite covering React/Electron → Codex app-server → KisanSathi MCP → FastAPI → isolated SQLite, with provider fakes at external boundaries only.
- Add CI under `.github/workflows/` to run `npm ci`, lint, UI tests, desktop tests, build, backend tests, agent tests, and scoped Codex plugin compatibility checks. No root CI workflow currently exists.

---

*Testing analysis: 2026-08-20*
