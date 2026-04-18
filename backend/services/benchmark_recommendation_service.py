"""
Benchmark Recommendation Service

Suggests relevant benchmark repositories based on similarity to the user's repository.
Uses GitHub Search API to find repositories with matching language, topics, and size.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from benchmark_models import BenchmarkSuggestion
from cache_keys import suggestion_cache_key
from config import settings
from services.github_service import GitHubService
from services.repository_profile_service import RepositoryProfileService
from utils.redis_client import redis_client

logger = logging.getLogger(__name__)

# TTL for suggestion cache (1 hour)
SUGGESTION_CACHE_TTL = 3600

# Size category brackets (Requirement 5.3)
def _size_category(stars: int) -> str:
    if stars < 100:
        return "small"
    if stars < 1000:
        return "medium"
    return "large"


class BenchmarkRecommendationService:
    """Suggests relevant benchmark repositories based on similarity."""

    COPY = {
        "en": {
            "size": {
                "small": "Small-scale peer",
                "medium": "Mid-scale peer",
                "large": "Large-scale peer",
            },
            "reason": {
                "overlap_topic_language": {
                    "title": "Strong topical overlap",
                    "summary": "Shares {language} and overlapping topics: {topics}. This is a closer apples-to-apples benchmark.",
                    "learn_from": "Study how it frames the same problem space, packages the README, and turns similar topics into stronger traction.",
                },
                "same_language_size": {
                    "title": "Similar stack and scale",
                    "summary": "Built in {language} and sits in a similar popularity bucket, so the comparison stays realistic.",
                    "learn_from": "Use it to compare repository hygiene, onboarding, release discipline, and polish without jumping to an unrealistic outlier.",
                },
            },
        },
        "zh": {
            "size": {
                "small": "同量级小体量项目",
                "medium": "同量级中等项目",
                "large": "同量级大型项目",
            },
            "reason": {
                "overlap_topic_language": {
                    "title": "主题高度相近",
                    "summary": "同样使用 {language}，并且和你的仓库共享这些主题：{topics}。这是更接近同类对比的标杆。",
                    "learn_from": "重点观察它如何定义同类问题、组织 README，以及把相近主题做出更强的传播和采用。",
                },
                "same_language_size": {
                    "title": "技术栈和体量接近",
                    "summary": "同样基于 {language}，而且项目热度处在相近体量区间，参考价值更现实。",
                    "learn_from": "适合拿来对比仓库卫生、上手体验、发布节奏和整体完成度，而不是和过大体量项目硬比。",
                },
            },
        },
    }

    def __init__(
        self,
        github_service: Optional[GitHubService] = None,
        profile_service: Optional[RepositoryProfileService] = None,
    ):
        self.github = github_service or GitHubService()
        self.profile_service = profile_service or RepositoryProfileService(self.github)

    async def suggest_benchmarks(
        self,
        mine: str,
        limit: int = 3,
        language: str = "en",
    ) -> list[BenchmarkSuggestion]:
        """
        Recommend benchmark repositories similar to the user's repository.

        Uses GitHub Search API to find repositories with:
        - Matching primary language
        - Overlapping topics
        - Similar size category
        - Higher or comparable star count

        Args:
            mine: User's repository full_name (owner/repo)
            limit: Maximum suggestions to return (1-3)
            language: Language for reason text (unused in reason_code, kept for future i18n)

        Returns:
            List of BenchmarkSuggestion with reason_code and reason_params.
            Returns empty list when no suitable matches are found.
        """
        limit = max(1, min(3, limit))

        # Check cache first
        cache_key = suggestion_cache_key(mine, limit)
        cached = await redis_client.get(cache_key)
        if cached and isinstance(cached, list):
            logger.info("Cache hit for suggestions: %s", mine)
            return [BenchmarkSuggestion(**item) for item in cached]

        # Fetch the user's repository profile
        try:
            profile = await self.profile_service.get_profile(mine)
        except Exception as exc:
            logger.warning("Could not fetch profile for %s: %s", mine, exc)
            return []

        repo_language = profile.language
        repo_topics = profile.topics or []
        repo_stars = profile.stars
        mine_lower = mine.strip().lower()
        copy = self.COPY.get(language, self.COPY["en"])

        candidates: list[BenchmarkSuggestion] = []

        # Strategy 1: matching language + topics (Requirement 7.2)
        if repo_language and repo_topics:
            results = await self._search_github(
                language=repo_language,
                topics=repo_topics[:3],  # use up to 3 topics
                min_stars=1,
            )
            for item in results:
                full_name = item.get("full_name", "").lower()
                if full_name == mine_lower:
                    continue
                item_stars = item.get("stargazers_count", 0)
                item_topics = [t.get("name", "") for t in item.get("topics", [])]
                overlapping = [t for t in repo_topics if t in item_topics]
                if not overlapping:
                    continue
                # Filter to similar size category (Requirement 7.3)
                if _size_category(item_stars) != _size_category(repo_stars):
                    continue
                candidates.append(
                    self._build_suggestion(
                        full_name=item.get("full_name", ""),
                        reason_code="overlap_topic_language",
                        reason_params={
                            "topics": overlapping,
                            "language": repo_language,
                            "size_category": _size_category(item_stars),
                        },
                        stars=item_stars,
                        copy=copy,
                    )
                )
                if len(candidates) >= limit * 3:
                    break

        # Strategy 2: fallback — matching language + similar size (Requirement 5.2)
        if len(candidates) < limit and repo_language:
            results = await self._search_github(
                language=repo_language,
                topics=[],
                min_stars=1,
            )
            existing_names = {c.full_name.lower() for c in candidates}
            for item in results:
                full_name = item.get("full_name", "").lower()
                if full_name == mine_lower or full_name in existing_names:
                    continue
                item_stars = item.get("stargazers_count", 0)
                if _size_category(item_stars) != _size_category(repo_stars):
                    continue
                candidates.append(
                    self._build_suggestion(
                        full_name=item.get("full_name", ""),
                        reason_code="same_language_size",
                        reason_params={
                            "language": repo_language,
                            "size_category": _size_category(item_stars),
                        },
                        stars=item_stars,
                        copy=copy,
                    )
                )
                if len(candidates) >= limit * 3:
                    break

        if not candidates:
            logger.info("No benchmark suggestions found for %s", mine)
            return []

        # Rank by relevance: topic-overlap suggestions first, then by star count descending
        def _rank_key(s: BenchmarkSuggestion) -> tuple[int, int]:
            priority = 0 if s.reason_code == "overlap_topic_language" else 1
            return (priority, -s.stars)

        candidates.sort(key=_rank_key)
        suggestions = candidates[:limit]

        # Cache the result
        serialized = [
            {
                "full_name": s.full_name,
                "reason_code": s.reason_code,
                "reason_params": s.reason_params,
                "stars": s.stars,
                "reason_title": s.reason_title,
                "reason_summary": s.reason_summary,
                "learn_from": s.learn_from,
                "badges": s.badges,
            }
            for s in suggestions
        ]
        await redis_client.set(cache_key, serialized, SUGGESTION_CACHE_TTL)

        return suggestions

    async def _search_github(
        self,
        language: str,
        topics: list[str],
        min_stars: int = 1,
    ) -> list[dict]:
        """
        Call GitHub Search API to find repositories.

        Endpoint: GET /search/repositories?q=language:{lang}+topic:{topic}&sort=stars

        Args:
            language: Primary programming language filter
            topics: List of topics to include in query (OR logic via multiple calls)
            min_stars: Minimum star count filter

        Returns:
            List of raw repository items from GitHub Search API.
        """
        headers = {
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        }

        results: list[dict] = []
        seen: set[str] = set()

        # Build query parts
        lang_part = f"language:{language.replace(' ', '+')}"
        stars_part = f"stars:>={min_stars}"

        queries: list[str] = []
        if topics:
            # One query per topic to maximize coverage
            for topic in topics:
                queries.append(f"{lang_part}+topic:{topic}+{stars_part}")
        else:
            queries.append(f"{lang_part}+{stars_part}")

        async with httpx.AsyncClient(timeout=15.0) as client:
            for query in queries:
                try:
                    response = await client.get(
                        f"https://api.github.com/search/repositories",
                        params={"q": query, "sort": "stars", "order": "desc", "per_page": 20},
                        headers=headers,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for item in data.get("items", []):
                            name = item.get("full_name", "").lower()
                            if name and name not in seen:
                                seen.add(name)
                                results.append(item)
                    elif response.status_code == 403:
                        logger.warning("GitHub Search API rate limit hit during suggestions")
                        break
                    else:
                        logger.warning("GitHub Search API returned %d", response.status_code)
                except httpx.TimeoutException:
                    logger.warning("GitHub Search API timed out for query: %s", query)
                except Exception as exc:
                    logger.warning("GitHub Search API error: %s", exc)

        return results

    def _build_suggestion(
        self,
        full_name: str,
        reason_code: str,
        reason_params: dict,
        stars: int,
        copy: dict,
    ) -> BenchmarkSuggestion:
        topics = reason_params.get("topics", [])
        language = reason_params.get("language") or "Code"
        size_category = reason_params.get("size_category") or _size_category(stars)
        template = copy["reason"][reason_code]
        topic_text = ", ".join(topics[:3]) if topics else language
        badges = [language, copy["size"][size_category]]
        badges.extend(topics[:2])
        return BenchmarkSuggestion(
            full_name=full_name,
            reason_code=reason_code,
            reason_params=reason_params,
            stars=stars,
            reason_title=template["title"],
            reason_summary=template["summary"].format(language=language, topics=topic_text),
            learn_from=template["learn_from"],
            badges=badges,
        )
