# Codex MCP Integration Research: KisanSathi

**Project:** KisanSathi Codex integration track  
**Researched:** 2026-08-19  
**Scope:** Package the existing Python KisanSathi MCP server for this Codex fork without adding farming-specific behavior to Codex's Rust runtime.  
**Overall confidence:** MEDIUM — the local implementation and Codex loader paths were inspected directly; the Python tests pass; Rust validation is currently blocked by the local MSVC linker installation.

## Executive Recommendation

Use the existing KisanSathi server as an external stdio process. Do not copy its Python implementation into `codex-mcp`, `codex-core`, or `core-plugins`: this fork already has the transport, lifecycle, plugin-manifest, policy, and connection-manager boundaries needed to launch an arbitrary stdio MCP server.

The implementation-ready sequence is:

1. Prove the runtime with the existing native Codex configuration in `agent/config/codex.mcp.example.toml`. Install `agent` into the selected Python environment, start the FastAPI backend, provide a farmer ID, and run Codex against the resulting `[mcp_servers.kisansathi]` entry.
2. For distribution, make `agent/` (or a packaging directory containing the same source) a portable Agent Plugin root with root-level `plugin.json` and `mcp.json`. Keep the Python source as the single source of truth; do not maintain a second copy under the Rust tree.
3. Solve the two packaging gaps before publishing: reproducible Python dependencies and user-specific farmer identity. A portable plugin manifest can carry literal package configuration, but it is not a secure secret/identity injection mechanism.

The direct configuration path is the shortest route to a working Codex integration. The Agent Plugin path is appropriate only after the launcher, environment, backend contract, and identity boundary are made reproducible on each supported platform.

## Existing KisanSathi Server

| Concern | Exact source | Finding and integration consequence |
|---|---|---|
| Package metadata | `agent/pyproject.toml:5-28` | Package is `kisansathi-agent`, Python `>=3.11`, `src/` layout. Runtime dependencies are `httpx>=0.27,<1`, `mcp>=1.29,<1.30`, and `pydantic>=2.7,<3`; `pytest>=8` is a dev dependency. The console entry point is `kisansathi-mcp`. |
| Process entry point | `agent/src/kisansathi_agent/__main__.py:11-21` | Builds settings and an async backend client, creates the FastMCP server, and calls `server.run("stdio")`. Logging is configured for diagnostics; stdout must remain MCP protocol data. |
| Environment contract | `agent/src/kisansathi_agent/config.py:11-49` | `KISANSATHI_BACKEND_URL` defaults to `http://127.0.0.1:8000`; `KISANSATHI_FARMER_ID` is mandatory. Farmer IDs are restricted to 1–64 ASCII characters (`[A-Za-z0-9._-]` with an alphanumeric start). Backend timeout defaults to 20 seconds and response output is bounded. |
| Backend boundary | `agent/src/kisansathi_agent/backend_client.py:20-124` | Every request sends `X-Farmer-ID` and a generated `X-Request-ID`; writes also send an idempotency key. The MCP server does not access frontend state or the databases directly. |
| Tool surface | `agent/src/kisansathi_agent/server.py:13-75` | The server registers farmer-scoped read tools plus mutation tools for reminders, reports, profiles, fields, crop cycles, soil tests, and alert status. Tools do not accept `farmer_id`; identity stays in launcher configuration. |
| Safety metadata | `agent/src/kisansathi_agent/server.py:13-24` | Reads advertise read-only/idempotent behavior. Writes are non-read-only but non-destructive and idempotent. This maps naturally to Codex's write approval mode. |
| Tool behavior/tests | `agent/src/kisansathi_agent/tools.py:13-74`, `agent/tests/test_tools.py` | HTTP verbs, bounded results, deterministic idempotency, weather coordinate lookup, degraded responses, and tool safety metadata are already tested. |
| Conversation guidance | `agent/skills/kisansathi/SKILL.md` | The skill requires treating tool results as authoritative for recorded facts, distinguishing stale/provider-unavailable data, and never claiming that advice actuated equipment. If packaged, include this skill under the plugin's `skills/` directory. |
| Existing launch recipe | `agent/README.md:1-24`, `agent/config/codex.mcp.example.toml:1-12` | The documented flow is `python -m pip install -e .\agent`, set backend URL and farmer ID, then run `python -m kisansathi_agent`. The example uses `cwd` to point at `agent`, `required = true`, 10-second startup, 30-second tool timeout, and `default_tools_approval_mode = "writes"`. |

