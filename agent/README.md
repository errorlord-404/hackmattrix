# KisanSathi MCP agent

This package exposes farmer-scoped MCP tools over local stdio. It wraps the existing FastAPI service; it does not read the frontend, SQLite files, or MongoDB directly.

## Local setup

From the repository root:

```powershell
python -m pip install -e .\agent
$env:KISANSATHI_BACKEND_URL = "http://127.0.0.1:8000"
$env:KISANSATHI_FARMER_ID = "demo"
python -m kisansathi_agent
```

The process writes MCP protocol messages to stdout and diagnostics to stderr. Start the backend first with the commands documented in `backend/README.md` or the repository setup notes.

`agent/agent.env` contains the non-secret local demo defaults and is loaded only
when the corresponding trusted launcher variables are absent. Process
environment values always win. The file points to the FastAPI backend launched
by `scripts/start-demo.ps1`, not the currently degraded legacy container.

## Codex configuration

Copy `config/codex.mcp.example.toml` into the Codex configuration and adjust the absolute `cwd` and farmer ID. The example enables automatic reads and Codex approval for the currently supported idempotent writes: irrigation records, reminders, and reports.

## Identity boundary

`KISANSATHI_FARMER_ID` is trusted launcher configuration and is sent as `X-Farmer-ID` on every backend request. It is deliberately absent from MCP tool schemas. The current backend documents this header as a temporary identity boundary, not production authentication; a production deployment must replace it with authenticated session claims.

## Prompt-only support queries

Codex can answer support questions directly from prompts through the read-only
`query_support_catalog` tool. It fans out to the canonical government-scheme,
machinery-rental, and marketplace APIs and returns a bounded, source-attributed
result. Example prompts:

- “What tractor rentals and farm support schemes are available in Maharashtra?”
- “Find machinery providers near Pune for a rotavator.”
- “Which public listings can help me arrange cold-chain transport in Maharashtra?”

Use `find_nearby_machinery` or `find_nearby_marketplace_listings` when a
farmer-owned field is selected. Directory results are discovery-only; the
farmer must verify contact, price, stock, eligibility, and availability with
the provider or official department.

## Farm-cycle workflow skill

`skills/kisansathi/SKILL.md` is the canonical farmer-agent workflow. The
desktop harness loads it into each new Codex thread, while the portable plugin
ships a mirrored copy. It routes next-crop selection, crop-stage work, crop
health, irrigation, marketplace, harvest, and disaster-support prompts across
the MCP tools.

For next-crop questions, the workflow requires one exact field and combines
recorded crop history, source- and time-labelled soil observations, the short
field forecast, explicitly labelled seasonal web evidence, crop-catalog checks,
market/MSP history, farmer costs, and supplier/logistics constraints. It ranks
the best-supported option under disclosed scenarios; it does not claim a
guaranteed maximum-profit crop.

The app-server session enables live web search for current official evidence.
Farm data still comes from KisanSathi tools: web results cannot overwrite field
state, and any persistent tool call remains farmer-confirmation gated.
