---
phase: 07-standalone-kisan-sathi-web-service-migration
plan: 04
subsystem: auth-isolation
tags: [oidc, pkce, session-cookie, csrf, tenant-isolation, actor-context]
requires: [07-02, 07-03]
provides: [WEB-03, oidc-session-boundary, claims-scoped-persistence, signed-harness-context]
affects: [07-06, 07-07, 07-08, 07-09, 07-11, 07-14, 07-15]
tech_stack:
  added: [PyJWT-2.14.0, shared-kisansathi-auth, fastapi-auth-router]
  patterns: [authorization-code-pkce, secure-cookie-double-submit-csrf, immutable-actorscope, hmac-context]
key_files:
  created:
    - Kisan Sathi Web/services/api/app/auth/internal_context.py
    - Kisan Sathi Web/services/api/app/auth/test_issuer.py
    - Kisan Sathi Web/services/api/app/routers/auth.py
    - Kisan Sathi Web/services/api/tests/test_auth_scope.py
    - Kisan Sathi Web/services/api/tests/test_cross_tenant.py
  modified:
    - Kisan Sathi Web/services/api/app/auth/dependencies.py
    - Kisan Sathi Web/services/api/app/main.py
    - Kisan Sathi Web/services/api/app/routers/domain.py
    - Kisan Sathi Web/services/api/app/routers/reference.py
    - Kisan Sathi Web/services/api/app/settings.py
    - Kisan Sathi Web/docs/MIGRATION_MANIFEST.md
requirements-completed: [WEB-03]
duration: "continued from stalled executor; local implementation and verification"
completed: 2026-09-18
status: complete
---

# Phase 7 Plan 04 Summary

**OIDC/session authentication and claim-scoped tenant isolation are implemented for the standalone API.**

## Accomplishments

- Added `/auth/login`, `/auth/callback`, `/auth/session`, `/auth/logout`, and an explicitly mode-gated `/auth/test/login` route.
- Added server-side Authorization Code + PKCE state/nonce handling, OIDC discovery/JWKS verification, secure HttpOnly session cookies, readable CSRF cookies, revocation, and cookie-authenticated unsafe-method protection.
- Replaced the temporary default farm-state selector with immutable `ActorScope` claims. SQLite paths now resolve from verified `tenant_id` and `farmer_id` claims; the browser/model cannot choose either value.
- Added short-lived audience-bound signed internal actor context with trace binding, method/path binding, nonce replay protection, and no secret/token disclosure to the browser session response.
- Rejected legacy `X-Farmer-ID` and farmer/tenant query selectors at the API boundary, while preserving the configured server bearer compatibility path for existing service deployments.
- Production app creation fails closed when OIDC, session/CSRF, and internal-context configuration is incomplete. The configured legacy server bearer path remains available only for existing service-to-service compatibility and does not create browser identity selectors.

## Verification

| Check | Result |
|---|---|
| `python -m pytest services/api/tests -q` | 31 passed, 1 warning |
| `python -m pytest packages/auth/tests/test_auth_contract.py -q` | 10 passed, 3 PyJWT warnings |
| `python scripts/validate_approved_releases.py --record docs/APPROVED_RELEASES.json --scope development-dependencies --print-digest` | passed; digest `65d3361ff822573ce18e72f12a4b314c452677196abcd8f45e66951683cc26ea` |
| Cross-tenant field read/mutation matrix | passed; 404 with no resource leakage |
| Parent Electron/source tree | not modified by this plan |

## Task Commit

- `d5f8cd3 feat(07-04): add OIDC sessions and tenant isolation`

## Deviations

- The parallel executor stalled after the shared-auth task. The remaining tasks were completed inline after inspecting its committed changes; no work was reset or discarded.
- The existing server bearer compatibility path remains because the standalone API's regression contract includes that explicit deployment mode. Browser sessions and all persistent farm-state access use claims-derived scope.
- CV release approval remains deferred under Plan 07-02; this plan does not activate, diagnose with, or certify any placeholder model.

## Self-Check: PASSED

- All implementation files are inside `Kisan Sathi Web/`.
- Auth, API, isolation, and package-contract tests pass.
- The migration manifest contains hashes for all Plan 07-04 implementation and test files.
- Existing parent/Electron changes were preserved.

---
*Phase: 07-standalone-kisan-sathi-web-service-migration*
*Plan: 04 — auth and isolation complete*
