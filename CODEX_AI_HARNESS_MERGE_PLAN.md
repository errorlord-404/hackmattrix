# Codex CLI + KisanSathi AI Harness: local merge and implementation plan

## Purpose

Turn the existing KisanSathi web application into a local AI harness for the
forked Codex CLI. The Codex fork must expose farmer-scoped KisanSathi tools,
while the FastAPI service remains the only source of farm data and provider
workflows.

This is an implementation plan only. It does not authorize a merge, file move,
or code change by itself.

## Current evidence and starting point

| Area | Current state | Planning consequence |
| --- | --- | --- |
| Repository | One Git worktree on local branch `pranav` at `99e77a3`. `codex/` is a directory in this worktree, not a separate Git repository. | Make one integration branch/worktree from `pranav`; do not try to merge a second Codex repository. |
| Existing merges | `f731f78` merged Prachi's voice work and `84d727a` merged the backend-fastapi work. | Treat those as the baseline; do not re-merge them. |
| Aman branch | Local `aman` still exists and has not been proven to be an ancestor of `pranav`. | Audit it first and merge it once, locally, only if it contains needed work. |
| Working tree | It contains many modified and untracked application, backend, frontend, and `agent/` files. | Preserve these changes before any Git merge. Do not reset, clean, or overwrite them. |
| Backend | `backend/app/main.py` mounts farm-state, weather, assistant, ingestion, machinery, crop, disease, seed, fertilizer, market, MSP, and scheme routers. | The harness calls these HTTP APIs; it does not access SQLite/Mongo files directly. |
| Existing MCP adapter | `agent/` is a Python/FastMCP server. It exposes 28 farmer-scoped tools, keeps farmer identity in launcher configuration, has idempotent writes, and is currently untracked. | Reuse and package this server. Do not duplicate its API client as 28 native Rust handlers. |
| Codex fork | `codex/codex-rs/codex-mcp` owns MCP connections and `codex-rs/core-plugins` loads plugin-owned MCP servers. | Add a KisanSathi plugin bundle to the fork and let the existing MCP connection manager surface the tools. |

## Target architecture

```text
Farmer / operator
       |
Forked Codex CLI
       |
KisanSathi bundled plugin  -- stdio -->  KisanSathi MCP server (`agent/` code)
       |                                      |
       |                              X-Farmer-ID from trusted launcher config
       |                                      |
       +----------------------------------> FastAPI backend
                                                   |
                               local farm state, reference data, providers
```

The plugin owns discovery, tool metadata, and local launch configuration. The
MCP server owns tool schemas, backend calls, result shaping, idempotency, and
safe failure responses. The backend owns data, authorization replacement,
provider calls, and domain logic. The frontend remains a client of the same
backend; it must not become an MCP dependency.

## Architecture decisions

1. **Use a bundled MCP plugin, not native Rust business tools.** The Codex fork
   already supports plugin-owned MCP servers and its contribution rules direct
   MCP tool work through `codex-rs/codex-mcp`. A native Rust tool set would
   duplicate the Python adapter and backend contract, then drift.
2. **Keep farmer identity out of model-provided tool arguments.** The launcher
   supplies `KISANSATHI_FARMER_ID`; the MCP client sends it as `X-Farmer-ID`.
   Replace this development identity boundary with authenticated claims before
   production use.
3. **Separate read, write, and provider-assisted capabilities.** Reads may run
   automatically. State-changing actions require Codex approval and explicit
   farmer confirmation. Provider-dependent diagnosis/advice/voice must return
   `unavailable` or `inconclusive` when the provider is not configured; they
   must never fabricate a result.
4. **Keep sensitive finance data opt-in.** The current finance ledger and
   profit simulator are browser-local. Do not silently copy them to Codex or
   the backend. First ship a stateless calculator; persist a ledger only after
   agreeing a data model, consent rule, retention policy, and authentication.
5. **Do not promise voice/image support until Codex transport is proved.** The
   plugin may expose a text-first advisor initially. Image diagnosis and audio
   turns are released only after an end-to-end test proves safe attachment
   transport, size limits, and redaction behavior.

## Required final plugin layout

Create this inside the Codex fork during implementation. The names below are
the intended ownership boundaries, not a command to move files now.

