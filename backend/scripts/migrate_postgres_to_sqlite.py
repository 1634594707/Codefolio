import argparse
import sqlite3
from pathlib import Path

try:
    import psycopg
except ImportError:  # pragma: no cover - runtime dependency
    psycopg = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate Codefolio snapshot data from PostgreSQL back to SQLite.")
    parser.add_argument("--postgres-url", required=True, help="Source PostgreSQL connection URL.")
    parser.add_argument("--sqlite-path", required=True, help="Target SQLite database file path.")
    parser.add_argument("--drop-existing", action="store_true", help="Delete existing SQLite data before import.")
    return parser.parse_args()


def ensure_sqlite_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS artifact_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artifact_type TEXT NOT NULL,
            tenant_scope TEXT NOT NULL DEFAULT 'global',
            scope_key TEXT NOT NULL,
            language TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_artifact_snapshots_unique
        ON artifact_snapshots (artifact_type, tenant_scope, scope_key, language)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_artifact_snapshots_lookup
        ON artifact_snapshots (artifact_type, tenant_scope, scope_key, language)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_artifact_snapshots_updated_at
        ON artifact_snapshots (updated_at)
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS workspaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workspaces_last_seen_at
        ON workspaces (last_seen_at)
        """
    )
    connection.commit()


def migrate(postgres_url: str, sqlite_path: Path, drop_existing: bool) -> None:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(postgres_url) as pg_connection:
        with pg_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT artifact_type, tenant_scope, scope_key, language, payload_json, created_at, updated_at
                FROM artifact_snapshots
                ORDER BY id
                """
            )
            snapshots = cursor.fetchall()
            cursor.execute(
                """
                SELECT workspace_id, created_at, last_seen_at
                FROM workspaces
                ORDER BY id
                """
            )
            workspaces = cursor.fetchall()

    sqlite_connection = sqlite3.connect(sqlite_path)
    try:
        ensure_sqlite_schema(sqlite_connection)
        if drop_existing:
            sqlite_connection.execute("DELETE FROM artifact_snapshots")
            sqlite_connection.execute("DELETE FROM workspaces")

        for row in snapshots:
            sqlite_connection.execute(
                """
                INSERT INTO artifact_snapshots (
                    artifact_type,
                    tenant_scope,
                    scope_key,
                    language,
                    payload_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(artifact_type, tenant_scope, scope_key, language)
                DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    row[0],
                    row[1] or "global",
                    row[2],
                    row[3] or "",
                    row[4],
                    str(row[5]),
                    str(row[6]),
                ),
            )

        for row in workspaces:
            sqlite_connection.execute(
                """
                INSERT INTO workspaces (workspace_id, created_at, last_seen_at)
                VALUES (?, ?, ?)
                ON CONFLICT(workspace_id)
                DO UPDATE SET last_seen_at = excluded.last_seen_at
                """,
                (row[0], str(row[1]), str(row[2])),
            )
        sqlite_connection.commit()
    finally:
        sqlite_connection.close()

    print(
        f"Migrated {len(snapshots)} artifact snapshots and {len(workspaces)} workspaces "
        f"from PostgreSQL to {sqlite_path}."
    )


def main() -> None:
    if psycopg is None:
        raise SystemExit("psycopg is not installed. Install backend requirements before running this migration.")
    args = parse_args()
    sqlite_path = Path(args.sqlite_path).expanduser().resolve()
    migrate(args.postgres_url, sqlite_path, args.drop_existing)


if __name__ == "__main__":
    main()