The existing implementation is therefore already shaped for Codex: one long-lived stdio process, no stdout logging, explicit timeouts, bounded output, and server-side farmer scoping.

## Codex Integration Surface

### Native MCP configuration

`codex/codex-rs/config/src/mcp_types.rs:180-251,293-493,512-546` defines the native `[mcp_servers.<name>]` format. For a stdio server it accepts `command`, `args`, `env`, `env_vars`, and `cwd`; it rejects URL/HTTP-only fields and defaults the environment ID to `local`. It also owns `required`, `startup_timeout_sec`, `tool_timeout_sec`, tool filters, and `default_tools_approval_mode`.

The current example is valid for this path:

```toml
[mcp_servers.kisansathi]
command = "python"
args = ["-m", "kisansathi_agent"]
cwd = "C:\\path\\to\\sih mvp\\agent"
required = true
startup_timeout_sec = 10
tool_timeout_sec = 30
default_tools_approval_mode = "writes"

[mcp_servers.kisansathi.env]
KISANSATHI_BACKEND_URL = "http://127.0.0.1:8000"
KISANSATHI_FARMER_ID = "demo"
```

For the first integration test, use this native configuration with an absolute local `cwd`. It is intentionally a local-development configuration, not a portable plugin manifest.

### Existing runtime path

`codex/codex-rs/codex-mcp/src/rmcp_client.rs:81-93` supplies default startup/tool timeouts and launches local stdio servers through the existing RMCP local launcher. `codex/codex-rs/codex-mcp/src/connection_manager.rs:193-244` owns connection aggregation, lazy startup, caching, and server lookup. `codex/codex-rs/codex-mcp/src/connection_manager/required.rs:10-59` turns a failed required server into a startup error.

No KisanSathi-specific branch is needed in these files. The server should enter through configuration and flow through the same connection manager as every other MCP server.

### Agent Plugin packaging

The fork has a stricter portable-plugin path than native config:

- `codex/codex-rs/core-plugins/src/agent_plugin_manifest.rs:16-28,63-196,219-235` expects an Agent Plugin `plugin.json`, validates the canonical schema, fixes the skill directory to `./skills`, fixes MCP configuration to root `./mcp.json`, and validates a lowercase plugin name of at most 64 characters.
- `codex/codex-rs/codex-mcp/src/agent_plugin_config.rs:13-16,38-148` parses the canonical MCP schema and supports stdio and Streamable HTTP. Legacy SSE is rejected by Codex.
- `codex/codex-rs/codex-mcp/src/agent_plugin_config.rs:150-245,349-428` requires a stdio command to be either a bare executable such as `python` or a plugin-relative command such as `./bin/kisansathi`; it rejects arbitrary absolute/external executable paths. `cwd` must remain under the plugin root or `${PLUGIN_DATA}`. Supported placeholders are `${PLUGIN_ROOT}` and `${PLUGIN_DATA}`.
- `codex/codex-rs/codex-mcp/src/agent_plugin_config.rs:245-331` validates HTTP URLs and rejects unsafe non-loopback plain HTTP. This is irrelevant to the recommended local stdio path but matters if the server is later hosted remotely.
- `codex/codex-rs/core-plugins/src/loader.rs:1491-1598` requires an Agent Plugin MCP file to be a regular non-symlink file contained by the plugin root, and creates an isolated plugin data root for stdio execution.
- `codex/codex-rs/core-plugins/src/loader.rs:920-927,950-966,1438-1488` loads the MCP file through `codex-mcp` and applies user policy overlays. `codex/codex-rs/config/src/types.rs:842-890` shows that plugin policy controls enabled state, approval mode, tool allow/deny lists, and per-tool policy; transport launch settings remain in the plugin manifest/config.