```text
codex/
  plugins/
    kisansathi/
      plugin.json                         # Portable Agent Plugin manifest
      .codex-plugin/plugin.json           # Codex overlay and UI metadata
      mcp.json                            # stdio KisanSathi server declaration
      skills/kisansathi/SKILL.md          # tool-use, provenance, and safety rules
      server/
        pyproject.toml
        requirements lock/constraints
        run_kisansathi_mcp.py
        src/kisansathi_agent/             # promoted copy of agent source
        tests/
      README.md                           # local setup, environment variables, test flow
  .agents/plugins/marketplace.json        # repo-local marketplace entry, if selected
```

The portable root `plugin.json` must use the Agent Plugins schema that the
fork's `core-plugins` loader accepts. The `.codex-plugin/plugin.json` overlay
must use the valid Codex plugin manifest shape. Keep `mcp.json` next to the
portable manifest because this is the fixed discovery location used by the
fork's Agent Plugin parser.

`mcp.json` should launch a **bare** Python executable with an argument under
`${PLUGIN_ROOT}` and a contained `cwd`; it must not hard-code a developer's
absolute path. `KISANSATHI_FARMER_ID` must be inherited from the trusted local
environment or entered through a future configuration flow, never committed as
a demo identity. `KISANSATHI_BACKEND_URL` defaults to local FastAPI but remains
overridable for a test/development deployment.

## Local-only merge sequence

### Phase 0 — protect the current workspace

1. Record `git status --short`, `git diff --stat`, and the current commit for
   auditability.
2. Create a local, recoverable checkpoint of all tracked and untracked work.
   Use either a named local WIP commit on a dedicated branch or a named stash
   that includes untracked files. Do not use `git reset --hard`, `git clean`,
   or `git checkout --`.
3. Create a second local worktree or an `integration/codex-ai-harness` branch
   from the current `pranav` commit. All merge resolution happens there,
   leaving the present workspace recoverable.
4. Maintain an integration log containing the source commit, resulting commit,
   conflicts, resolution rationale, and validation command for each step.

### Phase 1 — reconcile branches without network operations

1. Verify that Prachi and backend-fastapi work are reachable from the
   integration base with `git merge-base --is-ancestor`. They should be true
   because their merge commits are already in `pranav`.
2. Compare `aman` to the integration base using local-only commands:
   `git log --left-right --cherry-pick`, `git diff --name-status`, and
   `git merge-base`. Categorize each Aman change as already present, required,
   conflicting, or obsolete.
3. If Aman has required commits, execute one explicit local `--no-ff` merge on
   the integration branch. Resolve conflicts feature by feature, preserving the
   currently merged backend compatibility contracts. If it has no required
   commits, document the evidence and do not create an empty merge commit.
4. Promote the current untracked/modified application and backend work in
   reviewable commits rather than one bulk commit. Suggested ordering:

   - `feat(frontend): complete farmer-facing screens and shared API client`
   - `feat(backend): add farm state, assistant, weather, ingestion, and data contracts`
   - `feat(agent): add farmer-scoped KisanSathi MCP adapter`
   - `docs: add integration and operational guidance`

5. Run frontend lint/build and backend tests after each conflict-heavy merge,
   not only at the end.

### Phase 2 — make the adapter a fork-owned plugin

1. Copy or promote the existing `agent/src/kisansathi_agent` and its tests into
   `codex/plugins/kisansathi/server/`. Keep the old root `agent/` only until
   the promoted package passes the same tests; then choose one canonical source
   and remove duplication in a dedicated, reviewable change.
2. Add a small plugin-local launcher that imports only the bundled package and
   writes diagnostics to stderr. It must not alter global Python paths outside
   the plugin root.
3. Pin Python runtime dependencies with compatible bounds/constraints for
   `mcp`, `httpx`, and `pydantic`. Do not bundle a virtual environment or place
   secrets in the plugin.
4. Add the portable plugin manifest, Codex overlay manifest, `mcp.json`, and
   `skills/kisansathi/SKILL.md`. The skill states tool-selection rules,
   freshness/provenance requirements, confirmation requirements, and the
   no-invention policy.
5. Add a repo-local marketplace entry only if the fork's packaged local
   marketplace is the chosen install path. If the product should enable the
   plugin by default, make that a deliberate config-policy change with a Rust
   integration test; do not silently patch a user's global `~/.codex` config.
6. Validate the plugin manifest with the plugin validator and test that the
   fork's `core-plugins` loader resolves `mcp.json` to the expected stdio
   server. Verify tool discovery through `codex-mcp` rather than registering
   individual tools in `codex-core`.

### Phase 3 — close frontend-to-backend-to-MCP coverage

The following matrix is the required end state. A checkmark means the existing
adapter already has a direct tool; “build” means a named capability still needs
to be added and tested before claiming full harness coverage.

