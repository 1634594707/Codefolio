import argparse
import json
import sqlite3
from pathlib import Path

try:
    import psycopg
except ImportError:  # pragma: no cover - runtime dependency
    psycopg = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate Codefolio snapshot data from SQLite to PostgreSQL.")
    parser.add_argument("--sqlite-path", required=True, help="Path to the source SQLite database file.")
    parser.add_argument("--postgres-url", required=True, help="Target PostgreSQL connection URL.")
    parser.add_argument("--drop-existing", action="store_true", help="Delete existing target data before import.")
    return parser.parse_args()


def load_sqlite_rows(sqlite_path: Path) -> tuple[list[dict], list[dict]]:
    connection = sqlite3.connect(sqlite_path)
    connection.row_factory = sqlite3.Row
    try:
        snapshot_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(artifact_snapshots)").fetchall()
        }
        has_tenant_scope = "tenant_scope" in snapshot_columns
        workspace_table_exists = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'workspaces'"
        ).fetchone() is not None

        snapshot_sql = """
            SELECT artifact_type, {tenant_scope_select} scope_key, language, payload_json, created_at, updated_at
            FROM artifact_snapshots
            ORDER BY id
        """.format(
            tenant_scope_select="tenant_scope, " if has_tenant_scope else "'global' AS tenant_scope, "
        )
        snapshots = [
            dict(row)
            for row in connection.execute(
                snapshot_sql
            ).fetchall()
        ]
        workspaces = []
        if workspace_table_exists:
            workspaces = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT workspace_id, created_at, last_seen_at
                    FROM workspaces
                    ORDER BY id
                    """
                ).fetchall()
            ]
        return snapshots, workspaces
    finally:
        connection.close()


def ensure_target_schema(connection: psycopg.Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS artifact_snapshots (
                id BIGSERIAL PRIMARY KEY,
                artifact_type TEXT NOT NULL,
                tenant_scope TEXT NOT NULL DEFAULT 'global',
                scope_key TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL,
                UNIQUE (artifact_type, tenant_scope, scope_key, language)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS workspaces (
                id BIGSERIAL PRIMARY KEY,
                workspace_id TEXT NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL,
                last_seen_at TIMESTAMPTZ NOT NULL
            )
            """
        )
    connection.commit()


def migrate(sqlite_path: Path, postgres_url: str, drop_existing: bool) -> None:
    snapshots, workspaces = load_sqlite_rows(sqlite_path)
    with psycopg.connect(postgres_url) as connection:
        ensure_target_schema(connection)
        with connection.cursor() as cursor:
            if drop_existing:
                cursor.execute("TRUNCATE TABLE artifact_snapshots, workspaces RESTART IDENTITY")

            for row in snapshots:
                payload_json = row["payload_json"]
                json.loads(payload_json)
                cursor.execute(
                    """
                    INSERT INTO artifact_snapshots (
                        artifact_type,
                        tenant_scope,
                        scope_key,
                        language,
                        payload_json,
                        created_at,
                        updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (artifact_type, tenant_scope, scope_key, language)
                    DO UPDATE SET
                        payload_json = EXCLUDED.payload_json,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (
                        row["artifact_type"],
                        row["tenant_scope"] or "global",
                        row["scope_key"],
                        row["language"] or "",
                        payload_json,
                        row["created_at"],
                        row["updated_at"],
                    ),
                )

            for row in workspaces:
                cursor.execute(
                    """
                    INSERT INTO workspaces (workspace_id, created_at, last_seen_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (workspace_id)
                    DO UPDATE SET last_seen_at = EXCLUDED.last_seen_at
                    """,
                    (row["workspace_id"], row["created_at"], row["last_seen_at"]),
                )
        connection.commit()

    print(
        f"Migrated {len(snapshots)} artifact snapshots and {len(workspaces)} workspaces "
        f"from {sqlite_path} to PostgreSQL."
    )


def main() -> None:
    if psycopg is None:
        raise SystemExit("psycopg is not installed. Install backend requirements before running this migration.")
    args = parse_args()
    sqlite_path = Path(args.sqlite_path).expanduser().resolve()
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite database not found: {sqlite_path}")
    migrate(sqlite_path, args.postgres_url, args.drop_existing)


if __name__ == "__main__":
    main()