A future distributable layout should be conceptually:

```text
<plugin-root>/
  plugin.json
  mcp.json
  pyproject.toml
  src/kisansathi_agent/...
  skills/kisansathi/SKILL.md
  bin/<platform-launcher>
```

The root-level `mcp.json` should use `type: "stdio"`, a bare `python` only for a controlled development environment, or a plugin-relative launcher for a distributable package. It must not point `cwd` outside the plugin root. If the existing `agent/` directory is made the plugin root, `${PLUGIN_ROOT}/src` can be used as `PYTHONPATH`; otherwise, put the source and launcher inside the new root rather than referencing the sibling `agent/` directory.

The main packaging constraint is identity: `KISANSATHI_FARMER_ID` is required by `config.py`, but Agent Plugin `env` values are literal configuration plus the two supported path placeholders. Do not publish a real farmer ID in `mcp.json`, and do not treat a literal `demo` value as an authentication mechanism. Keep farmer identity in a user-local native config, a trusted per-user launcher, or a future Codex-supported identity bridge.

Also do not put native-only keys such as `required`, `startup_timeout_sec`, `tool_timeout_sec`, or `default_tools_approval_mode` into the portable Agent Plugin MCP file unless the schema explicitly gains them. Configure approval through the plugin policy overlay and use native config for the first local proof. `mcp.json` owns portable transport; Codex user policy owns enablement and tool approval.

## Implementation-Ready Path

### Phase 1: local runtime proof

1. From the repository root, install the package with `python -m pip install -e .\agent`.
2. Start the backend from `backend/` using the repository's documented environment and `uvicorn app.main:app --reload` (or the documented Docker compose setup in `backend/docs/UNIVERSAL_DATA_INGESTION.md:17-37`).
3. Set `KISANSATHI_BACKEND_URL` and a non-production test `KISANSATHI_FARMER_ID` in the Codex process environment or native config.
4. Add the existing example entry to the Codex config, changing the absolute `cwd` to the actual `agent` path and increasing startup timeout to 30 seconds if cold Python imports approach the limit.
5. Exercise `codex mcp list`, inspect the KisanSathi server, and run a read tool before testing writes. Keep `default_tools_approval_mode = "writes"` so mutations require approval.

### Phase 2: portable plugin artifact

1. Choose one plugin root and keep `agent/src`, `agent/pyproject.toml`, tests, and the KisanSathi skill together there. Do not duplicate the Python server under `codex/codex-rs`.
2. Add root `plugin.json` and root `mcp.json` in the packaging phase. Use the exact Agent Plugin schemas and a valid plugin name such as `kisansathi`.
3. Provide a platform-specific, plugin-relative launcher or a documented managed Python environment. A bare `python` command is acceptable for the local proof but is not a reproducible distribution contract because PATH and installed dependencies vary.
4. Add a dependency lock/installation process. The current `pyproject.toml` has version ranges but no lockfile; a published plugin must define how the compatible Python and MCP SDK environment is created.
5. Inject farmer identity outside the published portable manifest. Generate user-local configuration or have a trusted launcher supply it; document that the current `X-Farmer-ID` header is a temporary identity boundary, not production authentication (`agent/README.md`).
6. Register/install the plugin through the fork's existing plugin flow. User policy should enable the plugin and set write approval/tool filters; it should not need a Rust code change.

### Phase 3: fork-level verification

Add focused fixtures/tests only if the packaging phase exposes a regression. The natural test locations already exist: `codex/codex-rs/codex-mcp/src/plugin_config_tests.rs` for command/path/env normalization and `codex/codex-rs/core-plugins/src/loader_tests.rs` for manifest containment, regular-file, and isolated-data-root behavior. A successful integration should not require modifying the connection manager.

