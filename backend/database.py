import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config import settings


ARTIFACT_GITHUB_USER = "github_user"
ARTIFACT_REPOSITORY_PROFILE = "repository_profile"
ARTIFACT_AI_STYLE_TAGS = "ai_style_tags"
ARTIFACT_AI_ROAST = "ai_roast"
ARTIFACT_AI_TECH_SUMMARY = "ai_tech_summary"
ARTIFACT_REPOSITORY_ANALYSIS = "repository_analysis"
ARTIFACT_BENCHMARK_REPORT = "benchmark_report"


class SnapshotStore:
    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.ready = False

    async def connect(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(self._initialize_schema)
        self.ready = True

    async def close(self) -> None:
        self.ready = False

    async def get_snapshot(
        self,
        artifact_type: str,
        scope_key: str,
        language: str = "",
        max_age_seconds: int | None = None,
        tenant_scope: str = "global",
    ) -> dict[str, Any] | None:
        row = await asyncio.to_thread(
            self._fetch_row,
            artifact_type,
            self._scoped_scope_key(scope_key, tenant_scope),
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
        await asyncio.to_thread(
            self._upsert_row,
            artifact_type,
            self._scoped_scope_key(scope_key, tenant_scope),
            language,
            payload,
        )

    async def delete_snapshot(
        self,
        artifact_type: str,
        scope_key: str,
        language: str = "",
        tenant_scope: str = "global",
    ) -> int:
        return await asyncio.to_thread(
            self._delete_row,
            artifact_type,
            self._scoped_scope_key(scope_key, tenant_scope),
            language,
        )

    async def delete_scope_prefix(
        self,
        artifact_type: str,
        scope_prefix: str,
        tenant_scope: str = "global",
    ) -> int:
        return await asyncio.to_thread(
            self._delete_prefix_rows,
            artifact_type,
            self._scoped_scope_key(scope_prefix, tenant_scope),
        )

    async def delete_snapshot_all_scopes(
        self,
        artifact_type: str,
        scope_key: str,
        language: str = "",
    ) -> int:
        return await asyncio.to_thread(self._delete_row_all_scopes, artifact_type, scope_key, language)

    async def delete_scope_prefix_all_scopes(
        self,
        artifact_type: str,
        scope_prefix: str,
    ) -> int:
        return await asyncio.to_thread(self._delete_prefix_rows_all_scopes, artifact_type, scope_prefix)

    async def delete_artifact_all_rows(self, artifact_type: str) -> int:
        return await asyncio.to_thread(self._delete_artifact_rows, artifact_type)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_schema(self) -> None:
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

    def _fetch_row(self, artifact_type: str, scope_key: str, language: str) -> tuple[str, str] | None:
        tenant_scope, raw_scope_key = self._split_scope_key(scope_key)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json, updated_at
                FROM artifact_snapshots
                WHERE artifact_type = ? AND tenant_scope = ? AND scope_key = ? AND language = ?
                LIMIT 1
                """,
                (artifact_type, tenant_scope, raw_scope_key, language or ""),
            ).fetchone()
            if row is None:
                return None
            return row["payload_json"], row["updated_at"]

    def _upsert_row(self, artifact_type: str, scope_key: str, language: str, payload: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(payload)
        tenant_scope, raw_scope_key = self._split_scope_key(scope_key)
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
                (artifact_type, tenant_scope, raw_scope_key, language or "", payload_json, now, now),
            )
            connection.commit()

    def _delete_row(self, artifact_type: str, scope_key: str, language: str) -> int:
        tenant_scope, raw_scope_key = self._split_scope_key(scope_key)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM artifact_snapshots
                WHERE artifact_type = ? AND tenant_scope = ? AND scope_key = ? AND language = ?
                """,
                (artifact_type, tenant_scope, raw_scope_key, language or ""),
            )
            connection.commit()
            return cursor.rowcount

    def _delete_prefix_rows(self, artifact_type: str, scope_prefix: str) -> int:
        tenant_scope, raw_scope_prefix = self._split_scope_key(scope_prefix)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM artifact_snapshots
                WHERE artifact_type = ? AND tenant_scope = ? AND scope_key LIKE ?
                """,
                (artifact_type, tenant_scope, f"{raw_scope_prefix}%"),
            )
            connection.commit()
            return cursor.rowcount

    def _delete_row_all_scopes(self, artifact_type: str, scope_key: str, language: str) -> int:
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

    def _delete_prefix_rows_all_scopes(self, artifact_type: str, scope_prefix: str) -> int:
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

    def _delete_artifact_rows(self, artifact_type: str) -> int:
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

    async def ensure_workspace(self, workspace_id: str) -> None:
        await asyncio.to_thread(self._ensure_workspace_row, workspace_id)

    def _ensure_workspace_row(self, workspace_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO workspaces (workspace_id, created_at, last_seen_at)
                VALUES (?, ?, ?)
                ON CONFLICT(workspace_id)
                DO UPDATE SET last_seen_at = excluded.last_seen_at
                """,
                (workspace_id, now, now),
            )
            connection.commit()

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
    def _parse_timestamp(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


snapshot_store = SnapshotStore(settings.DATABASE_PATH)
