param(
    [ValidateSet("sqlite", "postgres")]
    [string]$DatabaseBackend = "sqlite",
    [switch]$Build = $true,
    [switch]$MigrateSqliteToPostgres,
    [string]$PythonExe = "D:\ProgramData\miniconda3\python.exe",
    [string]$SqlitePath = "backend/data/codefolio.db",
    [string]$PostgresUrl = ""
)

$ErrorActionPreference = "Stop"
$composeArgs = @("--env-file", ".env.production", "-f", "docker-compose.prod.yml")

if ($DatabaseBackend -eq "postgres") {
    $composeArgs += @("-f", "docker-compose.postgres.yml")
}

if ($DatabaseBackend -eq "postgres" -and $MigrateSqliteToPostgres) {
    if ([string]::IsNullOrWhiteSpace($PostgresUrl)) {
        throw "PostgresUrl is required when using -MigrateSqliteToPostgres."
    }
    & $PythonExe "backend/scripts/migrate_sqlite_to_postgres.py" `
        --sqlite-path $SqlitePath `
        --postgres-url $PostgresUrl `
        --drop-existing
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$upArgs = $composeArgs + @("up", "-d")
if ($Build) {
    $upArgs += "--build"
}

docker compose @upArgs