## Launch and Dependency Risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| Python environment drift | `agent/pyproject.toml` uses ranges and has no lockfile. `mcp` is pinned to the v1 line (`>=1.29,<1.30`), while the SDK ecosystem is evolving. | Lock the environment for distribution; verify the exact Python and SDK versions in CI. |
| Package not installed | `python -m kisansathi_agent` depends on the editable install or an equivalent `PYTHONPATH`. A plugin user's Python may not see `src/`. | Use a managed venv/launcher or explicitly set plugin-relative `PYTHONPATH`; test from a clean environment. |
| PATH-dependent `python` | Codex's portable plugin validation allows a bare command but a bare command is machine-dependent. | Use `python` only for local development; use a platform-specific plugin-relative launcher for distribution. |
| Required-server startup failure | Native `required = true` makes `codex exec` fail when the process cannot initialize. | Keep required only when backend, environment, and package are guaranteed; otherwise start optional during development. Set startup timeout for cold imports. |
| Backend unavailable | The MCP process can start while the FastAPI service at `127.0.0.1:8000` is down; tools then fail or degrade. | Make backend readiness an explicit preflight and test a real read call, not only MCP initialization. |
| Farmer identity missing or unsafe | `KISANSATHI_FARMER_ID` is mandatory. The current `X-Farmer-ID` header is trusted launcher input and is not production auth. | Keep identity user-local and move production authentication to authenticated backend claims before multi-user release. |
| Stdio protocol corruption | Any diagnostic written to stdout can break the MCP session. | Preserve the current stderr logging behavior and add an integration assertion that stdout contains only protocol traffic. |
| Timeout mismatch | Backend client timeout defaults to 20 seconds; the example Codex tool timeout is 30 seconds. Cold startup and provider calls can consume the remaining margin. | Align backend, Codex startup, and tool timeouts after measuring real calls; 30–60 seconds is a reasonable initial tool window. |
| Windows launch differences | The current development machine uses Windows. Absolute paths work in native config but violate portable plugin containment; `.cmd`/venv behavior needs platform testing. | Validate the actual launcher on Windows and each supported platform; keep commands one-token and plugin-relative in `mcp.json`. |
| Unsafe manifest assumptions | Agent Plugin MCP files must be root-contained regular files; symlinks and external `cwd`/commands are rejected. | Materialize `plugin.json`/`mcp.json` inside the plugin root and test the installed/cache layout. |
| Rust toolchain prerequisite | Codex crate tests currently stop before linking because `link.exe` is absent. | Install Visual Studio Build Tools/MSVC linker and rerun the prescribed `just` commands; this is independent of the Python server. |

## Test and Verification Commands

Run from the repository root for KisanSathi:

```powershell
python -m pip install -e .\agent
python -m pytest agent/tests -q

$env:KISANSATHI_BACKEND_URL = "http://127.0.0.1:8000"
$env:KISANSATHI_FARMER_ID = "demo"
python -m kisansathi_agent
```

The test command was run during this research and passed: **8 passed**. It emitted existing warnings from Pydantic's settings typing and an unset `pytest-asyncio` configuration option.

Run the backend separately as documented:

```powershell
Set-Location backend
uvicorn app.main:app --reload
```

Run from `codex/` for the fork:

```powershell
just fmt-check
just test -p codex-mcp
just test -p codex-core-plugins
```

If a Rust dependency or workspace manifest changes, `codex/AGENTS.md` requires:

```powershell
just bazel-lock-update
```

If config types change, use the repository recipe `just write-config-schema`. Do not use direct `cargo test`; the local instructions require the `just` wrappers. The two crate test commands were attempted during research and both stopped before test execution with `error: linker 'link.exe' not found` for the MSVC target. Install the Visual Studio C++ build tools before treating those results as code failures.

For end-to-end Codex validation after the toolchain and backend are ready:

