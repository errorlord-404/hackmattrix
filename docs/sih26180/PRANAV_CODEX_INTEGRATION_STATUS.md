# Pranav — Codex CLI integration status

**Status:** updated on 9 September 2026 for full farm-cycle skill orchestration;
the current non-hardware tool integration is complete, while field validation
and gated ML/hardware releases remain separate work.

## Delivered path

```text
Codex CLI / Codex app-server
  -> KisanSathi plugin (stdio)
  -> Python MCP adapter (`agent/src/kisansathi_agent`)
  -> FastAPI
  -> farmer-scoped SQLite state or shared Mongo/reference data
```

The Python MCP adapter remains the only farming-tool boundary. No KisanSathi
business rules were added to the Codex Rust core. The desktop harness starts
one `codex app-server` process and supplies the plugin launcher, backend URL,
and trusted farmer identity as process configuration.

## Completed artifacts

| Artifact | Purpose |
| --- | --- |
| `agent/src/kisansathi_agent/server.py` | Registers the complete current farmer-tool surface with read/write annotations. |
| `agent/src/kisansathi_agent/tools.py` | Maps tools to FastAPI routes, bounds results, preserves source/freshness warnings, and creates deterministic idempotency keys for writes. |
| `codex/plugins/kisansathi/plugin.json` | Portable Agent Plugin v1 manifest. |
| `codex/plugins/kisansathi/mcp.json` | Portable MCP stdio declaration using `${PLUGIN_ROOT}` and no developer-specific path. |
| `codex/plugins/kisansathi/run_server.py` | Uses a trusted explicit agent source root, repository-local package during development, or a normally installed package. |
| `desktop/codex-harness.cjs` | Starts the local Codex app-server with the KisanSathi server for the desktop companion only; it does not modify global Codex configuration. |
| `agent/skills/kisansathi/SKILL.md` | Canonical decision workflow loaded into every new desktop farmer session. |
| `agent/skills/kisansathi/references/farm-lifecycle-workflow.md` | Detailed next-crop, crop-stage, crop-health, irrigation, disaster, harvest, and market orchestration. |

Current MCP coverage includes farm overview/profile/fields/map, soil and
observations, weather and deterministic irrigation advice, alerts/reminders/
reports, crop/seed/fertilizer reference guidance, markets/MSP/schemes,
machinery/marketplace discovery, advisor/voice provider wrappers, and
ephemeral finance calculations. Every farmer-state call receives the launcher
identity as `X-Farmer-ID`; that identity is not an MCP tool argument.

The desktop session now enables Codex live web search for time-sensitive
official evidence. The workflow requires backend farm state first and permits
web evidence only to fill current public-information gaps such as seasonal
outlooks, sowing windows, advisories, scheme rules, and export requirements.
It explicitly prevents a short weather forecast, web snippet, crop catalog, or
market trend from being presented as a guaranteed seasonal or profit outcome.

## Safety boundary

- Reads are read-only MCP tools. Persistent record writes are marked for
  approval and use backend idempotency where supported.
- Tools can record irrigation history or explain irrigation advice, but cannot
  operate pumps, valves, tractors, machinery, payments, bookings, sales, or
  export filings.
- Provider-backed diagnosis, advisor, voice and translation routes must retain
  their returned unavailable/inconclusive state. They must not invent results.
- Marketplace tools discover source-attributed listings only; they do not
  promise stock, price, eligibility or supplier acceptance.

## Verified evidence

- `PYTHONPATH=src python -m pytest -q` from `agent/`: **12 passed**. This
  includes a live stdio JSON-RPC initialize + `tools/list` check. The server
  lists at least 60 tools and does not expose `farmer_id` in any tool schema.
- `node --test tests/desktop`: **6 passed**.
- A real installed `codex app-server --stdio` startup was completed through
  `desktop/codex-harness.cjs` with the KisanSathi MCP launcher and a trusted
  test farmer identity. This proves process startup and thread creation; it
  does not make a model call or invoke a farming write.
- `codex mcp list --json` with temporary command overrides reported the
  `kisansathi` server. No global MCP configuration was changed by that check.

## Direct CLI setup

Start FastAPI, install the agent package, and use a trusted identity chosen by
the launcher/operator:

```powershell
python -m pip install -e .\agent
$env:KISANSATHI_FARMER_ID = "your-trusted-farmer-id"
codex mcp add kisansathi --env KISANSATHI_BACKEND_URL=http://127.0.0.1:8000 --env KISANSATHI_FARMER_ID=$env:KISANSATHI_FARMER_ID -- python -m kisansathi_agent
codex mcp list
```

Use `codex mcp remove kisansathi` to remove this local registration when it is
no longer needed. The desktop route uses a session-only override instead and
does not write the user’s global config.

## Explicitly deferred

1. Hardware/device ingestion is Aman's backend contract plus Anwaar's firmware
   work. A future read-only device-health tool must wrap that canonical API; it
   must not reuse the human-confirmed `record_sensor_reading` tool.
2. CNN/deep-learning crop health is deferred. Do not expose a predictive vision
   tool until there is one selected crop/region dataset, model card,
   evaluation, confidence threshold, and inconclusive/escalation path.
3. The current `X-Farmer-ID` boundary is not production authentication.
   Replace it with authenticated claims before any network deployment.
