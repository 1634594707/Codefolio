"""
Central definitions for Redis cache keys. Import from here to avoid drift between
GitHubService, AIService, and cache invalidation (e.g. DELETE /api/cache/{username}).
"""

GITHUB_USER_CACHE_VERSION = "v4"
REPOSITORY_ANALYSIS_CACHE_VERSION = "v2"


def github_user_cache_key(username: str) -> str:
    return f"github:user:{GITHUB_USER_CACHE_VERSION}:{username}"


def github_user_cache_keys_to_clear(username: str) -> list[str]:
    """Current and legacy keys that may still exist in Redis."""
    return [
        github_user_cache_key(username),
        f"github:user:v2:{username}",
        f"github:user:{username}",
    ]


def ai_cache_keys_to_clear(username: str, languages: tuple[str, ...]) -> list[str]:
    """All AI insight keys for a user (current + legacy summary key)."""
    keys: list[str] = []
    for lang in languages:
        keys.extend(
            [
                f"ai:{username}:tags:{lang}",
                f"ai:{username}:roast:{lang}",
                f"ai:{username}:summary:v2:{lang}",
                f"ai:{username}:summary:{lang}",
            ]
        )
    return keys


def repository_analysis_cache_key(username: str, repo_name: str, language: str) -> str:
    normalized_repo = repo_name.strip().lower()
    return f"ai:{username}:repo-analysis:{REPOSITORY_ANALYSIS_CACHE_VERSION}:{normalized_repo}:{language}"


def repository_analysis_cache_prefix(username: str) -> str:
    return f"ai:{username}:repo-analysis:"
