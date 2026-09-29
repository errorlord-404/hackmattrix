# KisanSathi MCP Agent Implementation Plan

**Status:** First vertical slice implemented; remaining phases pending  
**Date:** 2026-08-18  
**Goal:** Make the farming application fully usable through a conversational Codex agent, without requiring the React frontend.

## 1. Target outcome

A farmer can talk to the agent in natural language and the agent can safely:

- read the farmer's profile, fields, crops, soil data, sensor readings, weather, alerts, reminders, reports, and market data;
- explain recommendations using the provenance and confidence already returned by the backend;
- record approved changes such as a field, crop stage, soil test, irrigation event, or reminder;
- create reports and guide the farmer through multi-step workflows;
- clearly report unavailable or stale data instead of inventing an answer;
- operate through Codex CLI initially and through a custom headless chat client later.

The React frontend remains available as an optional visual dashboard, but it is not part of the agent's execution path.

### Current implementation checkpoint

The repository now contains the standalone `agent/` package with 28 MCP tools: farmer-scoped reads plus approved, idempotent writes for profile, fields, crop cycles, soil tests, irrigation records, reminders, reports, and alert status. The remaining plan items are provider-backed diagnosis/voice, authenticated identity, physical/financial actions, and a dedicated App Server UI/client.

## 2. Recommended architecture

```text
Farmer
  |
  v
Codex CLI or headless chat client
  |
  | natural-language reasoning, approvals, conversation state
  v
Codex runtime / App Server
  |
  | MCP over local stdio
  v
KisanSathi MCP server (new Python package)
  |
  | validated HTTP requests with a session-bound farmer identity
  v
Existing FastAPI backend
  |-- per-farmer SQLite state
  |-- shared MongoDB reference data
  `-- weather and data-provider adapters
```

### Architectural decisions

1. **Build a separate MCP server, not farming tools inside `codex-core`.** This keeps the Codex fork maintainable, allows the farming tools to be tested independently, and follows the fork's instruction to avoid introducing new domain concepts into core.
2. **Wrap the existing FastAPI API.** The API remains the single owner of validation, persistence, farm rules, and provider access. MCP tools must not access SQLite or MongoDB directly.
3. **Use MCP stdio for the first version.** It is local, simple, and supported by Codex. Do not depend on experimental App Server dynamic tools or WebSocket transport for the MVP.
4. **Use Codex as the agent runtime.** Do not send agent requests through the backend's `/v1/advisor` endpoint; that endpoint is currently a provider-unavailable stub and would create an unnecessary second agent layer.
5. **Bind farmer identity outside the model.** The launcher supplies one trusted farmer ID to the MCP server. No tool accepts `farmer_id` as a model-controlled argument.
6. **Treat tools according to risk.** Reads can run automatically. Persistent mutations require approval. Future physical, purchasing, or financial actions require explicit confirmation immediately before execution.

## 3. Proposed repository layout

Create a top-level package so agent logic does not become backend business logic:

```text
agent/
  README.md
  pyproject.toml
  .env.example
  config/
    codex.mcp.example.toml
  src/kisansathi_agent/
    __init__.py
    __main__.py
    server.py
    config.py
    context.py
    backend_client.py
    errors.py
    policy.py
    result.py
    tools/
      farm.py
      crop.py
      soil.py
      weather.py
      irrigation.py
      alerts.py
      market.py
      schemes.py
      reports.py
  skills/kisansathi/
    SKILL.md
  tests/
    contract/
    integration/
    scenarios/
