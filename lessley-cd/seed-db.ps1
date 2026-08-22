<#
.SYNOPSIS
    Seed the Lessley MongoDB with the reference collections.

.DESCRIPTION
    Imports users, mccs, clubs, stores, store_aliases and deals from a directory
    of <collection>.json files (JSON arrays) by copying each file into the running
    mongodb container and running mongoimport there. See README.md -> Seeding
    MongoDB for the data layout.

    Defaults for the credentials and database name are read from .\.env
    (DB_USER, DB_PASS, DB_NAME) when it exists, so on a configured checkout this
    is just:

        .\seed-db.ps1

    Re-running is safe by default: rows are upserted on their business key (id,
    or _id for users), so an existing row is updated instead of duplicated.

.PARAMETER Username
    Mongo user. Default: DB_USER from .env, else "guest".

.PARAMETER Password
    Mongo password. Default: DB_PASS from .env, else "guest".

.PARAMETER Database
    Target database. Default: DB_NAME from .env, else "lessley".

.PARAMETER Path
    Directory holding the <collection>.json files.
    Default: ..\lessley-deals\data\seed relative to this script.

.PARAMETER Container
    Name of the running Mongo container. Default: "mongodb".

.PARAMETER Collections
    Subset to seed. Default: users, mccs, clubs, stores, store_aliases, deals.

.PARAMETER Drop
    Drop each collection before importing (destructive).

.PARAMETER Insert
    Plain inserts instead of upserts (fails on existing keys).

.PARAMETER EnvFile
    Dotenv file to read defaults from. Default: .\.env next to this script.

.PARAMETER DryRun
    Print what would run, change nothing.

.EXAMPLE
    .\seed-db.ps1

.EXAMPLE
    .\seed-db.ps1 -Username admin -Password s3cret -Path D:\dumps\lessley

.EXAMPLE
    .\seed-db.ps1 -Collections stores,deals -Drop
#>
[CmdletBinding()]
param(
    [Alias('u')][string]   $Username,
    [Alias('p')][string]   $Password,
    [Alias('d')][string]   $Database,
    [Alias('f')][string]   $Path,
    [Alias('c')][string]   $Container = 'mongodb',
    # Accepts both -Collections stores,deals (a PowerShell array) and
    # -Collections "stores,deals" (one string), which is all `powershell -File`
    # can pass. Validated below rather than with [ValidateSet] for that reason.
    [string[]]             $Collections,
    [switch]               $Drop,
    [switch]               $Insert,
    [string]               $EnvFile,
    [switch]               $DryRun
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Import order matters only for readability; each import is independent.
# The upsert key differs for users: ASP.NET Identity writes the account id as
# _id, while the scraping pipeline's exports keep the business key in id.
# store_aliases follows stores because every alias row points at one by store_id.
$collectionOrder = @('users', 'mccs', 'clubs', 'stores', 'store_aliases', 'deals')
$upsertFields    = @{
    users         = '_id'
    mccs          = 'id'
    clubs         = 'id'
    stores        = 'id'
    store_aliases = 'id'
    deals         = 'id'
}

# Read one KEY from a dotenv file, stripping an inline "  # comment" and any
# surrounding quotes. Returns $null when the file or the key is absent.
function Get-EnvValue {
    param([string] $Key, [string] $File)

    if (-not (Test-Path -LiteralPath $File)) { return $null }

    $line = Get-Content -LiteralPath $File |
            Where-Object { $_ -match "^\s*$([regex]::Escape($Key))\s*=" } |
            Select-Object -Last 1
    if (-not $line) { return $null }

    $value = ($line -split '=', 2)[1]
    $value = $value -replace '\s+#.*$', ''
    $value = $value.Trim().Trim('"').Trim("'")
    if ($value -eq '') { return $null }
    return $value
}

if (-not $EnvFile) { $EnvFile = Join-Path $scriptDir '.env' }

# .env fills in whatever was not passed explicitly.
if (-not $Username) { $Username = Get-EnvValue -Key 'DB_USER' -File $EnvFile }
if (-not $Password) { $Password = Get-EnvValue -Key 'DB_PASS' -File $EnvFile }
if (-not $Database) { $Database = Get-EnvValue -Key 'DB_NAME' -File $EnvFile }
if (-not $Username) { $Username = 'guest' }
if (-not $Password) { $Password = 'guest' }
if (-not $Database) { $Database = 'lessley' }
if (-not $Path)     { $Path     = Join-Path $scriptDir '..\lessley-deals\data\seed' }

if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
    throw "Seed directory not found: $Path (pass -Path)"
}
$Path = (Resolve-Path -LiteralPath $Path).Path

