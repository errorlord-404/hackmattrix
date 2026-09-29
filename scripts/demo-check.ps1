[CmdletBinding()]
param(
  [string]$BackendUrl = 'http://127.0.0.1:8001',
  [string]$FarmerId = 'demo'
)

$ErrorActionPreference = 'Stop'
$headers = @{ 'X-Farmer-ID' = $FarmerId }
try {
  $health = Invoke-RestMethod -Uri "$BackendUrl/health" -Headers $headers -TimeoutSec 5
  $diagnostics = Invoke-RestMethod -Uri "$BackendUrl/v1/diagnostics" -Headers $headers -TimeoutSec 5
  Write-Host "Backend: $($health.status); farm state: $($health.farm_state); reference: $($health.reference_database)"
  Write-Host "Farmer fixtures: $($diagnostics.farmer_state.fields) fields, $($diagnostics.farmer_state.open_tasks) open tasks, $($diagnostics.farmer_state.open_alerts) open alerts"
  Write-Host "Reference catalog: $($diagnostics.components.reference_database.counts.schemes) schemes, $($diagnostics.components.reference_database.counts.machinery) machinery, $($diagnostics.components.reference_database.counts.marketplace) marketplace"
  if ($diagnostics.degraded_components.Count -gt 0) { Write-Warning "Degraded optional/components: $($diagnostics.degraded_components -join ', ')" }
  if ($health.farm_state -ne 'available') { exit 1 }
  exit 0
} catch {
  Write-Error "Demo backend check failed: $($_.Exception.Message)"
  exit 1
}
