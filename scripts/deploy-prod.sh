#!/usr/bin/env bash
set -euo pipefail

DATABASE_BACKEND="${DATABASE_BACKEND:-sqlite}"
BUILD_FLAG="${BUILD_FLAG:---build}"
PYTHON_EXE="${PYTHON_EXE:-python}"
SQLITE_PATH="${SQLITE_PATH:-backend/data/codefolio.db}"
POSTGRES_URL="${POSTGRES_URL:-}"
MIGRATE_SQLITE_TO_POSTGRES="${MIGRATE_SQLITE_TO_POSTGRES:-false}"

compose_args=(--env-file .env.production -f docker-compose.prod.yml)

if [[ "$DATABASE_BACKEND" == "postgres" ]]; then
  compose_args+=(-f docker-compose.postgres.yml)
fi

if [[ "$DATABASE_BACKEND" == "postgres" && "$MIGRATE_SQLITE_TO_POSTGRES" == "true" ]]; then
  if [[ -z "$POSTGRES_URL" ]]; then
    echo "POSTGRES_URL is required when MIGRATE_SQLITE_TO_POSTGRES=true" >&2
    exit 1
  fi
  "$PYTHON_EXE" backend/scripts/migrate_sqlite_to_postgres.py \
    --sqlite-path "$SQLITE_PATH" \
    --postgres-url "$POSTGRES_URL" \
    --drop-existing
fi

docker compose "${compose_args[@]}" up -d "$BUILD_FLAG"
