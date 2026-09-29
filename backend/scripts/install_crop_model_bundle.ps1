param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$sourceRoot = Join-Path $RepositoryRoot 'Kisan Sathi Web\models'
$targetRoot = Join-Path $RepositoryRoot 'ml\private-artifacts\crop-disease\models'

if (-not (Test-Path -LiteralPath $sourceRoot)) {
    throw "The checked-in Kisan Sathi Web model source is missing: $sourceRoot"
}

New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null

function Copy-ModelFile([string]$Source, [string]$Target) {
    if (-not (Test-Path -LiteralPath $Source)) {
        throw "Required model artifact is missing: $Source"
    }
    $targetDirectory = Split-Path -Parent $Target
    New-Item -ItemType Directory -Force -Path $targetDirectory | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Target -Force
}

# Only runtime artifacts and provenance metadata are copied. Hugging Face
# cache directories, notebooks, and source examples are intentionally omitted.
Copy-ModelFile (Join-Path $sourceRoot 'crop_disease\downloaded\harimitra\trained_model.keras') (Join-Path $targetRoot 'harimitra\trained_model.keras')
Copy-ModelFile (Join-Path $sourceRoot 'crop_disease\downloaded\harimitra\trained_model.h5') (Join-Path $targetRoot 'harimitra\trained_model.h5')
Copy-ModelFile (Join-Path $sourceRoot 'crop_disease\downloaded\harimitra\labels.json') (Join-Path $targetRoot 'harimitra\labels.json')
Copy-ModelFile (Join-Path $sourceRoot 'crop_disease\downloaded\harimitra\download-manifest.json') (Join-Path $targetRoot 'harimitra\download-manifest.json')

Copy-ModelFile (Join-Path $sourceRoot 'crop_disease\downloaded\mesabo_resnet50\model.safetensors') (Join-Path $targetRoot 'mesabo_resnet50\model.safetensors')
Copy-ModelFile (Join-Path $sourceRoot 'crop_disease\downloaded\mesabo_resnet50\config.json') (Join-Path $targetRoot 'mesabo_resnet50\config.json')
Copy-ModelFile (Join-Path $sourceRoot 'crop_disease\downloaded\mesabo_resnet50\preprocessor_config.json') (Join-Path $targetRoot 'mesabo_resnet50\preprocessor_config.json')
Copy-ModelFile (Join-Path $sourceRoot 'crop_disease\downloaded\mesabo_resnet50\download-manifest.json') (Join-Path $targetRoot 'mesabo_resnet50\download-manifest.json')

Copy-ModelFile (Join-Path $sourceRoot 'crop_disease\downloaded\plantvillage_efficientnet\plant_disease_efficientnet.keras') (Join-Path $targetRoot 'plantvillage_efficientnet\plant_disease_efficientnet.keras')
Copy-ModelFile (Join-Path $sourceRoot 'crop_disease\downloaded\plantvillage_efficientnet\labels.json') (Join-Path $targetRoot 'plantvillage_efficientnet\labels.json')
Copy-ModelFile (Join-Path $sourceRoot 'crop_disease\downloaded\plantvillage_efficientnet\download-manifest.json') (Join-Path $targetRoot 'plantvillage_efficientnet\download-manifest.json')

$candidate = Join-Path $sourceRoot 'candidates\mesabo-agri-plant-disease-resnet50-61aa6c3'
Copy-ModelFile (Join-Path $candidate 'model-fp32.onnx') (Join-Path $targetRoot 'mesabo_resnet50_onnx\model-fp32.onnx')
Copy-ModelFile (Join-Path $candidate 'labels.json') (Join-Path $targetRoot 'mesabo_resnet50_onnx\labels.json')
Copy-ModelFile (Join-Path $candidate 'preprocess.json') (Join-Path $targetRoot 'mesabo_resnet50_onnx\preprocess.json')
Copy-ModelFile (Join-Path $candidate 'source-manifest.json') (Join-Path $targetRoot 'mesabo_resnet50_onnx\source-manifest.json')

$registry = Join-Path $RepositoryRoot 'ml\model_registry.json'
if (-not (Test-Path -LiteralPath $registry)) {
    throw "The parent model registry is missing: $registry"
}

Write-Output "Installed the four local research model runtimes under $targetRoot"
Write-Output "Registry: $registry"
Write-Output "These artifacts remain prototype-only and require expert review."
