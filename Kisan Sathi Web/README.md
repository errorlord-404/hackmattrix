# KisanSathi standalone web deployment

This directory is the independently deployable web/API packaging boundary for
KisanSathi. It intentionally does not contain Electron, Codex, parent-runtime,
or model artifact files.

The deployment contract is in [`deploy/README.md`](deploy/README.md). In brief:

```powershell
Copy-Item .\deploy\.env.example .\deploy\.env
docker compose --env-file .\deploy\.env -f .\deploy\compose.yaml up --build -d
```

The web service is published on `127.0.0.1:8080` and proxies same-origin
`/api/` calls to the private API service. Provider credentials are API-only
runtime environment values; they are never compiled into the browser image.

The source workstreams provide `apps/web` and `services/api` under this root.
Run the standalone smoke tests with:

```powershell
npm run test:web-boundary
```

The current browser slice intentionally renders crop screening as an explicit
placeholder until an approved model release is uploaded. The API is usable with
any provider that implements the OpenAI-compatible chat-completions streaming
contract by setting the server-only `KISANSATHI_LLM_BASE_URL`,
`KISANSATHI_LLM_API_KEY`, and `KISANSATHI_LLM_MODEL` values. Native-only
provider protocols should be added behind the adapter interface or normalized
at an upstream gateway; the browser and orchestration contracts do not change.
