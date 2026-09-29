param(
  [switch]$Down,
  [switch]$Build
)

$ErrorActionPreference = "Stop"
$standaloneRoot = Split-Path -Parent $PSScriptRoot
$compose = Join-Path $standaloneRoot "deploy/compose.yaml"
$envFile = Join-Path $standaloneRoot "deploy/.env"

python (Join-Path $standaloneRoot "scripts/health_check.py") --compose $compose --config-only
$args = @()
if (Test-Path $envFile) { $args += @("--env-file", $envFile) }
$args += @("-f", $compose)
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