| Frontend capability | Backend state | Current MCP state | Harness action |
| --- | --- | --- | --- |
| Dashboard, profile, alerts | Implemented under `/v1` farm state | `get_farm_overview`, `get_profile`, `list_alerts`, `update_profile`, `update_alert_status` | Keep; test farmer isolation and bounded output. |
| Fields, crop cycles, stage history | Implemented | `list_fields`, `get_field`, `create_field`, `start_crop_cycle`, `update_crop_stage`, `get_field_timeline` | Keep; add update/archive field only if the UI permits those operations. |
| Farm map | `/v1/fields/map` implemented | Partial: field boundaries are returned via `list_fields` | Build `get_farm_map` from the map endpoint so map semantics are explicit. |
| Soil health and observations | Implemented | `get_soil_health`, `get_latest_field_observations`, `record_soil_test` | Keep; test source, timestamp, and no fabricated values. |
| Weather | Implemented | `get_weather_for_field`, `get_weather_alerts_for_field` | Keep; prove coordinates only come from the stored field. |
| Irrigation and reminders | Implemented | advice/event/reminder tools | Keep; require confirmation for writes; retain the no-equipment-control guarantee. |
| Crop guide, crop catalog, seeds, fertilizer | Backend has crop/seed/fertilizer APIs and recommendation routes | Missing | Build `list_crops`, `get_crop_guidance`, `recommend_seeds`, and `recommend_fertilizers`; preserve backend recommendation assumptions. |
| Pest and disease | Disease data and assistant diagnosis endpoint exist | Missing | Build a text symptom workflow first; add image diagnosis only after attachment E2E validation. |
| Market, mandi comparison, MSP | Implemented | summary, trend, compare, MSP tools | Keep; return data source, date, pricing unit, and comparison assumptions. |
| Government schemes | List-by-state and eligibility endpoint implemented | `find_government_schemes` only | Extend the list tool to support bounded filters and add `check_scheme_eligibility` with explicit farmer-provided inputs. |
| Machinery rentals | Implemented CRUD/list API | Missing | Build `list_machinery_rentals` with the UI's supported filters; do not create bookings/contact actions unless the backend owns that workflow. |
| AI advisor | Provider-backed backend endpoints implemented | Missing | Build `ask_farm_advisor` and session read/continue tools. Surface provider unavailability verbatim. |
| Voice assistant | Backend voice turn endpoint implemented | Missing | Gate behind a real audio-input transport test. Until then, retain voice in the frontend only and expose a truthful unsupported/degraded response. |
| Reports | Implemented | list/get/create report tools | Keep; ensure created reports are scoped to the launcher's farmer identity. |
| Finance ledger and profit simulator | Browser-local state plus market comparison | Market comparison only | Build a stateless `calculate_farm_finance` tool first. Persisted finance data needs a separate approved backend/privacy design. |
| Language, navigation, display settings | Mostly frontend/local; profile preference is backend-backed | Profile preference read/write available | Do not make translation/navigation tools. Preserve preferred language in tool answers where supported. |

For every new tool:

1. Add a task-oriented method to the Python MCP adapter and a matching backend
   contract if one does not exist.
2. Register the tool with a concise description and correct MCP annotations.
3. Keep list responses bounded and include source/freshness metadata where the
   backend supplies it.
4. Put the farmer identity, credentials, API base URL policy, and timeouts in
   trusted launcher configuration, not in the model schema.
5. Add tool-level tests, backend contract tests, and a Codex discovery/execution
   integration test.

## Tool approval and safety policy

| Class | Examples | Codex behavior |
| --- | --- | --- |
| Read-only | weather, soil, field timeline, market, schemes, map | Auto-approve only after farmer scope has been set; no network/provider result may be presented as more current than its metadata says. |
| Idempotent record write | reminders, irrigation history, reports, profile, crop stage, soil test | Require explicit farmer confirmation plus Codex write approval. Pass an idempotency key and return the resulting record. |
| Sensitive/provider-assisted | diagnosis, advisor, voice, finance persistence | Require confirmation where user content is submitted, strict size/type limits, and clear unavailable/inconclusive responses. |
| Prohibited | pump/valve activation, unapproved booking/payment, silently changing finance data | Do not expose as a tool unless a new backend authorization and safety design is approved. |

## Required tests and release gates

### Application and adapter

1. Frontend lint and production build succeed.
2. Backend tests cover all newly added endpoints, farmer ownership, validation,
   idempotency, and provider-unavailable responses.
