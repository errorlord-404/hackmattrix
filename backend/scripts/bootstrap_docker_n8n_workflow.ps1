[CmdletBinding()]
param(
  [switch]$ForceImport
)

# n8n currently emits a Node deprecation warning on stderr. Native stderr must
# not bypass our explicit `$LASTEXITCODE` checks below.
$ErrorActionPreference = 'Continue'
$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$composeFile = Join-Path $backendRoot 'docker-compose.universal-data.yml'
$workflowPath = '/workflows/universal-data-sync.json'
$workflowId = 'KisanSathiUniversalDataSync'

function Invoke-N8nCli {
  param([string[]]$Arguments)
  & docker.exe compose -f $composeFile exec -T n8n n8n @Arguments
  if ($LASTEXITCODE -ne 0) { throw "n8n command failed: n8n $($Arguments -join ' ')" }
}

# Start the service first. The pinned container image deliberately has no shell,
# so this uses n8n's documented CLI directly rather than `/bin/sh -c`.
& docker.exe compose -f $composeFile up -d n8n
if ($LASTEXITCODE -ne 0) { throw 'Could not start the n8n service.' }

$probePath = '/tmp/kisansathi-workflow-probe.json'
$workflowExists = $false
& docker.exe compose -f $composeFile exec -T n8n n8n export:workflow "--id=$workflowId" "--output=$probePath" *> $null
if ($LASTEXITCODE -eq 0) { $workflowExists = $true }

if (-not $workflowExists -or $ForceImport) {
  Write-Host 'Importing the versioned KisanSathi universal-data workflow...'
  Invoke-N8nCli @('import:workflow', "--input=$workflowPath")
} else {
  Write-Host 'KisanSathi universal-data workflow already exists; preserving the stored workflow definition.'
}

Invoke-N8nCli @('update:workflow', "--id=$workflowId", '--active=true')
Write-Host 'Restarting n8n so the active schedule is loaded...'
& docker.exe compose -f $composeFile restart n8n
if ($LASTEXITCODE -ne 0) { throw 'Could not restart n8n after activating the workflow.' }

for ($attempt = 1; $attempt -le 30; $attempt++) {
  try {
    if ((Invoke-WebRequest -Uri 'http://127.0.0.1:5678/healthz' -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) {
      Write-Host "n8n is healthy and workflow $workflowId is active."
      exit 0
    }
  } catch { }
  Start-Sleep -Seconds 2
}

throw 'n8n did not become healthy after workflow activation.'
