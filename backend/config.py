from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# 始终从 backend 目录加载 .env，避免从仓库根目录启动时读不到 AI_API_KEY
_BACKEND_ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # GitHub API
    GITHUB_TOKEN: str = ""

    # AI API（兼容 OpenAI 风格：DeepSeek、火山方舟 /api/v3/chat/completions 等）
    AI_API_KEY: str = ""
    AI_API_BASE_URL: str = "https://api.deepseek.com/v1"
    AI_MODEL: str = "deepseek-chat"
    AI_REQUEST_TIMEOUT: float = 60.0

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_DB: int = 0

    # Durable snapshot storage
    DATABASE_URL: str = ""
    DATABASE_PATH: str = str(_BACKEND_ROOT / "data" / "codefolio.db")

    # Snapshot freshness / differential TTL strategy (Req 13.3)
    REPOSITORY_METADATA_TTL: int = 3600       # 1 hour  – repo metadata
    REPOSITORY_README_TTL: int = 21600        # 6 hours – README content
    REPOSITORY_STAR_HISTORY_TTL: int = 86400  # 24 hours – star history (Phase 2+)

    # Rate limiting for benchmark endpoints (Req 20.5)
    BENCHMARK_RATE_LIMIT_MAX_REQUESTS: int = 10   # max requests per window
    BENCHMARK_RATE_LIMIT_WINDOW_SECONDS: int = 60  # sliding window in seconds

    # LLM narrative generation
    LLM_NARRATIVE_ENABLED: bool = True
    LLM_MAX_README_CHARS_PER_REPO: int = 12000  # truncation limit per repo README

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Cache TTL (in seconds)
    GITHUB_CACHE_TTL: int = 86400  # 24 hours
    AI_CACHE_TTL: int = 604800  # 7 days

    @property
    def cors_origins_list(self) -> List[str]:
        stripped = self.CORS_ORIGINS.strip()
        if not stripped:
            return []
        if stripped.startswith("[") and stripped.endswith("]"):
            import json

            parsed = json.loads(stripped)
            return [origin.strip() for origin in parsed if str(origin).strip()]
        return [origin.strip() for origin in stripped.split(",") if origin.strip()]

    @property
    def database_backend(self) -> str:
        raw_url = self.DATABASE_URL.strip()
        if raw_url.startswith("postgresql://") or raw_url.startswith("postgres://"):
            return "postgresql"
        return "sqlite"

    @property
    def database_target(self) -> str:
        raw_url = self.DATABASE_URL.strip()
        return raw_url or self.DATABASE_PATH


settings = Settings()
