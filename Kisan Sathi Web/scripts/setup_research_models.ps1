[CmdletBinding()]
param(
    [switch]$InstallDependencies,
    [switch]$VerifyOnly,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$StandaloneRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path
Set-Location -LiteralPath $StandaloneRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is required but was not found on PATH."
}

if ($InstallDependencies) {
    python -m pip install -r models/crop_disease/requirements.optional.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Optional crop-model dependencies failed to install."
    }
}

$env:PYTHONPATH = "."
$arguments = @("-m", "models.crop_disease.downloader", "--all")
if ($VerifyOnly) { $arguments += "--verify" }
if ($Force -and -not $VerifyOnly) { $arguments += "--force" }

python @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Research model setup or verification failed."
}

python -c "import json; from pathlib import Path; root=Path('models/crop_disease/downloaded'); manifests=sorted(root.glob('*/download-manifest.json')); print(json.dumps({'status':'verified','model_count':len(manifests),'manifests':[str(p.relative_to(root.parent.parent)).replace('\\\\','/') for p in manifests]}, indent=2))"
if ($LASTEXITCODE -ne 0) {
    throw "Downloaded model manifest summary failed."
}

Write-Host "Research model setup complete. Assets remain non-approved and non-diagnostic."