```powershell
just codex mcp list
just codex mcp get kisansathi
```

Then run a controlled `codex exec` scenario with a temporary Codex home/config, first a read-only query, then an explicitly approved mutation. Verify that the backend records the expected `X-Farmer-ID`, request ID, idempotency key, and no cross-farmer data is returned. Exact plugin-install commands should follow the fork's existing marketplace/install flow rather than inventing a second loader.

## What Should Not Change

- `codex/codex-rs/codex-mcp/src/connection_manager.rs`: no KisanSathi-specific connection path.
- `codex/codex-rs/codex-mcp/src/rmcp_client.rs`: no new launcher; its existing local stdio launcher is the correct boundary.
- `codex/codex-rs/core-plugins/src/loader.rs` and `agent_plugin_manifest.rs`: no special-case plugin loader unless a generic missing capability is demonstrated by a failing fixture.
- `codex/codex-rs/config/src/mcp_types.rs`: no new transport/config fields for the first integration.
- KisanSathi tool identity and safety semantics: preserve the launcher-owned farmer ID and existing write approval behavior.

The only likely Codex-side changes are packaging fixtures, documentation, or narrowly scoped tests. A Rust runtime change would indicate a new requirement such as authenticated identity injection, not ordinary MCP packaging.

## Sources and Confidence

### Direct repository sources — high confidence

- `codex/AGENTS.md` — local build, test, config-schema, and dependency-lock rules.
- `agent/pyproject.toml`, `agent/README.md`, `agent/config/codex.mcp.example.toml` — package, launch, and native Codex configuration contract.
- `agent/src/kisansathi_agent/__main__.py`, `config.py`, `backend_client.py`, `server.py`, `tools.py` — process, identity, HTTP, tool, timeout, and safety behavior.
- `agent/tests/test_tools.py`, `agent/skills/kisansathi/SKILL.md` — existing behavioral coverage and conversation constraints.
- `codex/codex-rs/codex-mcp/src/rmcp_client.rs`, `connection_manager.rs`, `connection_manager/required.rs`, `agent_plugin_config.rs` — MCP lifecycle and portable transport constraints.
- `codex/codex-rs/core-plugins/src/agent_plugin_manifest.rs`, `loader.rs`, `loader_tests.rs`, `manager_tests.rs` — Agent Plugin manifest, containment, policy, and data-root behavior.
- `codex/codex-rs/config/src/mcp_types.rs`, `config_toml.rs`, `types.rs` — native MCP and plugin policy schemas.
- `codex/codex-rs/justfile` — prescribed formatting, tests, lock update, and schema commands.
- `MCP_AGENT_IMPLEMENTATION_PLAN.md` — project-level architecture and required MCP/identity/safety verification scenarios.

### External references — lower confidence, used only to cross-check schema/SDK assumptions

- [Agent Plugins Specification](https://agent-plugins.org/specification) — portable `plugin.json`/`mcp.json`, stdio command, placeholder, and containment conventions. Web-search confidence: LOW; the local Codex parser/tests are authoritative for this fork.
- [MCP Python SDK v1 documentation](https://py.sdk.modelcontextprotocol.io/v1/) and [official Python SDK repository](https://github.com/modelcontextprotocol/python-sdk) — stdio/FastMCP and SDK version-line context. Web-search confidence: LOW; the project's pinned dependency and passing tests are the actionable sources.

## Open Questions for Implementation

- Which marketplace/installation source will own the KisanSathi plugin identifier (`kisansathi@<marketplace>`)? The loader tests show the policy shape, but this research did not change or invent a marketplace entry.
- Will supported users have a managed Python environment, or should the plugin ship a per-platform executable/launcher? This determines whether `python` is acceptable in the final `mcp.json`.
- How will farmer identity be selected and authenticated for multiple users? The current environment/header boundary is suitable for a controlled MVP, not a production multi-tenant trust boundary.
- What backend readiness and provider latency should determine final `startup_timeout_sec` and `tool_timeout_sec` values?
