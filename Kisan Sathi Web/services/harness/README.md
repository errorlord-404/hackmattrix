# Standalone service harness

`contracts/tool-registry.json` is the standalone copy of the bounded tool
metadata contract used by `services/api`. The web service reads this JSON at
startup and does not import the parent agent or backend runtime.

The API accepts server-only configuration through environment variables:

- `KISANSATHI_LLM_BASE_URL`
- `KISANSATHI_LLM_API_KEY`
- `KISANSATHI_LLM_MODEL`
- `KISANSATHI_WEB_BEARER_TOKEN`
- `KISANSATHI_ENV=production`
- `KISANSATHI_DEV_MODE=true` (explicit non-production opt-in)

The adapter also accepts the equivalent server-side `OPENAI_BASE_URL`,
`OPENAI_API_KEY`, and `OPENAI_MODEL` names.

No model weights or fake provider artifacts are included.
