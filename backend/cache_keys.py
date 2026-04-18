"""
Central definitions for Redis cache keys. Import from here to avoid drift between
GitHubService, AIService, and cache invalidation (e.g. DELETE /api/cache/{username}).
"""

GITHUB_USER_CACHE_VERSION = "v4"
REPOSITORY_ANALYSIS_CACHE_VERSION = "v4"
REPOSITORY_PROFILE_CACHE_VERSION = "v1"


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


def repository_profile_cache_key(full_name: str) -> str:
    normalized = full_name.strip().lower()
    return f"github:repo:{REPOSITORY_PROFILE_CACHE_VERSION}:{normalized}"


def repo_profile_cache_key(owner: str, repo: str) -> str:
    """Cache key for repository profiles. Format: repo:profile:v1:{owner_lower}/{repo_lower}"""
    return f"repo:profile:{REPOSITORY_PROFILE_CACHE_VERSION}:{owner.strip().lower()}/{repo.strip().lower()}"


def benchmark_cache_key(
    mine: str,
    benchmarks: list[str],
    language: str = "en",
    include_narrative: bool = False,
) -> str:
    """Generate cache key for benchmark analysis results."""
    import hashlib
    mine_hash = hashlib.md5(mine.strip().lower().encode()).hexdigest()[:8]
    bench_hash = hashlib.md5(",".join(sorted(item.strip().lower() for item in benchmarks)).encode()).hexdigest()[:8]
    narrative_flag = "n1" if include_narrative else "n0"
    return f"benchmark:v2:{mine_hash}:{bench_hash}:{language}:{narrative_flag}"


def benchmark_result_cache_key(mine: str, benchmarks: list[str]) -> str:
    """Cache key for benchmark results. Format: benchmark:v1:{mine_hash}:{benchmarks_hash}"""
    import hashlib
    mine_hash = hashlib.md5(mine.strip().lower().encode()).hexdigest()[:8]
    benchmarks_hash = hashlib.md5(",".join(sorted(item.strip().lower() for item in benchmarks)).encode()).hexdigest()[:8]
    return f"benchmark:v1:{mine_hash}:{benchmarks_hash}"


def suggestion_cache_key(repo: str, limit: int) -> str:
    """Generate cache key for benchmark suggestions."""
    import hashlib
    repo_hash = hashlib.md5(repo.encode()).hexdigest()[:8]
    return f"suggestions:v1:{repo_hash}:{limit}"
