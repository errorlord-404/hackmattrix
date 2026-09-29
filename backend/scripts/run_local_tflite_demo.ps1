<#
.SYNOPSIS
Runs the explicit, controlled-image TensorFlow Lite crop-health demonstration.

.DESCRIPTION
This script sets process-local settings only. It does not modify .env and must
never be used to describe the model as field deployed. The dynamic-range model
is intentionally selected because the current full-INT8 candidate is rejected
by the recorded release gate.
#>
[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$NoReload,
    [ValidateRange(1, 65535)]
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$modelPath = Join-Path $repoRoot 'ml\private-artifacts\tomato-efficientnetv2-b0-benchmark-v2-tflite\model-dynamic.tflite'
$labelsPath = Join-Path $repoRoot 'ml\private-artifacts\tomato-efficientnetv2-b0-benchmark-v2-tflite\labels.json'
$manifestPath = Join-Path $repoRoot 'ml\releases\crop-health-tfhub-tomato-controlled-demo-v0.3.yaml'

foreach ($requiredPath in @($modelPath, $labelsPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required controlled-demo artifact is unavailable: $requiredPath`nRun the documented TF Hub training/export workflow first. Do not substitute an unversioned model."
    }
}

& python (Join-Path $repoRoot 'ml\training\validate_release_manifest.py') --manifest $manifestPath --repo-root $repoRoot
if ($LASTEXITCODE -ne 0) {
    throw 'The controlled-demo manifest did not match its local artifact. Do not start inference with an unverified model.'
}

$env:DIAGNOSIS_PROVIDER = 'local_tflite_demo'
$env:CROP_HEALTH_TFLITE_MODEL_PATH = $modelPath
$env:CROP_HEALTH_TFLITE_LABELS_PATH = $labelsPath
$env:CROP_HEALTH_TFLITE_CROP = 'tomato'
$env:CROP_HEALTH_TFLITE_RELEASE_MANIFEST_PATH = $manifestPath

Write-Host 'Configured local_tflite_demo with the controlled EfficientNetV2-B0 PlantVillage tomato artifact.'
Write-Warning 'Demo-only: not field validated; it must not trigger pesticide, fertiliser, irrigation, or pump action.'

if ($CheckOnly) {
    Write-Host 'Artifact and explicit runtime configuration checks passed.'
    return
}

Push-Location (Join-Path $repoRoot 'backend')
try {
    $uvicornArgs = @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', $Port)
    if (-not $NoReload) {
        # The ignored runtime directory can contain active MongoDB/n8n installs.
        # Watching it makes ordinary dependency writes restart the demo service.
        # Keep each glob in the same native argument as its option. Passing a
        # bare wildcard through PowerShell expands it to every runtime file,
        # which makes Uvicorn receive hundreds of unexpected arguments.
        $uvicornArgs += @('--reload', '--reload-exclude=.runtime/*', '--reload-exclude=.runtime/**')
    }
    & python @uvicornArgs
} finally {
    Pop-Location
}
