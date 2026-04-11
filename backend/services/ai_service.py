"""
AI Service for generating insights using LLM.

This service integrates with LLM APIs (DeepSeek, GPT-4o-mini, etc.) to generate:
- Style tags describing coding patterns
- Roast comments with programming humor
- Tech stack summaries

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

import json
import logging
from typing import List

import httpx

from config import settings
from cache_keys import repository_analysis_cache_key
from models import GitScore, Repository, RepositoryAIAnalysis, UserData
from utils.redis_client import redis_client

logger = logging.getLogger(__name__)

AI_CACHE_TTL = 604800


class AIService:
    """Service for generating AI-powered insights about developers."""

    def __init__(self):
        self.api_key = (settings.AI_API_KEY or "").strip()
        self.api_base_url = settings.AI_API_BASE_URL
        self.model = settings.AI_MODEL
        self.timeout = float(settings.AI_REQUEST_TIMEOUT)
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        if not self.api_key:
            logger.warning(
                "AI_API_KEY 未配置：标签、吐槽与技术摘要将使用本地 fallback。"
                "请在 backend/.env 中设置 AI_API_KEY（与仓库根目录启动无关，已固定读取 backend/.env）。"
            )

    async def close(self):
        await self.client.aclose()

    @staticmethod
    def _extract_message_content(result: dict) -> str:
        """Parse OpenAI-compatible chat completion JSON (incl. some multimodal shapes)."""
        choices = result.get("choices")
        if not choices:
            raise KeyError("choices")
        choice0 = choices[0]
        message = choice0.get("message") or choice0.get("delta") or {}
        content = message.get("content")
        if content is None:
            raise KeyError("message.content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: List[str] = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text" and "text" in block:
                        parts.append(str(block["text"]))
                    elif "text" in block:
                        parts.append(str(block["text"]))
                elif isinstance(block, str):
                    parts.append(block)
            return "".join(parts).strip()
        return str(content).strip()

    async def _call_llm(self, prompt: str, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500,
        }

        if not self.api_key:
            raise ValueError("AI_API_KEY not configured")

        try:
            base_url = self.api_base_url.rstrip("/")
            if base_url.endswith("/chat/completions"):
                url = base_url
            else:
                url = f"{base_url}/chat/completions"

            response = await self.client.post(
                url,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            return self._extract_message_content(result)
        except httpx.TimeoutException:
            logger.error("LLM API call timed out after %s seconds", self.timeout)
            raise
        except httpx.HTTPStatusError as error:
            body = (error.response.text[:800] if error.response is not None else "") or ""
            logger.error(
                "LLM HTTP %s: %s",
                error.response.status_code if error.response else "?",
                body,
            )
            raise
        except httpx.HTTPError as error:
            logger.error("LLM API call failed: %s", error)
            raise
        except (KeyError, TypeError, ValueError) as error:
            logger.error("Unexpected LLM response JSON: %s", error)
            raise

    async def generate_style_tags(
        self,
        user_data: UserData,
        gitscore: GitScore,
        language: str = "en",
    ) -> List[str]:
        """Generate 3-5 style tags describing coding patterns."""
        cache_key = f"ai:{user_data.username}:tags:{language}"
        cached_tags = await redis_client.get(cache_key)
        if cached_tags:
            logger.info("Cache hit for style tags: %s", user_data.username)
            return cached_tags.get("tags", self._get_fallback_tags(language))

        top_languages = sorted(user_data.languages.items(), key=lambda item: item[1], reverse=True)[:3]
        top_langs_str = ", ".join(lang for lang, _ in top_languages)
        top_repos = sorted(user_data.repositories, key=lambda repo: repo.stars, reverse=True)[:3]
        top_repo_str = top_repos[0].name if top_repos else "N/A"

        lang_instruction = "in Chinese (Simplified)" if language == "zh" else "in English"
        system_prompt = (
            "You are analyzing a developer's GitHub profile. "
            "Generate 3-5 creative style tags (2-4 characters each in Chinese, 1-3 words in English) "
            f"that describe coding patterns. Use # prefix and output {lang_instruction}."
        )
        user_prompt = f"""Developer Profile:
