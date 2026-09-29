param(
    [int]$Port = 8000,
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (-not $SkipInstall) {
    & (Join-Path $PSScriptRoot 'install_crop_model_bundle.ps1') -RepositoryRoot $repositoryRoot
}

$env:DIAGNOSIS_PROVIDER = 'local_model_registry_demo'
$env:CROP_HEALTH_MODEL_REGISTRY_PATH = Join-Path $repositoryRoot 'ml\model_registry.json'
$env:CROP_HEALTH_MODEL_ROOT = Join-Path $repositoryRoot 'ml\private-artifacts\crop-disease'
$env:CROP_HEALTH_MODEL_IDS = 'mesabo_resnet50_onnx'
$env:CROP_HEALTH_MODEL_MAX_COUNT = '1'

Write-Output 'Starting the original Codex/FastAPI backend with the local crop-model registry.'
Write-Output 'The ONNX research model is selected for a responsive demo; results remain in expert-review state.'
Set-Location (Join-Path $repositoryRoot 'backend')
& python -m uvicorn app.main:app --host 127.0.0.1 --port $Port
