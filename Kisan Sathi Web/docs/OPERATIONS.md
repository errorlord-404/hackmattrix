# Kisan Sathi Web operations

The standalone service is a three-container deployment: `web` serves the
browser bundle and same-origin proxy, `api` owns domain/media/CV persistence,
and `harness` owns provider-neutral LLM orchestration, approvals, tool policy,
and event replay.

## Local startup

```powershell
Copy-Item deploy/.env.example deploy/.env
.\scripts\start.ps1 -Build
```

The startup script validates the compose topology before starting. The browser
is served at `http://127.0.0.1:8080`; `/api/` and `/harness/` remain same-origin
paths. `GET /healthz` is process liveness and `GET /readyz` is dependency
readiness.

## Production configuration

Set `KISANSATHI_ENV=production`, inject session/CSRF/internal secrets through
the deployment secret manager, configure OIDC claims, and provide an
allowlisted provider model through server-only variables. Never put provider
keys in `VITE_*`, browser storage, tool arguments, or logs. Production harness
readiness remains degraded until a real provider is configured; it never falls
back to the deterministic fake provider.

## CV release policy

CV model bytes are mounted separately and read-only. Candidate and placeholder
directories are excluded from Docker build contexts. A production CV release
must pass `scripts/validate_approved_releases.py --require-all`,
`models/validate_release_manifest.py --require-approved --verify-artifacts`,
and the field/OOD, redistribution, agronomist, golden-parity, and rollback
gates before the browser or server can return an authoritative diagnosis.

## Health, logs, and recovery

Use `docker compose -f deploy/compose.yaml ps` and the service healthchecks for
basic status. Proxy buffering is disabled for harness streams so event IDs and
resume cursors are preserved. Logs must contain correlation/request/session/
turn/tool IDs only after redaction; media bodies, cookies, bearer tokens, and
provider secrets are not valid log fields.

Named volumes hold farm state, uploads, approved model releases, crop model
artifacts, and harness state. Back up the named volumes before schema/model
changes, record the release identity and checksums, and use the rollback command
once the release-gate runner is implemented. Do not delete evidence while
recovering a failed deployment.
