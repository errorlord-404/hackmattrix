[CmdletBinding()]
param(
    [string]$DestinationRoot
)

$ErrorActionPreference = 'Stop'
if (-not $DestinationRoot) {
    $DestinationRoot = Join-Path $PSScriptRoot '..\models\placeholders'
}

$packages = @(
    @{
        Directory = 'ktt-mobilenetv3-int8'
        File = 'model.onnx'
        Url = 'https://huggingface.co/DrUkachi/ktt-crop-disease-classifier/resolve/0bc90b39028bd57124e1cbd51bf4a41ae36b7de8/model.onnx'
        Size = 4335078
        Sha256 = 'd00355a27089622d486d6de379474f7b99b424928be5c7ac96bf8f7953ff74c8'
    }
)

foreach ($package in $packages) {
    $directory = Join-Path $DestinationRoot $package.Directory
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    $destination = Join-Path $directory $package.File
    $validExisting = $false
    if (Test-Path -LiteralPath $destination) {
        $item = Get-Item -LiteralPath $destination
        $hash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
        $validExisting = $item.Length -eq $package.Size -and $hash -eq $package.Sha256
    }
    if (-not $validExisting) {
        $temporary = "$destination.download"
        Invoke-WebRequest -Uri $package.Url -OutFile $temporary -UseBasicParsing
        $item = Get-Item -LiteralPath $temporary
        $hash = (Get-FileHash -LiteralPath $temporary -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($item.Length -ne $package.Size -or $hash -ne $package.Sha256) {
            Remove-Item -LiteralPath $temporary -Force
            throw "Downloaded placeholder failed integrity validation: $($package.Directory)"
        }
        Move-Item -LiteralPath $temporary -Destination $destination -Force
    }
    Write-Output "$($package.Directory): installed and verified"
}