# A typo must fail loudly instead of quietly seeding nothing; the canonical
# order above is kept whatever order the caller asked in.
if ($Collections) {
    $requested = $Collections -split ',' |
                 ForEach-Object { $_.Trim() } |
                 Where-Object { $_ -ne '' }
    $unknown = $requested | Where-Object { $collectionOrder -notcontains $_ }
    if ($unknown) {
        throw "Unknown collection(s): $($unknown -join ', ') (known: $($collectionOrder -join ', '))"
    }
    $selected = $collectionOrder | Where-Object { $requested -contains $_ }
} else {
    $selected = $collectionOrder
}

# ── Preflight ───────────────────────────────────────────────────────────────────
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'docker not found on PATH'
}
if (-not $DryRun) {
    $running = docker inspect --format '{{.State.Running}}' $Container 2>$null
    if ($LASTEXITCODE -ne 0 -or $running -notmatch 'true') {
        throw "Container '$Container' is not running (start it with: docker compose up -d mongodb)"
    }
}

$mode = 'upsert'
if ($Insert) { $mode = 'insert' }
$dropNote = ''
if ($Drop) { $dropNote = ' (drop first)' }

Write-Host "Seeding $Database on container $Container from $Path"
Write-Host "User: $Username   Mode: $mode$dropNote"
Write-Host ''

$imported = 0
$skipped  = @()
$failed   = @()

foreach ($collection in $selected) {
    $file = Join-Path $Path "$collection.json"
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        Write-Host ("  ~ {0,-13} no {1}.json in {2} - skipped" -f $collection, $collection, $Path)
        $skipped += $collection
        continue
    }

    $remote = "/tmp/lessley-seed-$collection.json"
    Write-Host ("  > {0,-13} {1}" -f $collection, $file)

    $importArgs = @(
        'mongoimport'
        '--db', $Database
        '--collection', $collection
        '--file', $remote
        '--jsonArray'
        '--username', $Username
        '--password', $Password
        '--authenticationDatabase', 'admin'
    )
    # --drop already guarantees an empty collection, so upserting on top of it
    # would only cost a lookup per row.
    if ($Drop) {
        $importArgs += '--drop'
    } elseif ($mode -eq 'upsert') {
        $importArgs += @('--mode=upsert', "--upsertFields=$($upsertFields[$collection])")
    }

    if ($DryRun) {
        Write-Host "  [dry-run] docker cp `"$file`" ${Container}:$remote"
        Write-Host "  [dry-run] docker exec $Container $($importArgs -join ' ')"
        $imported++
        continue
    }

    $ok = $true

    docker cp $file "${Container}:$remote" | Out-Null
    if ($LASTEXITCODE -ne 0) { $ok = $false }

    if ($ok) {
        docker exec $Container @importArgs
        if ($LASTEXITCODE -ne 0) { $ok = $false }
    }

    # Best effort: a leftover temp file inside the container is harmless, and a
    # failed cleanup must not mask the import's own result.
    docker exec $Container rm -f $remote 2>$null | Out-Null

    if ($ok) {
        $imported++
    } else {
        Write-Host ("  ! {0,-13} import failed" -f $collection) -ForegroundColor Red
        $failed += $collection
    }
}

$summary = "`nImported $imported collection(s)."
if ($skipped.Count -gt 0) { $summary += " Skipped (no file): $($skipped -join ', ')." }
if ($failed.Count  -gt 0) { $summary += " Failed: $($failed -join ', ')." }
Write-Host $summary

if ($failed.Count -gt 0) { exit 1 }
