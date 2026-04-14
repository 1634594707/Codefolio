#!/usr/bin/env bash
set -euo pipefail

PYTHON_EXE="${PYTHON_EXE:-python}"
SQLITE_PATH="${SQLITE_PATH:-backend/data/codefolio.rollback.db}"
POSTGRES_URL="${POSTGRES_URL:-}"

if [[ -z "$POSTGRES_URL" ]]; then
  echo "POSTGRES_URL is required" >&2
  exit 1
fi

"$PYTHON_EXE" backend/scripts/backup_postgres.py \
  --postgres-url "$POSTGRES_URL" \
  --output backups/postgres-before-sqlite-rollback.dump

"$PYTHON_EXE" backend/scripts/migrate_postgres_to_sqlite.py \
  --postgres-url "$POSTGRES_URL" \
  --sqlite-path "$SQLITE_PATH" \
  --drop-existing

docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