- Primary languages: {top_langs_str}
- Commits last year: {user_data.contributions.total_commits_last_year}
- Pull requests: {user_data.contributions.total_prs_last_year}
- Top repository: {top_repo_str}
- GitScore: {gitscore.total:.1f}/100
- Project Impact: {gitscore.dimensions.get('impact', 0):.1f}/35
- Community Activity: {gitscore.dimensions.get('community', 0):.1f}/20

Generate 3-5 style tags. Output ONLY a JSON array like ["#tag1", "#tag2", "#tag3"].
No additional text or explanation."""

        try:
            response = await self._call_llm(user_prompt, system_prompt)
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(line for line in lines if not line.startswith("```"))

            tags = json.loads(response)
            validated_tags = []
            for tag in tags[:5]:
                cleaned = tag.strip()
                if not cleaned.startswith("#"):
                    cleaned = f"#{cleaned}"
                validated_tags.append(cleaned)

            result_tags = validated_tags if validated_tags else self._get_fallback_tags(language)
            await redis_client.set(cache_key, {"tags": result_tags}, AI_CACHE_TTL)
            logger.info("Cached style tags for %s", user_data.username)
            return result_tags
        except httpx.TimeoutException:
            logger.warning("AI service timed out generating style tags for %s", user_data.username)
            return self._get_fallback_tags(language)
        except ValueError as error:
            if str(error) == "AI_API_KEY not configured":
                logger.warning("Skipping LLM for style tags (%s): %s", user_data.username, error)
                return self._get_fallback_tags(language)
            logger.error("Failed to generate style tags for %s: %s", user_data.username, error)
            return self._get_fallback_tags(language)
        except (httpx.HTTPError, json.JSONDecodeError, KeyError) as error:
            logger.error("Failed to generate style tags for %s: %s", user_data.username, error)
            return self._get_fallback_tags(language)
        except Exception as error:
            logger.error("Unexpected error generating style tags for %s: %s", user_data.username, error)
            return self._get_fallback_tags(language)

    async def generate_roast_comment(
        self,
        user_data: UserData,
        gitscore: GitScore,
        language: str = "en",
    ) -> str:
        """Generate a short, friendly roast comment."""
        cache_key = f"ai:{user_data.username}:roast:{language}"
        cached_roast = await redis_client.get(cache_key)
        if cached_roast:
            logger.info("Cache hit for roast comment: %s", user_data.username)
            return cached_roast.get("comment", "")

        top_languages = sorted(user_data.languages.items(), key=lambda item: item[1], reverse=True)[:2]
        top_lang = top_languages[0][0] if top_languages else "Unknown"
        lang_instruction = "in Chinese (Simplified)" if language == "zh" else "in English"
        char_limit = "30 characters" if language == "zh" else "60 characters"
        system_prompt = (
            "You are a humorous but friendly code reviewer. "
            f"Write one respectful programming joke about this developer in {lang_instruction}. "
            f"Stay within {char_limit}."
        )
        user_prompt = f"""Developer Profile:
- Primary language: {top_lang}
- Commits last year: {user_data.contributions.total_commits_last_year}
- GitScore: {gitscore.total:.1f}/100
- Followers: {user_data.followers}

