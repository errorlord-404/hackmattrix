[CmdletBinding()]
param(
  [string]$BackendUrl = 'http://127.0.0.1:8001',
  [string]$FarmerId = 'demo',
  [ValidateRange(1, 65535)]
  [int]$RendererPort = 5173,
  [switch]$SkipMongo,
  [switch]$SkipSeed,
  [switch]$ResetDemo,
  [switch]$DisableCropModels
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$backendRoot = Join-Path $repoRoot 'backend'
$backendProcess = $null
$frontendProcess = $null
$electronProcess = $null

function Wait-Backend {
  param([string]$Url)
  $healthUrl = "$Url/health"
  for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
      $response = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
      if ($response.farm_state -eq 'available') { return $response }
    } catch { }
    Start-Sleep -Milliseconds 500
  }
  throw "Backend did not become healthy at $healthUrl."
}

function Stop-OwnedProcess {
  param($Process)
  if ($null -ne $Process -and -not $Process.HasExited) {
    # npm.cmd and Vite spawn child processes. Kill only this owned process tree so
    # Ctrl+C cannot leave a renderer/server running on the demo port.
    try {
      & taskkill.exe /PID $Process.Id /T /F *> $null
    } catch {
      Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    }
  }
}

function Select-RendererPort {
  param([int]$Preferred)
  for ($candidate = $Preferred; $candidate -le ($Preferred + 20); $candidate++) {
    try {
      $listener = Get-NetTCPConnection -LocalPort $candidate -State Listen -ErrorAction Stop
      if ($listener) { continue }
    } catch { return $candidate }
  }
  throw "No free renderer port found near $Preferred."
}

