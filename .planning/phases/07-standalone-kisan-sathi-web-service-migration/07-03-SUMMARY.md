---
phase: 07-standalone-kisan-sathi-web-service-migration
plan: 03
subsystem: standalone-api-data
tags: [fastapi, sqlite, migrations, idempotency, domain-parity]
dependency_graph:
  requires: [07-01]
  provides: [WEB-01, standalone-domain-api, data-migration-rehearsal]
  affects: [07-04, 07-06, 07-08, 07-11]
tech_stack:
  added: [standalone-fastapi-domain-router, sqlite-farm-state-store]
  patterns: [claims-ready-store-boundary, canonical-idempotency-hash, checksum-verified-bundles]
key_files:
  created:
    - Kisan Sathi Web/services/api/app/core/config.py
    - Kisan Sathi Web/services/api/app/core/database.py
    - Kisan Sathi Web/services/api/app/farm_state/store.py
    - Kisan Sathi Web/services/api/app/routers/domain.py
    - Kisan Sathi Web/services/api/app/routers/reference.py
    - Kisan Sathi Web/services/api/migrations/001_initial.sql
    - Kisan Sathi Web/services/api/scripts/migrate_data.py
    - Kisan Sathi Web/services/api/tests/test_domain_parity.py
    - Kisan Sathi Web/services/api/tests/test_data_migration.py
  modified:
    - Kisan Sathi Web/services/api/app/main.py
    - Kisan Sathi Web/services/api/pyproject.toml
    - Kisan Sathi Web/services/api/requirements.lock
metrics:
  duration: "agent stalled after implementation; verified locally"
  completed: 2026-09-18
  tasks: 3
  files: 75
status: complete
---

# Phase 07 Plan 03: Standalone API and data foundation

The standalone API now owns the farm-state domain surface, reference-route
boundary, SQLite persistence, bounded request handling, canonical idempotency,
and explicit export/import/rehearsal tooling without importing the parent
runtime.

## Delivered

- Ported the domain models and schemas into `Kisan Sathi Web/services/api`.
- Added standalone configuration, database lifecycle, migrations, and a
  claims-ready `FarmStateStore` with tenant/farmer partition keys.
- Added `/v1` domain routes for profile, fields, sensors, alerts, irrigation,
  reports, settings, and storage status, plus bounded reference routes.
- Rejected the legacy `X-Farmer-ID` selector at the API boundary; Plan 07-04
  will replace the temporary development store identity with verified claims.
- Added checksum-verified, tenant-partitioned, idempotent migration bundles
  with rollback-safe validation and reconciliation rehearsal.
- Preserved explicit unavailable states for the optional reference database and
  excluded browser-local finance data from migration bundles.

## Verification

| Check | Result |
|---|---|
| `python -m pytest Kisan Sathi Web/services/api/tests/test_domain_parity.py -q` | 5 passed |
| `python -m pytest Kisan Sathi Web/services/api/tests/test_data_migration.py -q` | 2 passed |
| API/data plan suite together | 7 passed |
| Parent source changes | none |

## Known Stubs

- Temporary development tenant/farmer identity remains in the store dependency
  until Plan 07-04 installs the verified OIDC/session ActorScope boundary.
- Reference MongoDB routes are intentionally degraded when no reference
  database is configured; they do not fabricate records.
- CV model artifacts remain placeholder-only by the user decision and are not
  part of this plan.

## Deviations from Plan

### Auto-fixed Issues

1. The executor agent stalled after writing the implementation. The plan was
   completed by local verification and this summary was written without
   resetting or discarding the agent's changes.

### Deferred

- Approved dependency/image/model release identities remain governed by the
  blocking 07-02 checkpoint and were not installed or fabricated.

## Self-Check: PASSED

- All implementation files exist under `Kisan Sathi Web/`.
- Focused domain and migration tests pass.
- No existing Electron or parent source files were modified.
