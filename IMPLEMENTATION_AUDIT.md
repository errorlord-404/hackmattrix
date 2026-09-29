# KisanSathi implementation audit

Date: 2026-08-19

## Result

The frontend feature surface is connected to backend contracts and is now
available to the local Codex fork through the KisanSathi MCP plugin.

- Frontend route surface audited: dashboard, fields, map, crop guide, soil,
  weather, irrigation, pest/disease, market, schemes, finance, machinery,
  advisor, voice, reports, and settings/profile.
- Backend OpenAPI paths audited: 58 total; all 26 paths used by the MCP
  feature surface are present.
- MCP tools: 47 registered, farmer identity kept in the trusted launcher
  environment, bounded result envelopes, deterministic idempotency keys for
  writes, and explicit read/write annotations.
- Codex plugin: manifest, MCP config, launcher, and skill instructions pass
  the local plugin validator. A stdio initialize + tools/list smoke exchange
  returned all 44 tools.

## Fixes applied

- Added MCP coverage for farm map, field updates, sensor readings, crop
  catalog, seed/fertilizer recommendations, government scheme catalog and
  eligibility, machinery rentals, market history, advisor sessions/questions,
  crop diagnosis, voice turns, and local profit calculations.
- Added multipart and binary request support to the MCP backend client with
  base64 and payload-size validation.
- Added backend idempotency handling for sensor readings, diagnoses, advisor
  sessions, and advisor messages.
- Removed the irrigation-plan GET side effect. Refreshing a read-only plan no
  longer inserts an unbounded row into SQLite.
- Added regression tests for those behaviors.
- Added an environment-only Sarvam adapter for short-audio speech-to-text,
  Bulbul text-to-speech, translation, direct capability routes, and the
  combined voice-turn flow. No Sarvam key is committed.
- Wired returned Sarvam audio into the browser voice conversation with safe
  playback-failure handling.

## Verification evidence

- `backend`: 14 tests passed.
- `agent`: 10 tests passed.
- Frontend ESLint passed.
- Frontend production build passed.
- Python compileall passed for backend and agent.
- Codex plugin validator passed.
- MCP stdio protocol smoke passed with 47 tools.
- Sarvam route contract tests passed with mocked upstream responses.

## Manual/platform gates

- Diagnosis, advisor, and voice adapters intentionally return explicit
  provider-unavailable states until approved providers and credentials are
  configured; no fabricated result is produced. Sarvam STT/TTS/translation
  becomes active after `SARVAM_API_KEY` and `VOICE_PROVIDER=sarvam` are set.
- `X-Farmer-ID` is a demo/local identity boundary, not authentication. A real
  deployment still needs authenticated identity binding and authorization.
- The frontend finance ledger remains private browser storage. The MCP profit
  tool is an ephemeral calculation and does not claim to read or persist that
  ledger.
- Rust Codex integration tests were not required for this Python/plugin-only
  change. Windows Rust linking still requires the MSVC `link.exe` toolchain.
- The GSD `audit-uat` command could not run because the requested fast path
  intentionally skipped `.planning/phases/*` artifacts; the source, contract,
  test, and stdio audits above were run directly instead.