3. MCP unit tests cover method/path/payload shaping, no farmer ID in schemas,
   output bounds, tool annotations, and error envelopes.
4. Start FastAPI locally and launch the bundled server over stdio. Perform MCP
   `tools/list` and `tools/call` integration tests against a demo farmer.
5. Repeat key tests for two farmer IDs to prove data cannot cross scopes.

### Codex fork

1. Run formatter from `codex/codex-rs`: `just fmt`.
2. Run the targeted plugin and MCP crates with the repository wrapper, not raw
   `cargo test` (expected packages include `codex-core-plugins` and
   `codex-mcp`; confirm exact targets with `just --list`).
3. Add an integration test proving the plugin manifest is loaded, its stdio
   server starts, the KisanSathi tools are discovered, and a mocked model can
   receive a tool result. Use the fork's existing `test_codex`/Responses mock
   utilities for agent behavior changes.
4. Validate the packaged CLI on Windows, macOS, and Linux path rules. In
   particular, the plugin command must be bare and all plugin-relative paths
   must remain within the plugin root.
5. Keep Rust changes outside `codex-core` unless plugin/MCP abstractions prove
   insufficient. Any Rust configuration schema change requires the fork's
   schema-generation step and an explicit compatibility review.

### Acceptance scenarios

Run the following in a new Codex session after the plugin is installed:

1. “Show my fields, soil status, and weather alerts.”
2. “Compare nearby mandi prices for my crop and explain assumptions.”
3. “Create a reminder for irrigation tomorrow at 7 AM.” Confirm before the
   write and verify it is stored once even when retried.
4. “Record a soil test for field X.” Verify output source/time and farmer scope.
5. “Find schemes for my state and check my eligibility.” Verify the tool asks
   only for the eligibility fields actually required.
6. “What machinery can I rent nearby?” Verify filters map to backend results.
7. “Diagnose these crop symptoms / ask my advisor.” Verify either a sourced
   result or a clear provider-unavailable response.
8. Attempt a second farmer context and prove the first farmer's fields,
   reminders, reports, and finance inputs never appear.

## Commit and review sequence

Keep each change reviewable and under the fork's normal change-size guidance.

1. `chore(integration): preserve WIP and reconcile required local branches`
2. `feat(kisansathi-plugin): package existing MCP server for the Codex fork`
3. `test(kisansathi-plugin): verify manifest, discovery, and stdio launch`
4. `feat(kisansathi-tools): close crop/map/schemes/machinery/advisor coverage`
5. `feat(kisansathi-tools): add validated diagnosis and voice support` (only
   after the attachment transport gate passes)
6. `feat(finance): add approved stateless calculator or separately approved ledger`
7. `test(harness): add end-to-end farmer-isolation and acceptance coverage`
8. `docs(harness): document installation, environment configuration, tool
   policy, troubleshooting, and rollback`

Each commit must state the changed user behavior, tool schemas, backend routes,
test evidence, and any remaining feature gate. Do not mix Aman conflict
resolution, plugin packaging, and new tools in one commit.

## Definition of done

The AI harness is ready only when all of the following are proven:

- The integration branch contains the required Aman work exactly once and
  preserves the existing Prachi/backend merge work.
- The KisanSathi plugin is physically inside `codex/`, validates as a plugin,
  and is loadable by the forked Codex CLI without user-specific hard-coded
  paths or secrets.
- Codex discovers and executes the bundled KisanSathi MCP tools against the
  local FastAPI backend.
- Every backend-backed frontend capability in the coverage matrix has a tested
  MCP tool, or is explicitly frontend-only because it is presentation/local
  behavior (language/navigation). There are no silent gaps.
- Finance persistence, image diagnosis, and voice are either implemented with
  their stated transport/privacy gates or remain clearly marked as intentionally
  deferred—not presented as supported tools.
- Writes require confirmation, preserve farmer isolation, are idempotent where
  applicable, and cannot control machinery or make commitments the backend does
  not authorize.
- Frontend, backend, adapter, plugin-loader, and end-to-end tests pass with
  documented commands and results.
- A clean local rollback path exists: revert only the relevant atomic commit or
  switch away from the integration worktree; do not delete the protected WIP
  checkpoint.

## First implementation checkpoint after plan approval

Implement only the plugin shell and the existing 28 proven adapter tools:
package the agent source under `codex/plugins/kisansathi`, add valid manifests
and local launch configuration, and prove Codex discovers the server. Do not
add new domain tools or merge Aman until that checkpoint passes. This gives a
working harness with the current supported farm functionality before expanding
coverage in controlled stages.
