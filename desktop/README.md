# KisanSathi Desktop Harness

This Electron companion keeps the React app as the manual farm interface and routes its farmer chat through the local `codex app-server` process and the KisanSathi MCP plugin.

## Run locally

1. For the repeatable presentation path, run `npm run demo:desktop` (add `-ResetDemo` to the PowerShell command when a clean fixture is required). Use `npm run demo:check` to verify a running backend without opening Electron.
2. Start the FastAPI backend with its normal local configuration when using the manual path. Set `SARVAM_API_KEY` when voice transcription, translation, or speech output is required.
3. Ensure the `codex` executable is on `PATH` and is signed in. Set `CODEX_BINARY` when using a different executable.
4. The desktop process injects the local KisanSathi MCP launcher into that one Codex app-server session. It does not modify global Codex configuration. The launcher inherits `KISANSATHI_AGENT_ROOT`, `KISANSATHI_BACKEND_URL`, and `KISANSATHI_FARMER_ID` from the desktop process.
5. Run `npm run desktop:dev` for development, or `npm run desktop:build` to build the frontend and open Electron.

The harness uses `KISANSATHI_FARMER_ID=demo` by default. Override it only in the local launch environment. It never accepts a farmer identity from the chat model or renderer.

## Operational behavior

- Voice and typed local-language input go through Sarvam translation before the Codex turn.
- Codex thread IDs are stored locally so the companion can resume the farmer's conversation after a restart.
- Crop images are passed to Codex as local image inputs when supported; unsupported vision turns fall back to the existing diagnosis service.
- Codex receives farmer-scoped KisanSathi MCP tools and must ask before any persistent write.
- Tool results, normalized write actions, warnings, and write approvals appear in the chat. Manual screens remain available to check the saved farm state.
- Settings includes a connection status card for Codex, the local plugin, the farm service, and Sarvam, without displaying the trusted farmer ID.
- If Codex or Sarvam is unavailable, the UI reports the reason and leaves manual workflows usable.

## Verification

`npm run lint`, `npm run build`, `npm run test:desktop`, and `npm run test:ui` cover the renderer and desktop harness. The backend and MCP agent retain their Python test suites. Rust/Codex source is intentionally not compiled by this project workflow; install and sign in to the Codex CLI separately before launching the companion.
