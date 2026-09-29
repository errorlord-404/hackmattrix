param(
    [switch]$SkipPopulation
)

$ErrorActionPreference = 'Stop'
$backendRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $backendRoot '.runtime'
$downloadRoot = Join-Path $runtimeRoot 'downloads'
$mongoRoot = Join-Path $runtimeRoot 'mongodb'
$mongoData = Join-Path $runtimeRoot 'mongodb-data'
$mongoLog = Join-Path $runtimeRoot 'mongodb.log'
$n8nRoot = Join-Path $runtimeRoot 'n8n'
$n8nData = Join-Path $runtimeRoot 'n8n-data'
$envFile = Join-Path $backendRoot '.env'
$workflowFile = Join-Path $backendRoot 'n8n\universal-data-sync.json'
$mongoVersion = '8.0.26'
$n8nVersion = '1.123.72'
$mongoArchive = Join-Path $downloadRoot "mongodb-windows-x86_64-$mongoVersion.zip"
$mongoUrl = "https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-$mongoVersion.zip"

function Import-DotEnv([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing $Path. Copy .env.example to .env and replace the placeholder secrets first."
    }
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#') -or -not $trimmed.Contains('=')) {
            continue
        }
        $parts = $trimmed.Split('=', 2)
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1], 'Process')
    }
}

function Wait-ForPort([int]$Port, [int]$Seconds = 60) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue) {
            return
        }
        Start-Sleep -Seconds 2
    }
    throw "Port $Port did not become ready within $Seconds seconds."
}

Import-DotEnv $envFile
if (-not $env:SCRAPER_WEBHOOK_TOKEN -or $env:SCRAPER_WEBHOOK_TOKEN -like 'replace-*') {
    throw 'Set a real SCRAPER_WEBHOOK_TOKEN in backend/.env before continuing.'
}
if (-not $env:N8N_ENCRYPTION_KEY -or $env:N8N_ENCRYPTION_KEY -like 'replace-*') {
    throw 'Set a real N8N_ENCRYPTION_KEY in backend/.env before continuing.'
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python is required and was not found on PATH.'
}
if (-not (Get-Command node -ErrorAction SilentlyContinue) -or -not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw 'Node.js and npm are required and were not found on PATH.'
}
$nodeVersion = [version]((& node --version).TrimStart('v'))
if ($nodeVersion -lt [version]'20.19.0') {
    throw "n8n $n8nVersion requires Node.js 20.19 or newer; found $nodeVersion."
}

New-Item -ItemType Directory -Force -Path $runtimeRoot, $downloadRoot, $mongoData, $n8nRoot, $n8nData | Out-Null

$mongoExecutable = Get-ChildItem -LiteralPath $mongoRoot -Filter mongod.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $mongoExecutable) {
    if (-not (Test-Path -LiteralPath $mongoArchive)) {
        Write-Host "Downloading MongoDB Community $mongoVersion from mongodb.com..."
        Start-BitsTransfer -Source $mongoUrl -Destination $mongoArchive -DisplayName 'KisanSathi MongoDB Runtime'
    }
    Write-Host 'Extracting MongoDB runtime...'
    Expand-Archive -LiteralPath $mongoArchive -DestinationPath $mongoRoot -Force
    $mongoExecutable = Get-ChildItem -LiteralPath $mongoRoot -Filter mongod.exe -Recurse | Select-Object -First 1
}
if (-not $mongoExecutable) {
    throw 'mongod.exe was not found after extracting the official MongoDB archive.'
}

if (-not (Test-NetConnection -ComputerName 127.0.0.1 -Port 27017 -InformationLevel Quiet -WarningAction SilentlyContinue)) {
    Write-Host 'Starting workspace-local MongoDB...'
    # Start-Process joins an argument array without preserving quotes around
    # values. Quote paths explicitly because the workspace may contain spaces.
    $mongoArguments = "--dbpath=`"$mongoData`" --bind_ip=127.0.0.1 --port=27017 --logpath=`"$mongoLog`" --logappend"
    $mongoProcess = Start-Process -FilePath $mongoExecutable.FullName -ArgumentList $mongoArguments -WindowStyle Hidden -PassThru
    Set-Content -LiteralPath (Join-Path $runtimeRoot 'mongod.pid') -Value $mongoProcess.Id
    Wait-ForPort -Port 27017
}