Generate ONE humorous roast comment. Output ONLY the comment text, no quotes or additional text."""

        try:
            response = await self._call_llm(user_prompt, system_prompt)
            comment = response.strip().strip('"').strip("'")
            max_len = 30 if language == "zh" else 60
            if len(comment) > max_len:
                comment = comment[: max_len - 3] + "..."

            await redis_client.set(cache_key, {"comment": comment}, AI_CACHE_TTL)
            logger.info("Cached roast comment for %s", user_data.username)
            return comment
        except ValueError as error:
            if str(error) == "AI_API_KEY not configured":
                logger.warning("Skipping LLM for roast (%s): %s", user_data.username, error)
                return ""
            logger.warning("Roast generation error for %s: %s", user_data.username, error)
            return ""
        except (httpx.TimeoutException, httpx.HTTPError) as error:
            logger.warning("Skipping roast comment for %s: %s", user_data.username, error)
            return ""
        except Exception as error:
            logger.error("Unexpected error generating roast comment for %s: %s", user_data.username, error)
            return ""

    async def generate_tech_summary(self, user_data: UserData, language: str = "en") -> str:
        """Generate a brief tech stack summary."""
        cache_key = f"ai:{user_data.username}:summary:v2:{language}"
        cached_summary = await redis_client.get(cache_key)
        if cached_summary:
            logger.info("Cache hit for tech summary: %s", user_data.username)
            return cached_summary.get("summary", self._get_fallback_summary(user_data, language))

        top_languages = sorted(user_data.languages.items(), key=lambda item: item[1], reverse=True)[:5]
        langs_str = ", ".join(lang for lang, _ in top_languages)
        total_stars = sum(repo.stars for repo in user_data.repositories)
        total_repos = len(user_data.repositories)
        lang_instruction = "in Chinese (Simplified)" if language == "zh" else "in English"
        system_prompt = (
            "You write CV / resume bullet points (not a cover letter). "
            f"Output in {lang_instruction}. "
            "Each line must start with '- ' (markdown bullet). "
            "3–5 bullets only. Each bullet: one fact-heavy line—stack, scale (repo count, stars), "
            "activity (commits/PRs), domains—no storytelling, no school/employer narrative unless it appears in the bio field. "
            "No 'I think', no self-praise adjectives like 'passionate' or 'potential'. "
            "No hashtags."
        )
        user_prompt = f"""Public GitHub facts for resume bullets:
- Display name: {user_data.name or user_data.username}
- Primary languages (by bytes): {langs_str}
- Public repositories: {total_repos}
- Stars across repos: {total_stars}
- Followers: {user_data.followers}
- Commits last year: {user_data.contributions.total_commits_last_year}
- PRs last year: {user_data.contributions.total_prs_last_year}
- Bio (optional, use only if factual): {user_data.bio or 'N/A'}

Write ONLY the bullet list, nothing else."""

        try:
            response = await self._call_llm(user_prompt, system_prompt)
            summary = response.strip()
            await redis_client.set(cache_key, {"summary": summary}, AI_CACHE_TTL)
            logger.info("Cached tech summary for %s", user_data.username)
            return summary
        except ValueError as error:
            if str(error) == "AI_API_KEY not configured":
                logger.warning("Skipping LLM for summary (%s): %s", user_data.username, error)
                return self._get_fallback_summary(user_data, language)
            logger.warning("Tech summary error for %s: %s", user_data.username, error)
            return self._get_fallback_summary(user_data, language)
        except (httpx.TimeoutException, httpx.HTTPError) as error:
            logger.warning("Using fallback tech summary for %s: %s", user_data.username, error)
            return self._get_fallback_summary(user_data, language)
        except Exception as error:
            logger.error("Unexpected error generating tech summary for %s: %s", user_data.username, error)
            return self._get_fallback_summary(user_data, language)

    async def generate_repository_analysis(
        self,
        user_data: UserData,
        repository: Repository,
        language: str = "en",
    ) -> RepositoryAIAnalysis:
        cache_key = repository_analysis_cache_key(user_data.username, repository.name, language)
        cached = await redis_client.get(cache_key)
        if cached:
            return RepositoryAIAnalysis(
                repo_name=repository.name,
                title=cached.get("title", ""),
                summary=cached.get("summary", ""),
                highlights=cached.get("highlights", []),
                keywords=cached.get("keywords", []),
            )

        readme_excerpt = (repository.readme_text or "")[:2500]
        topics_text = ", ".join(repository.topics[:8]) or "None"
        file_tree_text = ", ".join(repository.file_tree[:15]) or "Unknown"
        lang_instruction = "in Chinese (Simplified)" if language == "zh" else "in English"
        system_prompt = (
            "You are a senior engineering manager writing concise resume-ready repository analysis. "
            f"Respond {lang_instruction}. Return ONLY valid JSON with keys: title, summary, highlights, keywords. "
            "title should be 1 short line. summary should be 1-2 sentences. highlights must be an array of 3 short bullet-style strings. "
            "keywords must be an array of 3-5 short tags without #."
        )
        user_prompt = f"""Repository facts:
- Owner: {user_data.username}
- Repository: {repository.name}
- Description: {repository.description or "N/A"}
- Primary language: {repository.language}
- Stars: {repository.stars}
- Forks: {repository.forks}
- Topics: {topics_text}
- Has README: {repository.has_readme}
- Has License: {repository.has_license}
- Root files: {file_tree_text}
- README excerpt:
{readme_excerpt or "N/A"}

