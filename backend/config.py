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


settings = Settings()
