# KisanSathi Codex Plugin

This plugin exposes the shared `agent/` Python MCP server through Codex. The
portable Agent Plugin files are `plugin.json` and `mcp.json`; the hidden
Codex files remain as compatibility metadata for the current local fork.
The launcher reads `KISANSATHI_BACKEND_URL` and `KISANSATHI_FARMER_ID` from
the trusted process environment.

Install the agent package once from the repository root:

```powershell
python -m pip install -e .\agent
```

Start the backend, set `KISANSATHI_FARMER_ID`, and enable this plugin from the
fork's plugin discovery path. Writes should remain approval-gated in Codex.

For direct Codex CLI use during local development, register the same canonical
server without modifying the plugin source:

```powershell
$env:KISANSATHI_FARMER_ID = "your-trusted-farmer-id"
codex mcp add kisansathi --env KISANSATHI_BACKEND_URL=http://127.0.0.1:8000 --env KISANSATHI_FARMER_ID=$env:KISANSATHI_FARMER_ID -- python -m kisansathi_agent
codex mcp list
```

This MCP server offers farm reads and approval-gated record writes only. It
cannot actuate irrigation, book equipment, make payments, or provide CNN/ML
crop-health inference until those separately gated modules are ready.

For prompt-only discovery, the server registers `query_support_catalog`, which
queries the live scheme, machinery, and marketplace reference APIs in one
bounded read. Codex should call it for questions such as “find tractor rentals
and farm-support schemes in Maharashtra,” then answer with the returned source
and freshness metadata. Use the nearby tools when a selected field is needed;
all directory results remain discovery-only.

The plugin also contains the `kisansathi` workflow skill. It defines the
complete crop-cycle orchestration: field and history binding, soil evidence,
short-range versus seasonal weather, crop rotation, market/profit scenarios,
stage actions, crop-health triage, irrigation, disaster support, harvest, and
post-harvest discovery. The desktop harness loads the canonical copy from
`agent/skills/kisansathi/SKILL.md` when it starts a new private Codex thread.