Analyze what this repository says about the developer, what kind of project it is, and why it deserves a place on a resume."""

        try:
            response = await self._call_llm(user_prompt, system_prompt)
            payload = json.loads(response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip())
            result = RepositoryAIAnalysis(
                repo_name=repository.name,
                title=str(payload.get("title", "")).strip() or repository.name,
                summary=str(payload.get("summary", "")).strip() or self._get_fallback_repository_analysis(repository, language).summary,
                highlights=[str(item).strip() for item in payload.get("highlights", []) if str(item).strip()][:3],
                keywords=[str(item).strip() for item in payload.get("keywords", []) if str(item).strip()][:5],
            )
            if not result.highlights:
                result.highlights = self._get_fallback_repository_analysis(repository, language).highlights
            await redis_client.set(
                cache_key,
                {
                    "title": result.title,
                    "summary": result.summary,
                    "highlights": result.highlights,
                    "keywords": result.keywords,
                },
                AI_CACHE_TTL,
            )
            return result
        except Exception as error:
            logger.warning("Repository analysis fallback for %s/%s: %s", user_data.username, repository.name, error)
            return self._get_fallback_repository_analysis(repository, language)

    def _get_fallback_tags(self, language: str = "en") -> List[str]:
        if language == "zh":
            return ["#代码爱好者", "#开源贡献者", "#技术探索者"]
        return ["#CodeEnthusiast", "#OpenSource", "#TechExplorer"]

    def _get_fallback_summary(self, user_data: UserData, language: str = "en") -> str:
        top_languages = sorted(user_data.languages.items(), key=lambda item: item[1], reverse=True)[:3]
        langs = ", ".join(lang for lang, _ in top_languages) if top_languages else "various technologies"
        total_stars = sum(repo.stars for repo in user_data.repositories)
        total_repos = len(user_data.repositories)
        commits = user_data.contributions.total_commits_last_year
        prs = user_data.contributions.total_prs_last_year

        if language == "zh":
            return (
                f"- 公开仓库 {total_repos} 个，累计星标 {total_stars}；主要语言：{langs}。\n"
                f"- 近一年提交 {commits} 次、Pull Request {prs} 次（GitHub 公开数据）。\n"
                "- 以下技能栈与项目信息由公开仓库语言与仓库元数据汇总。"
            )
        return (
            f"- {total_repos} public repositories, {total_stars} total stars; primary languages: {langs}.\n"
            f"- {commits} commits and {prs} PRs in the last year (public GitHub metrics).\n"
            "- Skills and projects below are inferred from public repositories."
        )

    def _get_fallback_repository_analysis(self, repository: Repository, language: str = "en") -> RepositoryAIAnalysis:
        if language == "zh":
            summary = (
                f"{repository.name} 是一个以 {repository.language or '多技术栈'} 为主的项目，"
                f"结合 README、topics 和仓库结构看，适合放进简历展示工程完成度与项目方向。"
            )
            highlights = [
                f"技术焦点：{repository.language or '多技术栈'}",
                "具备可展示的项目结构与文档信号" if repository.has_readme else "建议补充 README 提升可展示性",
                f"社区反馈：{repository.stars} stars / {repository.forks} forks",
            ]
            keywords = repository.topics[:4] or [repository.language or "project", "resume"]
            title = f"{repository.name} 可作为代表项目"
        else:
            summary = (
                f"{repository.name} is a {repository.language or 'multi-stack'} project that looks strong enough "
                "to represent engineering quality and project direction on a resume."
            )
            highlights = [
                f"Primary stack: {repository.language or 'multi-stack'}",
                "Shows documentation and project structure signals" if repository.has_readme else "Would be stronger with a clearer README",
                f"Community proof: {repository.stars} stars / {repository.forks} forks",
            ]
            keywords = repository.topics[:4] or [repository.language or "project", "resume"]
            title = f"{repository.name} is resume-ready"
        return RepositoryAIAnalysis(
            repo_name=repository.name,
            title=title,
            summary=summary,
            highlights=highlights,
            keywords=keywords,
        )