try {
  Set-Location $repoRoot
  # The local hackathon demo explicitly enables the field-scoped Tomato
  # simulator. Production/default backend launches leave this feature off.
  $env:TOMATO_DEMO_ENABLED = 'true'
  $modelRegistryPath = Join-Path $repoRoot 'ml\model_registry.json'
  $modelRootPath = Join-Path $repoRoot 'ml\private-artifacts\crop-disease'
  $modelBundleReady = (Test-Path -LiteralPath $modelRegistryPath) -and (Test-Path -LiteralPath (Join-Path $modelRootPath 'models'))
  # An explicit hosted provider in backend/.env takes precedence over the
  # bundled local demo model. This keeps the demo launcher aligned with the
  # consent-gated provider selected by the operator.
  $kindwiseSelected = Select-String -LiteralPath (Join-Path $backendRoot '.env') -Pattern '^\s*DIAGNOSIS_PROVIDER\s*=\s*kindwise_crop_health\s*$' -Quiet -ErrorAction SilentlyContinue
  if ($kindwiseSelected) {
    Write-Host 'Kindwise crop-health provider selected in backend/.env; local model registry will not be injected.'
  }
  elseif (-not $DisableCropModels -and $modelBundleReady) {
    # Environment variables are set before FastAPI starts so the original
    # Codex/Electron path can use the local registry without a second service.
    $env:DIAGNOSIS_PROVIDER = 'local_model_registry_demo'
    $env:CROP_HEALTH_MODEL_REGISTRY_PATH = $modelRegistryPath
    $env:CROP_HEALTH_MODEL_ROOT = $modelRootPath
    # The ONNX model gives a reliable local demonstration response without
    # loading every optional TensorFlow/PyTorch checkpoint at once.
    $env:CROP_HEALTH_MODEL_IDS = 'mesabo_resnet50_onnx'
    $env:CROP_HEALTH_MODEL_MAX_COUNT = '1'
    Write-Host 'Local ONNX crop model detected; crop-image checks will return research-only review signals.'
  }
  elseif ($DisableCropModels) {
    Write-Host 'Local crop model registry disabled for this run.'
  }
  else {
    Write-Host 'Local crop model bundle not installed; crop-health remains provider-unconfigured.'
  }
  if (-not $SkipMongo) {
    try {
      docker compose -f (Join-Path $backendRoot 'docker-compose.universal-data.yml') up -d mongodb | Out-Host
    } catch {
      Write-Warning "MongoDB could not be started by Docker. Existing MongoDB or degraded reference mode will be used."
    }
  }

  $backendPort = ([Uri]$BackendUrl).Port
  $health = $null
  try { $health = Invoke-RestMethod -Uri "$BackendUrl/health" -TimeoutSec 2 } catch { }
  if ($health -and $health.farm_state -eq 'available') {
    Write-Host "Using existing compatible backend: $BackendUrl/health ($($health.status), reference $($health.reference_database))"
  } else {
    $occupied = Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue
    if ($occupied) { throw "Backend port $backendPort is occupied by an incompatible service. Choose -BackendUrl with a free port." }
    $backendProcess = Start-Process -FilePath 'python' -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port',$backendPort) -WorkingDirectory $backendRoot -PassThru -WindowStyle Hidden
    $health = Wait-Backend -Url $BackendUrl
    Write-Host "Backend ready: $BackendUrl/health ($($health.status), reference $($health.reference_database))"
  }

  $env:KISANSATHI_FARM_STATE_API_URL = $BackendUrl
  if ($ResetDemo) {
    $env:KISANSATHI_RESET_DEMO = '1'
    $env:PYTHONPATH = $backendRoot
    python (Join-Path $backendRoot 'scripts\reset_demo_farmer_state.py') --farmer-id $FarmerId --confirm-demo-reset | Out-Host
  }
  if (-not $SkipSeed) {
    $env:PYTHONPATH = $backendRoot
    python (Join-Path $backendRoot 'scripts\seed_local_reference_data.py') | Out-Host
    python (Join-Path $backendRoot 'scripts\seed_demo_farmer_state.py') | Out-Host
    # Refresh approved public directories after the labelled offline seed. If
    # a government source is unavailable, retain the clearly labelled fixtures
    # so the rest of the field-state demo remains runnable.
    try {
      python (Join-Path $backendRoot 'scripts\refresh_live_reference_data.py') | Out-Host
      if ($LASTEXITCODE -ne 0) { Write-Warning 'Live reference refresh failed; local demo directory records remain labelled and unchanged.' }
    } catch {
      Write-Warning "Live reference refresh failed; local demo directory records remain labelled and unchanged. $($_.Exception.Message)"
    }
  }

  $RendererPort = Select-RendererPort -Preferred $RendererPort
  $rendererUrl = "http://127.0.0.1:$RendererPort"
  $env:VITE_FARM_STATE_API_URL = $BackendUrl
  $env:VITE_REFERENCE_API_URL = $BackendUrl
  $env:VITE_DEMO_FARMER_ID = $FarmerId
  $frontendProcess = Start-Process -FilePath 'npm.cmd' -ArgumentList @('run','dev','--','--host','127.0.0.1','--port',$RendererPort) -WorkingDirectory $repoRoot -PassThru -WindowStyle Hidden
  for ($attempt = 1; $attempt -le 30; $attempt++) {
    try { if ((Invoke-WebRequest -Uri $rendererUrl -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { break } } catch { }
    Start-Sleep -Milliseconds 500
  }

  $env:KISANSATHI_BACKEND_URL = $BackendUrl
  $env:KISANSATHI_FARMER_ID = $FarmerId
  $env:ELECTRON_RENDERER_URL = $rendererUrl
  $electronProcess = Start-Process -FilePath 'npm.cmd' -ArgumentList @('run','desktop') -WorkingDirectory $repoRoot -PassThru
  Write-Host 'KisanSathi Electron demo is running. Close Electron or press Ctrl+C to stop owned services.'
  Wait-Process -Id $electronProcess.Id
} finally {
  Stop-OwnedProcess $electronProcess
  Stop-OwnedProcess $frontendProcess
  Stop-OwnedProcess $backendProcess
}
