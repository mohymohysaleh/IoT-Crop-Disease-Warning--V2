<#
.SYNOPSIS
  Removes only this stack's Postgres Docker volume and restarts Compose. PostgreSQL replays
  configuration/postgresql/initdb/*.sql (UI user **`admin@local`**, Zone1/Zone2 apps, 10 devices, 2 gateways).

  Does NOT remove ThingsBoard or Redis volumes.

.EXAMPLE
  cd chirpstack\chirpstack-docker
  .\scripts\Reset-ChirpStackPostgres.ps1

  Note: run in PowerShell only. Do not use python/py on this file.

.EXAMPLE
  $env:CHIRPSTACK_BOOTSTRAP_PASSWORD = 'ChooseALongLabPassword'
  .\scripts\Reset-ChirpStackPostgres.ps1 -Force
  Remove-Item Env:CHIRPSTACK_BOOTSTRAP_PASSWORD
#>
param([switch]$Force)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ComposeRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $ComposeRoot

function Test-DockerCompose {
    docker compose version 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose V2 required (docker compose)." }
}

function Read-ChirpStackUserCount {
    $qs = @'
SELECT COUNT(*) FROM public."user";
'@
    $out = ($qs | docker compose exec -T postgres psql -U chirpstack -d chirpstack -At).Trim()
    $n = 0
    if (-not [int]::TryParse($out, [ref]$n)) { return -1 }
    return $n
}

function Read-ChirpStackFirstUserEmail {
    $qs = @'
SELECT email FROM public."user" ORDER BY created_at ASC LIMIT 1;
'@
    $line = ($qs | docker compose exec -T postgres psql -U chirpstack -d chirpstack -At | Select-Object -First 1)
    if ($null -eq $line) { return $null }
    $e = "$line".Trim()
    if ([string]::IsNullOrWhiteSpace($e)) { return $null }
    return $e
}

try {
    Test-DockerCompose

    Write-Host ""
    Write-Host "Compose directory: $ComposeRoot" -ForegroundColor Cyan
    Write-Host "This removes ONLY the Postgres named volume for this project (ThingsBoard + Redis kept)."
    Write-Host "Init replays chirpstack/chirpstack-docker/configuration/postgresql/initdb/"
    Write-Host ""

    if (-not $Force) {
        $r = Read-Host "Type RESET to confirm"
        if ($r -ne "RESET") {
            Write-Host "Aborted."
            exit 0
        }
    }

    $dirName = Split-Path -Leaf ($ComposeRoot.TrimEnd('\').TrimEnd('/'))
    $fallbackVol = "${dirName}_postgresqldata"
    $volToRemove = $null

    Write-Host "Detecting Postgres data volume..."
    $pgId = (docker compose ps -q postgres 2>$null | Select-Object -First 1)
    $pgId = if ($null -ne $pgId) { "$pgId".Trim() } else { "" }

    if ($pgId) {
        $raw = docker inspect $pgId --format '{{json .Mounts}}'
        $mounts = $raw | ConvertFrom-Json
        foreach ($m in $mounts) {
            if ($m.Destination -eq '/var/lib/postgresql/data' -and $m.Name) {
                $volToRemove = $m.Name
                break
            }
        }
    }

    if (-not $volToRemove) {
        $volToRemove = $fallbackVol
        Write-Host "Postgres container not inspected; fallback volume name: $fallbackVol"
    }
    else {
        Write-Host "Will remove volume: $volToRemove"
    }

    Write-Host ""
    Write-Host "Stopping stack..."
    docker compose down

    docker volume inspect $volToRemove 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Volume not found: $volToRemove" -ForegroundColor Red
        docker volume ls --format "{{.Name}}" | Select-String -Pattern 'postgres'
        throw "Remove the correct chirpstack *postgresqldata* volume, then run: docker compose up -d"
    }

    docker volume rm $volToRemove

    Write-Host ""
    Write-Host "Starting stack (PostgreSQL init may take 60-180 seconds)..."
    docker compose up -d

    Write-Host ""
    Write-Host "Waiting for chirpstack and postgres containers (up to 150s)..."
    $deadline = (Get-Date).AddSeconds(150)
    do {
        Start-Sleep -Seconds 5
        $csOk = docker compose ps chirpstack --status running --format "{{.State}}" 2>$null | Select-Object -First 1
        $pgOk = docker compose ps postgres --status running --format "{{.State}}" 2>$null | Select-Object -First 1
        if (($csOk -eq "running") -and ($pgOk -eq "running")) { break }
    } while ((Get-Date) -lt $deadline)

    Write-Host ""
    Write-Host "Waiting for seeded login user row (postgres init replaying *.sql; up to 180s more)..."
    $seedDeadline = (Get-Date).AddSeconds(180)
    $userCount = 0
    do {
        Start-Sleep -Seconds 4
        $userCount = Read-ChirpStackUserCount
        if ($userCount -gt 0) { break }
    } while ((Get-Date) -lt $seedDeadline)

    Write-Host ""
    Write-Host "=== Done ===" -ForegroundColor Green
    if ($userCount -lt 1) {
        Write-Host "WARNING: public.user row count still 0 - init scripts may still be running or failed." -ForegroundColor Red
        Write-Host "Check: docker compose logs postgres --tail 80"
        Write-Host "Retry set-password once userCount is 1+."
        Write-Host ""
    }

    $seedEmail = "admin@local"
    if ($userCount -ge 1) {
        $dbEmail = Read-ChirpStackFirstUserEmail
        if (-not [string]::IsNullOrWhiteSpace($dbEmail)) { $seedEmail = $dbEmail }
    }

    Write-Host "ChirpStack UI login email (must match public.user.email; used for set-password --email):" -ForegroundColor Cyan
    Write-Host "  $seedEmail"
    Write-Host ""
    Write-Host "1) Set password (interactive, enter twice):"
    Write-Host "    docker compose exec -it chirpstack chirpstack --config /etc/chirpstack set-password --email $seedEmail"
    Write-Host ""

    $boot = [Environment]::GetEnvironmentVariable("CHIRPSTACK_BOOTSTRAP_PASSWORD", "Process")
    if ($userCount -ge 1 -and -not [string]::IsNullOrEmpty($boot)) {
        Write-Host "Applying CHIRPSTACK_BOOTSTRAP_PASSWORD via stdin..."
        $boot | docker compose exec -T chirpstack chirpstack --config /etc/chirpstack set-password --email $seedEmail --stdin
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Bootstrap OK. Remove CHIRPSTACK_BOOTSTRAP_PASSWORD from your shell." -ForegroundColor Green
        }
    }

    Write-Host ""
    Write-Host "2) Open http://localhost:8080 - sign in with the same email as above (password you just set)."
    Write-Host ""
    Write-Host "3) Row check (paste in PowerShell): see docs/VERIFICATION_AND_TESTING.md"
}
finally {
    Pop-Location
}
