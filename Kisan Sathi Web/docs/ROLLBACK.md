# Rollback rehearsal

Rollback identities include the prior image, schema, model, and data snapshot.
The state switch is atomic and preserves the evidence files.

```powershell
python scripts/rollback.py --state tests/fixtures/current-release.json --target tests/fixtures/previous-release.json --dry-run
```

Apply mode is reserved for an operator-approved deployment and must be run only
after the cutover preflight and backup checks pass.
