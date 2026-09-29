---
phase: 07-standalone-kisan-sathi-web-service-migration
plan: 08
status: complete
completed: 2026-09-18
---

# Plan 07-08 Summary: Standalone authenticated browser shell

## Delivered

- Added a pinned standalone browser lockfile and root/web verification scripts.
- Added same-origin credentialed HTTP transport with request IDs, CSRF handling for unsafe commands, bounded errors, and caller-supplied idempotency support.
- Added server-owned session login/session/logout clients and an authenticated route gate. The browser stores no bearer token, provider secret, farmer identity, or tenant selector.
- Added typed harness commands for session start/resume/status, text turns, cancellation, approval/clarification responses, and resumable SSE using `Last-Event-ID`.
- Added transport-neutral conversation state with sequence deduplication, stable event handling, approval/degraded/reconnect state, and no Electron/Codex bridge assumptions.
- Added browser standalone scanning/linting and an accessible auth-gate test.

## Verification

- `npm run test` — **8 passed**.
- `npm run lint` — **13 files checked**.
- `npm run check:standalone` — **PASS**.
- `npm run build` — **Vite production build PASS**.
- `python scripts/check_standalone_boundary.py --root . --manifest docs/MIGRATION_MANIFEST.md --standalone-copy-check --check` — **PASS**.
- Combined API/auth compatibility gate — **41 passed**.

## Scope note

Farm workflow pages, voice/image UX, and CV routing remain owned by later Phase 07 plans. This shell is ready to host those routes without reintroducing Electron IPC or browser-selected identity.