Push-Location $backendRoot
try {
    & python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }

    & python -m compileall -q app
    if ($LASTEXITCODE -ne 0) { throw 'Python compile validation failed.' }

    & python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed; services were not activated.' }

    if (-not $SkipPopulation) {
        Write-Host 'Populating official market, MSP, crop, MahaDBT scheme, FARMS network, and approved marketplace data...'
        & python -m app.scraping --sources market_prices,msp,crops,gov_schemes,machinery,marketplace
        if ($LASTEXITCODE -ne 0) { throw 'Universal-data population failed.' }
    }

    if (-not (Test-NetConnection -ComputerName 127.0.0.1 -Port 8000 -InformationLevel Quiet -WarningAction SilentlyContinue)) {
        Write-Host 'Starting FastAPI...'
        $apiProcess = Start-Process -FilePath 'python' -ArgumentList @(
            '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'
        ) -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru
        Set-Content -LiteralPath (Join-Path $runtimeRoot 'api.pid') -Value $apiProcess.Id
        Wait-ForPort -Port 8000
    }

    $n8nCommand = Join-Path $n8nRoot 'node_modules\.bin\n8n.cmd'
    $installedN8nVersion = if (Test-Path -LiteralPath $n8nCommand) { (& $n8nCommand --version).Trim() } else { '' }
    if ($installedN8nVersion -ne $n8nVersion) {
        Write-Host "Installing n8n $n8nVersion in the ignored runtime directory..."
        & npm.cmd install --prefix $n8nRoot "n8n@$n8nVersion" --no-package-lock --no-save
        if ($LASTEXITCODE -ne 0) { throw 'n8n installation failed.' }
    }

    $env:N8N_USER_FOLDER = $n8nData
    $env:GENERIC_TIMEZONE = 'Asia/Kolkata'
    $env:TZ = 'Asia/Kolkata'
    $env:N8N_BLOCK_ENV_ACCESS_IN_NODE = 'false'
    $env:BACKEND_INTERNAL_URL = 'http://127.0.0.1:8000'

    Write-Host 'Importing and activating the scheduled n8n workflow...'
    $workflowProbe = Join-Path $runtimeRoot 'existing-workflow.json'
    & $n8nCommand export:workflow --id=KisanSathiUniversalDataSync --output=$workflowProbe *> $null
    if ($LASTEXITCODE -ne 0) {
        & $n8nCommand import:workflow --input=$workflowFile
        if ($LASTEXITCODE -ne 0) { throw 'n8n workflow import failed.' }
    }
    & $n8nCommand update:workflow --id=KisanSathiUniversalDataSync --active=true
    if ($LASTEXITCODE -ne 0) { throw 'n8n workflow activation failed.' }

    if (-not (Test-NetConnection -ComputerName 127.0.0.1 -Port 5678 -InformationLevel Quiet -WarningAction SilentlyContinue)) {
        $n8nProcess = Start-Process -FilePath 'cmd.exe' -ArgumentList @('/c', "`"$n8nCommand`" start") `
            -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru
        Set-Content -LiteralPath (Join-Path $runtimeRoot 'n8n.pid') -Value $n8nProcess.Id
        Wait-ForPort -Port 5678 -Seconds 120
    }
}
finally {
    Pop-Location
}

Write-Host 'Universal data is ready.'
Write-Host 'FastAPI: http://127.0.0.1:8000/health'
Write-Host 'n8n:     http://127.0.0.1:5678'
Write-Host 'Schedule: daily at 06:30 Asia/Kolkata'
