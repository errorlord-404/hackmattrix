param(
  [switch]$Down,
  [switch]$Build
)

$ErrorActionPreference = "Stop"
$standaloneRoot = Split-Path -Parent $PSScriptRoot
$baseCompose = Join-Path $standaloneRoot "deploy/compose.yaml"
$prototypeCompose = Join-Path $standaloneRoot "deploy/compose.prototype.yaml"
$envFile = Join-Path $standaloneRoot "deploy/.env"

python (Join-Path $standaloneRoot "scripts/validate_prototype_models.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python (Join-Path $standaloneRoot "scripts/validate_prototype_models.py") --registry (Join-Path $standaloneRoot "models/crop_disease/registry.prototype.json") --root (Join-Path $standaloneRoot "models/candidates")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python (Join-Path $standaloneRoot "scripts/health_check.py") --compose $baseCompose --config-only
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$args = @()
if (Test-Path $envFile) { $args += @("--env-file", $envFile) }
$args += @("-f", $baseCompose, "-f", $prototypeCompose)
if ($Down) {
  docker compose @args down
  exit $LASTEXITCODE
}
if ($Build) {
  docker compose @args build
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
docker compose @args up -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker compose @args ps
