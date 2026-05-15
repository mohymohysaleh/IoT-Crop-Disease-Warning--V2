<#
.SYNOPSIS
  Repairs common ChirpStack Postgres inconsistencies without wiping the volume:
  - Recreates missing tenant rows still referenced by applications/gateways (orphan refs).
  - Links the first global admin into tenant_user for tenants with no users.

  If applications exist but device/gateway counts are still 0, your data was partially
  deleted — run Reset-ChirpStackPostgres.ps1 to replay the full seed.

.EXAMPLE
  cd chirpstack\chirpstack-docker
  .\scripts\Repair-ChirpStackTenantLinks.ps1
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ComposeRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$SqlFile = Join-Path $PSScriptRoot "repair_chirpstack_visibility.sql"
Push-Location $ComposeRoot
try {
    Get-Content -Raw -Encoding UTF8 $SqlFile | docker compose exec -T postgres psql -U chirpstack -d chirpstack -v ON_ERROR_STOP=1
    Write-Host "Done. Refresh ChirpStack UI (hard refresh). Tenants -> ChirpStack -> Applications." -ForegroundColor Green
    Write-Host "If devices/gateways are still empty in SQL, run Reset-ChirpStackPostgres.ps1 for full lab seed." -ForegroundColor DarkYellow
}
finally {
    Pop-Location
}
