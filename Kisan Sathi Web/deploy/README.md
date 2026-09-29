# Standalone deployment

This directory packages the standalone web and API services. The build context
is the standalone root (`Kisan Sathi Web`); the source trees supplied by the
web and API workstreams are expected at `apps/web` and `services/api`.

## Run

1. Copy `.env.example` to `.env` and fill server-only values. Keep `.env` out of
   version control.
2. Validate the rendered Compose model:

   ```powershell
   docker compose --env-file .\deploy\.env -f .\deploy\compose.yaml config
   ```

3. Build and start both services:

   ```powershell
   docker compose --env-file .\deploy\.env -f .\deploy\compose.yaml up --build -d
   ```

The web UI is available at `http://127.0.0.1:8080`. Its browser requests use
`/api/...`, which Nginx proxies over the private Compose network to the API.
The API is bound to loopback for operator diagnostics and is not the public
entrypoint.

## Run the current CV prototype

The base Compose file intentionally leaves the model-release volume empty and
does not package research weights into the production image. To run the web
prototype with the currently installed, manifest-verified research checkpoints,
use the explicit prototype overlay from the standalone root:

```powershell
python .\scripts\validate_prototype_models.py
docker compose -f .\deploy\compose.yaml -f .\deploy\compose.prototype.yaml up --build -d
```

The equivalent helpers are `scripts/start-prototype.ps1` and
`scripts/start-prototype.sh`. The overlay binds the selected
`models/candidates/mesabo-agri-plant-disease-resnet50-61aa6c3` directory
read-only into the API container; it does not
approve the models, enable browser diagnosis, or alter the production Compose
contract. The overlay selects `Dockerfile.api.prototype`, which installs only
CPU ONNX Runtime and binds the existing ONNX research candidate read-only. The
UI remains explicitly non-diagnostic and supports only the crops reported by
the installed prototype registry.

Stop the prototype with:

```powershell
docker compose -f .\deploy\compose.yaml -f .\deploy\compose.prototype.yaml down
```

## Secrets and provider keys

Provider credentials such as `SARVAM_API_KEY` and `DATA_GOV_IN_API_KEY` must be
injected into the API container at runtime through the env file, an orchestrator
secret manager, or an equivalent server-side mechanism. Do not put them in
`VITE_*` variables, web build arguments, browser local storage, or committed
files. Vite variables are compile-time browser data and cannot be treated as
secrets.

For a CI or production secret file stored outside this checkout, point the API
service's `env_file` at that file and use the same file for Compose
interpolation:

```powershell
$env:API_ENV_FILE = 'C:\secure\kisansathi-api.env'
docker compose --env-file $env:API_ENV_FILE -f .\deploy\compose.yaml up --build -d
```

Only the API service consumes that file. In a CI shell, set `API_ENV_FILE` to
the runner's secret-file path before invoking Compose. If your secret manager
exposes mounted files instead of environment variables, translate them to the
API process environment in the deployment platform; do not mount them into the
web image.

## Health and readiness

The API image and Compose healthcheck call `GET /healthz`, which is a liveness
check and intentionally succeeds while the provider is unconfigured. `GET
/readyz` is the full-service readiness contract: it returns degraded until the
provider and tool registry are ready. The web image serves its own `GET
/healthz`, while `GET /readyz` is proxied to the API so an ingress can check the
complete path.

The web service starts as soon as the API process starts, including when the
LLM provider is intentionally unconfigured. `GET /readyz` remains the honest
full-service readiness signal and returns degraded until the provider and tool
registry are ready. Logs and request correlation should be inspected with
`docker compose logs api web`.

## Persistent-volume contract

Compose creates three named volumes:

| Volume | Container path | Contract |
| --- | --- | --- |
| `kisansathi_farm_state` | `/app/data/farm_state` | API-owned durable farm-state database/files. |
| `kisansathi_farm_uploads` | `/app/data/farm_uploads` | API-owned private upload data; never served by Nginx. |
| `kisansathi_model_releases` | `/app/models/releases` | Runtime-injected, versioned and approved model release. Mounted read-only. |
| `kisansathi_crop_disease_models` | `/app/models/crop_disease/downloaded` | Runtime-injected, approved crop-specialist artifacts only. Mounted read-only. |

The deployable image contains no candidate or placeholder model bytes. The
empty `volumes/models` directory is only a contract marker. Populate the model volume through a release process
that verifies manifest hashes, approval status, and license/redistribution
policy before enabling inference.

Quarantined research candidates and structural placeholders are excluded from
the Docker build context. They remain available for offline validation only;
they are never copied into a deployable image or model volume.