```

The backend continues to own all API schemas and domain rules. The agent package owns tool schemas, API orchestration, output shaping, approval metadata, and agent instructions.

## 4. Tool contract

Expose task-oriented tools rather than a one-to-one dump of every REST endpoint. Each result must use a common envelope containing `status`, `summary`, `data`, `source`, `observed_at`, `freshness`, `confidence`, `warnings`, and `next_actions` where applicable.

### Phase-one read tools

| MCP tool | Backend API or orchestration | Approval |
|---|---|---|
| `get_farm_overview` | `/v1/dashboard` plus profile/field context | None |
| `get_profile` | `GET /v1/profile` | None |
| `list_fields` | `GET /v1/fields` | None |
| `get_field_timeline` | `GET /v1/fields/{field_id}/timeline` | None |
| `get_soil_health` | `GET /v1/fields/{field_id}/soil-health` | None |
| `get_latest_field_observations` | `GET /v1/fields/{field_id}/latest-observations` | None |
| `get_weather_for_field` | Resolve field coordinates, then call `/v1/weather` | None |
| `get_weather_alerts_for_field` | Resolve field coordinates, then call `/v1/weather/alerts` | None |
| `get_irrigation_advice` | `/v1/fields/{field_id}/irrigation-plan` after its read contract is fixed | None |
| `list_alerts` | `GET /v1/alerts` | None |
| `list_reminders` | `GET /v1/reminders` | None |
| `get_market_summary` | `GET /market-prices/summary` | None |
| `get_market_trend` | `GET /market-prices/trend` | None |
| `compare_mandis` | `GET /market-prices/compare/{crop}` | None |
| `get_msp` | MSP read endpoints | None |
| `find_government_schemes` | state and eligibility read endpoints | None |
| `list_reports` | `GET /v1/reports` | None |

### Phase-two mutation tools

| MCP tool | Backend API | Policy |
|---|---|---|
| `update_profile` | `PUT /v1/profile` | Show changed fields and request approval |
| `create_field` | `POST /v1/fields` | Confirm name, area, and geometry summary |
| `update_field` | `PATCH /v1/fields/{field_id}` | Confirm changed fields |
| `start_crop_cycle` | crop-cycle create endpoint | Confirm field, crop, variety, and sowing date |
| `update_crop_stage` | crop-stage update endpoint | Confirm old and new stage |
| `record_soil_test` | soil-test create endpoint | Confirm units and flag implausible values |
| `record_irrigation_event` | irrigation-event endpoint | Confirm field, amount, method, and time |
| `create_reminder` | `POST /v1/reminders` | Confirm schedule and timezone |
| `update_alert_status` | `PATCH /v1/alerts/{alert_id}` | Confirm acknowledgement or resolution |
| `create_report` | `POST /v1/reports` | Confirm requested report type |

Do not expose central crop, market, MSP, seed, disease, fertilizer, or scheme administration endpoints to a farmer-facing agent. Do not expose deletion tools in the MVP.

### Deferred tools

- diagnosis from image, after a real provider and safe image-transfer contract exist;
- voice input/output, after speech providers are configured;
- automatic sensor ingestion, which should use a device-authenticated path rather than conversational tools;
- pump or machinery control, purchases, loans, subsidy submission, or produce sales;
- autonomous background actions and notifications.

## 5. Safety and trust rules

- The MCP process receives `KISANSATHI_FARMER_ID` from trusted launcher configuration and attaches it as `X-Farmer-ID` on every farmer-state request.
- Tool arguments never contain raw backend URLs, headers, tokens, SQL, collection names, or arbitrary paths.
- Market, weather, MSP, and scheme responses always preserve source and freshness metadata.
- Missing provider data produces an explicit degraded result. The model must not fill missing observations with general knowledge.
- Tool descriptions distinguish recorded facts, deterministic screening guidance, and model-generated explanation.
- All mutations carry an idempotency key. Backend endpoints that do not currently enforce idempotency must be upgraded before the corresponding tool is enabled.
- Responses and logs redact ingestion tokens, provider secrets, precise credentials, and unnecessary personal data.
- Output size is bounded and paginated; the model receives summaries plus identifiers for follow-up calls.
- Read-only tool annotations are used only for genuinely side-effect-free operations.
- No physical or financial action can be inferred from a prior general confirmation.

## 6. Implementation phases

### Phase 0 — Stabilize backend contracts

**Purpose:** Remove known blockers before placing an agent in front of the API.

Tasks:

1. Fix the weather router's missing settings import and add a weather cache-path test.
2. Split irrigation calculation from persistence: a read-only advice endpoint must not create a plan row on every GET. Add an explicit endpoint if the farmer chooses to save a plan.
3. Make weather snapshot lookup field/location-specific rather than selecting the latest snapshot globally within a farmer database.
4. Add real idempotency enforcement for supported mutation endpoints.
5. Standardize API errors with a stable code, safe message, retryability, and request ID.
6. Add request-ID middleware and structured logs.
7. Add bounded pagination to list endpoints used by tools.
8. Document which endpoints work when MongoDB or external providers are unavailable.

Acceptance criteria:

- Backend tests pass.
- Every intended read tool maps to a side-effect-free endpoint.
- Replaying a mutation with the same idempotency key does not duplicate state.
- Weather, MongoDB, and validation failures have machine-readable responses.

### Phase 1 — Build the MCP foundation

**Purpose:** Establish a small, testable server with no domain duplication.

Tasks:

1. Create the `agent/` Python package and pin the supported Python/MCP dependencies.
2. Implement configuration for backend URL, farmer ID, timeouts, retry limits, locale, and log level.
3. Implement one asynchronous backend client that attaches identity, request IDs, and idempotency keys.
4. Map backend failures into typed MCP-safe errors.
5. Implement the common result envelope and bounded serialization.
6. Start an MCP stdio server with health/version resources and structured stderr logging; reserve stdout for protocol messages.
7. Add `get_profile` and `list_fields` as the first vertical slice.

Acceptance criteria:

- Codex can start the server, list its tools, and call the two tools.
- The model cannot choose or override the farmer identity.
- Backend secrets and stack traces never appear in tool output.
- A failed backend call is clear, retryable when appropriate, and does not crash the MCP process.

### Phase 2 — Add read-only farmer intelligence

**Purpose:** Support useful conversations before enabling writes.

Tasks:

1. Add farm overview, field timeline, soil health, latest observations, alerts, and reminders.
2. Add field-aware weather and weather-alert tools. Resolve coordinates inside the MCP server from the selected field.
3. Add irrigation advice after the backend read contract is corrected.
4. Add market summary/trend/comparison, MSP, and government-scheme tools.
5. Add report listing and reading with output limits.
6. Annotate all verified reads as read-only and enable safe parallel calls.

Acceptance criteria:

- A farmer can ask, “What needs attention on my farm today?” and receive an evidence-backed summary assembled from relevant tools.
- Tool results retain source, timestamp, freshness, assumptions, and confidence.
- Unknown field/crop names cause a clarification or candidate list, not a guessed identifier.
- Cross-farmer isolation tests pass.

### Phase 3 — Add controlled mutations

**Purpose:** Let the agent maintain farm records while keeping the farmer in control.

Tasks:

1. Implement profile, field, crop cycle/stage, soil test, irrigation event, reminder, alert, and report mutations.
2. Configure per-tool Codex approval rules; default the MCP server to approval for writes.
3. Return a human-readable preview before each tool call and a concise before/after result afterward.
4. Enforce idempotency and test retry behavior.
5. Add domain validation at both MCP schema and backend layers without duplicating decision rules.

Acceptance criteria:

- No persistent mutation runs without the configured approval.
- Cancelling approval leaves state unchanged.
- Retrying an approved call cannot create duplicates.
- Every mutation is traceable through request ID, farmer context, tool name, and timestamp.

### Phase 4 — Add KisanSathi agent behavior

**Purpose:** Turn a collection of tools into a consistent farming assistant.

Tasks:

1. Create `agent/skills/kisansathi/SKILL.md` with workflow, safety, provenance, and response rules.
2. Instruct the agent to gather farm context before advice, distinguish facts from general guidance, and ask only for missing information required for an action.
3. Define multilingual behavior: preserve crop, location, units, and proper names while answering in the farmer's chosen language.
4. Add example Codex MCP configuration with only the approved farmer tool allow-list.
5. Add conversation scenarios for daily briefing, irrigation, market comparison, scheme discovery, record updates, and degraded providers.

Acceptance criteria:

- The agent chooses task-oriented tools consistently and does not use backend endpoints directly.
- It never claims an operation succeeded until the tool confirms it.
- It explains recommendation rationale, uncertainty, and source in farmer-friendly language.
- The same workflows work from Codex CLI without opening the frontend.

### Phase 5 — Add a headless chat application

**Purpose:** Provide a dedicated ChatGPT-like experience while retaining Codex as the runtime.

Tasks:

1. Build a small client around `codex app-server` using its initialize, thread, turn, streamed item, and approval lifecycle.
2. Use stdio JSONL for the first production-capable client transport.
3. Persist only application thread identifiers and user preferences; leave conversation execution to App Server.
4. Surface tool calls, citations/provenance, progress, approvals, recoverable errors, and cancellation.
5. Generate protocol types from the fork's App Server schema rather than hand-maintaining them.
6. Keep experimental WebSocket support behind a development flag only.

Acceptance criteria:

- A user can start/resume a conversation, stream an answer, approve or reject a write, and cancel a turn.
- The client works with the MCP tool server and existing FastAPI backend while the React frontend is stopped.
- App Server errors and MCP failures are presented without losing the conversation thread.

### Phase 6 — Providers and high-risk capabilities

Implement only after the core workflow is stable:

1. Add a real diagnosis provider and evaluated image workflow.
2. Add speech-to-text and text-to-speech providers.
3. Add device authentication and sensor ingestion outside the chat tool path.
4. Design explicit authorization, confirmation, limits, and emergency stops before any physical or financial integration.

## 7. Verification strategy

### Automated tests

- **Backend contract tests:** endpoint shape, error envelope, idempotency, pagination, and no side effects on GET.
- **MCP schema tests:** unique names, bounded descriptions, valid input/output schemas, correct annotations, and no farmer-ID argument.
- **Client tests:** headers, timeouts, retry rules, error mapping, redaction, and response caps using mocked HTTP transport.
- **Integration tests:** launch the MCP server over stdio, list tools, call each tool against a FastAPI test instance, and verify SQLite state.
- **Isolation tests:** identical calls from two configured MCP processes never cross farmer databases.
- **Safety tests:** prompt-injection strings in market/scheme/provider data remain untrusted data and cannot alter tool policy.
- **Scenario evaluations:** verify expected tool selection, required approvals, grounded responses, and degraded-mode behavior.

### Required end-to-end scenarios

1. “Give me today's farm briefing.”
2. “Does field A need irrigation, and why?”
3. “Where should I sell this crop?”
4. “Which schemes might apply to me?”
5. “I irrigated field A with 20 mm this morning”—preview, approve, record, and verify.
6. Weather unavailable, MongoDB unavailable, and no soil observation available.
7. An attempted request to read another farmer's data.
8. A duplicate mutation after a timeout.

## 8. Delivery order

Deliver in vertical slices:

1. Phase 0 backend contract fixes.
2. MCP process plus `get_profile` and `list_fields`.
3. Daily farm briefing using read-only tools.
4. Irrigation and soil workflow.
5. Market and scheme workflow.
6. One approved mutation workflow: record irrigation.
7. Remaining safe mutations.
8. KisanSathi skill and full scenario evaluation.
9. Dedicated App Server chat client.
10. Voice, diagnosis, devices, and high-risk integrations.

This order proves the complete path early—farmer conversation → Codex → MCP → FastAPI → farmer data—before expanding the tool surface.

## 9. MVP definition of done

The MCP-agent MVP is complete when:

- it runs without the React frontend;
- a configured farmer can complete the eight end-to-end scenarios above;
- all read answers are grounded in tool output and preserve provenance/freshness;
- all state changes require approval, are idempotent, and are auditable;
- farmer isolation, degraded provider behavior, and prompt-injection tests pass;
- no changes to `codex-core` are required;
- setup is documented for starting FastAPI, registering the MCP stdio server with Codex, and beginning a conversation.

## 10. Explicit non-goals for the MVP

- Replacing FastAPI with MCP.
- Reimplementing backend rules inside the agent.
- Using the frontend's browser-specific API client in the headless process.
- Autonomous purchases, financial transactions, government submissions, or equipment control.
- Training a custom model.
- Making App Server's experimental WebSocket or dynamic-tool APIs a production dependency.

## 11. Reference implementation surfaces

- Backend entry point: `backend/app/main.py`
- Backend farmer-state routes: `backend/app/api/v1/farm_state.py`
- Backend assistant stubs: `backend/app/api/v1/assistants.py`
- Farmer identity boundary: `backend/app/farm_state/dependencies.py`
- Current frontend API inventory: `src/api/farmStateApi.js` and `src/api/referenceApi.js`
- Codex MCP configuration: `codex/codex-rs/config/src/mcp_types.rs`
- Codex MCP handler: `codex/codex-rs/core/src/tools/handlers/mcp.rs`
- Codex App Server protocol: `codex/codex-rs/app-server/README.md`

Official architecture references:

- [Codex MCP documentation](https://developers.openai.com/codex/mcp/)
- [Codex App Server documentation](https://developers.openai.com/codex/app-server/)
