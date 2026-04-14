import asyncio
import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config import settings

try:
    import psycopg
except ImportError:  # pragma: no cover - optional dependency
    psycopg = None

try:
    from psycopg_pool import ConnectionPool
except ImportError:  # pragma: no cover - optional dependency
    ConnectionPool = None


ARTIFACT_GITHUB_USER = "github_user"
ARTIFACT_REPOSITORY_PROFILE = "repository_profile"
ARTIFACT_AI_STYLE_TAGS = "ai_style_tags"
ARTIFACT_AI_ROAST = "ai_roast"
ARTIFACT_AI_TECH_SUMMARY = "ai_tech_summary"
ARTIFACT_REPOSITORY_ANALYSIS = "repository_analysis"
ARTIFACT_BENCHMARK_REPORT = "benchmark_report"


class SnapshotBackend(ABC):
    backend_name = "unknown"

    @abstractmethod
    def initialize_schema(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def fetch_row(self, artifact_type: str, tenant_scope: str, scope_key: str, language: str) -> tuple[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_row(
        self,
        artifact_type: str,
        tenant_scope: str,
        scope_key: str,
        language: str,
        payload_json: str,
        now_iso: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_row(self, artifact_type: str, tenant_scope: str, scope_key: str, language: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def delete_prefix_rows(self, artifact_type: str, tenant_scope: str, scope_prefix: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def delete_row_all_scopes(self, artifact_type: str, scope_key: str, language: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def delete_prefix_rows_all_scopes(self, artifact_type: str, scope_prefix: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def delete_artifact_rows(self, artifact_type: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def ensure_workspace_row(self, workspace_id: str, now_iso: str) -> None:
        raise NotImplementedError


class SqliteSnapshotBackend(SnapshotBackend):
    backend_name = "sqlite"

    def __init__(self, database_path: str):
        self.database_path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize_schema(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            self._ensure_snapshot_schema(connection)
            self._ensure_workspace_schema(connection)
            connection.commit()

    def _ensure_snapshot_schema(self, connection: sqlite3.Connection) -> None:
        table_exists = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'artifact_snapshots'"
        ).fetchone()

        if table_exists is None:
            connection.execute(
                """
                CREATE TABLE artifact_snapshots (
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
        else:
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(artifact_snapshots)").fetchall()
            }
            if "tenant_scope" not in columns:
                connection.execute("ALTER TABLE artifact_snapshots RENAME TO artifact_snapshots_legacy")
                connection.execute(
                    """
                    CREATE TABLE artifact_snapshots (
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
                    INSERT INTO artifact_snapshots (
                        id,
                        artifact_type,
                        tenant_scope,
                        scope_key,
                        language,
                        payload_json,
                        created_at,
                        updated_at
                    )
                    SELECT
                        id,
                        artifact_type,
                        'global',
                        scope_key,
                        language,
                        payload_json,
                        created_at,
                        updated_at
                    FROM artifact_snapshots_legacy
                    """
                )
                connection.execute("DROP TABLE artifact_snapshots_legacy")

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

    def _ensure_workspace_schema(self, connection: sqlite3.Connection) -> None:
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

    def fetch_row(self, artifact_type: str, tenant_scope: str, scope_key: str, language: str) -> tuple[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json, updated_at
                FROM artifact_snapshots
                WHERE artifact_type = ? AND tenant_scope = ? AND scope_key = ? AND language = ?
                LIMIT 1
                """,
                (artifact_type, tenant_scope, scope_key, language or ""),
            ).fetchone()
            if row is None:
                return None
            return row["payload_json"], row["updated_at"]

    def upsert_row(
        self,
        artifact_type: str,
        tenant_scope: str,
        scope_key: str,
        language: str,
        payload_json: str,
        now_iso: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
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
                (artifact_type, tenant_scope, scope_key, language or "", payload_json, now_iso, now_iso),
            )
            connection.commit()

    def delete_row(self, artifact_type: str, tenant_scope: str, scope_key: str, language: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM artifact_snapshots
                WHERE artifact_type = ? AND tenant_scope = ? AND scope_key = ? AND language = ?
                """,
                (artifact_type, tenant_scope, scope_key, language or ""),
            )
            connection.commit()
            return cursor.rowcount

    def delete_prefix_rows(self, artifact_type: str, tenant_scope: str, scope_prefix: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM artifact_snapshots
                WHERE artifact_type = ? AND tenant_scope = ? AND scope_key LIKE ?
                """,
                (artifact_type, tenant_scope, f"{scope_prefix}%"),
            )
            connection.commit()
            return cursor.rowcount

    def delete_row_all_scopes(self, artifact_type: str, scope_key: str, language: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM artifact_snapshots
                WHERE artifact_type = ? AND scope_key = ? AND language = ?
                """,
                (artifact_type, scope_key, language or ""),
            )
            connection.commit()
            return cursor.rowcount

    def delete_prefix_rows_all_scopes(self, artifact_type: str, scope_prefix: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM artifact_snapshots
                WHERE artifact_type = ? AND scope_key LIKE ?
                """,
                (artifact_type, f"{scope_prefix}%"),
            )
            connection.commit()
            return cursor.rowcount

    def delete_artifact_rows(self, artifact_type: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM artifact_snapshots
                WHERE artifact_type = ?
                """,
                (artifact_type,),
            )
            connection.commit()
            return cursor.rowcount

    def ensure_workspace_row(self, workspace_id: str, now_iso: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO workspaces (workspace_id, created_at, last_seen_at)
                VALUES (?, ?, ?)
                ON CONFLICT(workspace_id)
                DO UPDATE SET last_seen_at = excluded.last_seen_at
                """,
                (workspace_id, now_iso, now_iso),
            )
            connection.commit()


class PostgresSnapshotBackend(SnapshotBackend):
    backend_name = "postgresql"

    def __init__(self, database_url: str):
        if psycopg is None or ConnectionPool is None:
            raise RuntimeError(
                "DATABASE_URL is set to PostgreSQL but psycopg pool dependencies are not installed. "
                "Install backend requirements with psycopg and psycopg-pool enabled first."
            )
        self.database_url = database_url
        self.pool = ConnectionPool(
            conninfo=self.database_url,
            min_size=max(settings.POSTGRES_POOL_MIN_SIZE, 1),
            max_size=max(settings.POSTGRES_POOL_MAX_SIZE, max(settings.POSTGRES_POOL_MIN_SIZE, 1)),
            kwargs={"autocommit": False},
            open=False,
        )

    def _connection(self):
        return self.pool.connection()

    def initialize_schema(self) -> None:
        self.pool.open(wait=True)
        with self._connection() as connection:
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
                    CREATE INDEX IF NOT EXISTS idx_artifact_snapshots_lookup
                    ON artifact_snapshots (artifact_type, tenant_scope, scope_key, language)
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_artifact_snapshots_updated_at
                    ON artifact_snapshots (updated_at)
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
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_workspaces_last_seen_at
                    ON workspaces (last_seen_at)
                    """
                )
            connection.commit()

    def fetch_row(self, artifact_type: str, tenant_scope: str, scope_key: str, language: str) -> tuple[str, Any] | None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload_json, updated_at
                    FROM artifact_snapshots
                    WHERE artifact_type = %s AND tenant_scope = %s AND scope_key = %s AND language = %s
                    LIMIT 1
                    """,
                    (artifact_type, tenant_scope, scope_key, language or ""),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                return row[0], row[1]

    def upsert_row(
        self,
        artifact_type: str,
        tenant_scope: str,
        scope_key: str,
        language: str,
        payload_json: str,
        now_iso: str,
    ) -> None:
        now = datetime.fromisoformat(now_iso)
        with self._connection() as connection:
            with connection.cursor() as cursor:
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
                    ON CONFLICT(artifact_type, tenant_scope, scope_key, language)
                    DO UPDATE SET
                        payload_json = EXCLUDED.payload_json,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (artifact_type, tenant_scope, scope_key, language or "", payload_json, now, now),
                )
            connection.commit()

    def delete_row(self, artifact_type: str, tenant_scope: str, scope_key: str, language: str) -> int:
        return self._delete_with_rowcount(
            """
            DELETE FROM artifact_snapshots
            WHERE artifact_type = %s AND tenant_scope = %s AND scope_key = %s AND language = %s
            """,
            (artifact_type, tenant_scope, scope_key, language or ""),
        )

    def delete_prefix_rows(self, artifact_type: str, tenant_scope: str, scope_prefix: str) -> int:
        return self._delete_with_rowcount(
            """
            DELETE FROM artifact_snapshots
            WHERE artifact_type = %s AND tenant_scope = %s AND scope_key LIKE %s
            """,
            (artifact_type, tenant_scope, f"{scope_prefix}%"),
        )

    def delete_row_all_scopes(self, artifact_type: str, scope_key: str, language: str) -> int:
        return self._delete_with_rowcount(
            """
            DELETE FROM artifact_snapshots
            WHERE artifact_type = %s AND scope_key = %s AND language = %s
            """,
            (artifact_type, scope_key, language or ""),
        )

    def delete_prefix_rows_all_scopes(self, artifact_type: str, scope_prefix: str) -> int:
        return self._delete_with_rowcount(
            """
            DELETE FROM artifact_snapshots
            WHERE artifact_type = %s AND scope_key LIKE %s
            """,
            (artifact_type, f"{scope_prefix}%"),
        )

    def delete_artifact_rows(self, artifact_type: str) -> int:
        return self._delete_with_rowcount(
            """
            DELETE FROM artifact_snapshots
            WHERE artifact_type = %s
            """,
            (artifact_type,),
        )

    def _delete_with_rowcount(self, sql: str, params: tuple[Any, ...]) -> int:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                rowcount = cursor.rowcount
            connection.commit()
            return rowcount

    def ensure_workspace_row(self, workspace_id: str, now_iso: str) -> None:
        now = datetime.fromisoformat(now_iso)
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO workspaces (workspace_id, created_at, last_seen_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT(workspace_id)
                    DO UPDATE SET last_seen_at = EXCLUDED.last_seen_at
                    """,
                    (workspace_id, now, now),
                )
            connection.commit()

    def close(self) -> None:
        self.pool.close()


class SnapshotStore:
    def __init__(self, database_url: str, database_path: str):
        self.database_url = (database_url or "").strip()
        self.database_path = database_path
        self.backend = self._build_backend()
        self.ready = False

    @property
    def backend_name(self) -> str:
        return self.backend.backend_name

    @property
    def target_description(self) -> str:
        if self.backend_name == "sqlite":
            return self.database_path
        return self.database_url

    async def connect(self) -> None:
        await asyncio.to_thread(self.backend.initialize_schema)
        self.ready = True

    async def close(self) -> None:
        close_method = getattr(self.backend, "close", None)
        if callable(close_method):
            await asyncio.to_thread(close_method)
        self.ready = False

    async def get_snapshot(
        self,
        artifact_type: str,
        scope_key: str,
        language: str = "",
        max_age_seconds: int | None = None,
        tenant_scope: str = "global",
    ) -> dict[str, Any] | None:
        normalized_scope, raw_scope_key = self._split_scope_key(self._scoped_scope_key(scope_key, tenant_scope))
        row = await asyncio.to_thread(
            self.backend.fetch_row,
            artifact_type,
            normalized_scope,
            raw_scope_key,
            language,
        )
        if row is None:
            return None

        payload_json, updated_at_raw = row
        if max_age_seconds is not None:
            updated_at = self._parse_timestamp(updated_at_raw)
            if updated_at is None:
                return None
            if datetime.now(timezone.utc) - updated_at > timedelta(seconds=max_age_seconds):
                return None

        return json.loads(payload_json)

    async def upsert_snapshot(
        self,
        artifact_type: str,
        scope_key: str,
        payload: dict[str, Any],
        language: str = "",
        tenant_scope: str = "global",
    ) -> None:
        normalized_scope, raw_scope_key = self._split_scope_key(self._scoped_scope_key(scope_key, tenant_scope))
        await asyncio.to_thread(
            self.backend.upsert_row,
            artifact_type,
            normalized_scope,
            raw_scope_key,
            language,
            json.dumps(payload),
            datetime.now(timezone.utc).isoformat(),
        )

    async def delete_snapshot(
        self,
        artifact_type: str,
        scope_key: str,
        language: str = "",
        tenant_scope: str = "global",
    ) -> int:
        normalized_scope, raw_scope_key = self._split_scope_key(self._scoped_scope_key(scope_key, tenant_scope))
        return await asyncio.to_thread(
            self.backend.delete_row,
            artifact_type,
            normalized_scope,
            raw_scope_key,
            language,
        )

    async def delete_scope_prefix(
        self,
        artifact_type: str,
        scope_prefix: str,
        tenant_scope: str = "global",
    ) -> int:
        normalized_scope, raw_scope_prefix = self._split_scope_key(self._scoped_scope_key(scope_prefix, tenant_scope))
        return await asyncio.to_thread(
            self.backend.delete_prefix_rows,
            artifact_type,
            normalized_scope,
            raw_scope_prefix,
        )

    async def delete_snapshot_all_scopes(
        self,
        artifact_type: str,
        scope_key: str,
        language: str = "",
    ) -> int:
        return await asyncio.to_thread(self.backend.delete_row_all_scopes, artifact_type, scope_key, language)

    async def delete_scope_prefix_all_scopes(
        self,
        artifact_type: str,
        scope_prefix: str,
    ) -> int:
        return await asyncio.to_thread(self.backend.delete_prefix_rows_all_scopes, artifact_type, scope_prefix)

    async def delete_artifact_all_rows(self, artifact_type: str) -> int:
        return await asyncio.to_thread(self.backend.delete_artifact_rows, artifact_type)

    async def ensure_workspace(self, workspace_id: str) -> None:
        await asyncio.to_thread(
            self.backend.ensure_workspace_row,
            workspace_id,
            datetime.now(timezone.utc).isoformat(),
        )

    def _build_backend(self) -> SnapshotBackend:
        if self.database_url and self.database_url.startswith("postgresql://"):
            return PostgresSnapshotBackend(self.database_url)
        if self.database_url and self.database_url.startswith("postgres://"):
            normalized_url = "postgresql://" + self.database_url[len("postgres://") :]
            return PostgresSnapshotBackend(normalized_url)
        return SqliteSnapshotBackend(self.database_path)

    @staticmethod
    def _scoped_scope_key(scope_key: str, tenant_scope: str) -> str:
        normalized_scope = (tenant_scope or "global").strip() or "global"
        if normalized_scope == "global":
            return scope_key
        return f"{normalized_scope}::{scope_key}"

    @staticmethod
    def _split_scope_key(scope_key: str) -> tuple[str, str]:
        if "::" not in scope_key:
            return "global", scope_key
        tenant_scope, raw_scope_key = scope_key.split("::", 1)
        return tenant_scope or "global", raw_scope_key

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None


snapshot_store = SnapshotStore(settings.DATABASE_URL, settings.DATABASE_PATH)
