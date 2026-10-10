# User-space Postgres for the Dell (no Docker / no admin installer).
# Binaries live under %LOCALAPPDATA%\dnd-ai-dm (not OneDrive).
# Official EnterpriseDB Windows x64 zip, SHA-256 verified.

$ErrorActionPreference = "Stop"
$InstallRoot = Join-Path $env:LOCALAPPDATA "dnd-ai-dm"
$BinDir = Join-Path $InstallRoot "pgsql-17\pgsql\bin"
$DataDir = Join-Path $InstallRoot "pgdata"
$LogFile = Join-Path $InstallRoot "postgres.log"
$RepoZip = Join-Path (Split-Path -Parent $PSScriptRoot) ".local-postgres\postgresql-17.11-5-windows-x64-binaries.zip"
$Url = "https://get.enterprisedb.com/postgresql/postgresql-17.11-5-windows-x64-binaries.zip"
$ExpectedSha = "80379b2c04d51c30225532e0ae04509899141e9957ed096fe749d7fd9df8f82f"
$Port = 5432

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null

if (-not (Test-Path (Join-Path $BinDir "postgres.exe"))) {
    $zip = $RepoZip
    if (-not (Test-Path $zip)) {
        $zip = Join-Path $InstallRoot "postgresql-17.11-5-windows-x64-binaries.zip"
        Write-Host "Downloading PostgreSQL 17.11 Windows binaries..."
        Invoke-WebRequest -Uri $Url -OutFile $zip
    }
    $actual = (Get-FileHash -Algorithm SHA256 $zip).Hash.ToLower()
    if ($actual -ne $ExpectedSha) { throw "SHA-256 mismatch: $actual" }
    Write-Host "Extracting to $InstallRoot\pgsql-17 ..."
    New-Item -ItemType Directory -Force -Path (Join-Path $InstallRoot "pgsql-17") | Out-Null
    tar.exe -xf $zip -C (Join-Path $InstallRoot "pgsql-17")
}

if (-not (Test-Path (Join-Path $DataDir "PG_VERSION"))) {
    $pwFile = Join-Path $InstallRoot "pw.txt"
    Set-Content -Path $pwFile -Value "postgres" -NoNewline -Encoding ascii
    & (Join-Path $BinDir "initdb.exe") -D $DataDir -U postgres -A password --pwfile=$pwFile -E UTF8 --no-locale
    Add-Content (Join-Path $DataDir "postgresql.conf") "`nlisten_addresses = '127.0.0.1'`nport = $Port`n"
}

$env:PGPASSWORD = "postgres"
$probe = & (Join-Path $BinDir "psql.exe") -U postgres -h 127.0.0.1 -p $Port -d postgres -c "SELECT 1" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Starting Postgres on 127.0.0.1:$Port..."
    & (Join-Path $BinDir "pg_ctl.exe") -D $DataDir -l $LogFile start
    Start-Sleep -Seconds 2
}

$Psql = Join-Path $BinDir "psql.exe"
& $Psql -U postgres -h 127.0.0.1 -p $Port -d postgres -c "DO `$`$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'dnd') THEN CREATE ROLE dnd LOGIN PASSWORD 'dnd_local' CREATEDB; END IF; END `$`$;"
& $Psql -U postgres -h 127.0.0.1 -p $Port -d postgres -c "ALTER ROLE dnd CREATEDB;"
$dbExists = & $Psql -U postgres -h 127.0.0.1 -p $Port -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='dnd_bot_v3'"
if (-not $dbExists) {
    & $Psql -U postgres -h 127.0.0.1 -p $Port -d postgres -c "CREATE DATABASE dnd_bot_v3 OWNER dnd;"
}
Write-Host "SUCCESS: postgresql://dnd:***@127.0.0.1:$Port/dnd_bot_v3"
