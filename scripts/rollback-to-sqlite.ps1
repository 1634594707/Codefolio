param(
    [string]$PythonExe = "D:\ProgramData\miniconda3\python.exe",
    [string]$SqlitePath = "backend/data/codefolio.rollback.db",
    [string]$PostgresUrl = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($PostgresUrl)) {
    throw "PostgresUrl is required."
}

& $PythonExe "backend/scripts/backup_postgres.py" `
    --postgres-url $PostgresUrl `
    --output "backups/postgres-before-sqlite-rollback.dump"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $PythonExe "backend/scripts/migrate_postgres_to_sqlite.py" `
    --postgres-url $PostgresUrl `
    --sqlite-path $SqlitePath `
    --drop-existing
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
