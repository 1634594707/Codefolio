"""
AI Service for generating insights using LLM.

This service integrates with LLM APIs (DeepSeek, GPT-4o-mini, etc.) to generate:
- Style tags describing coding patterns
- Roast comments with programming humor
- Tech stack summaries
"""

import json
import logging
from typing import List

import httpx

from cache_keys import repository_analysis_cache_key
from config import settings
from database import (
    ARTIFACT_AI_ROAST,
    ARTIFACT_AI_STYLE_TAGS,
    ARTIFACT_AI_TECH_SUMMARY,
    ARTIFACT_REPOSITORY_ANALYSIS,
    snapshot_store,
)
from models import GitScore, Repository, RepositoryAIAnalysis, UserData
from utils.redis_client import redis_client
from utils.workspace_scope import scoped_cache_key

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
                "AI_API_KEY is not configured; AI outputs will fall back to deterministic local summaries."
            )

    async def close(self):
        await self.client.aclose()

    @staticmethod
    def _extract_message_content(result: dict) -> str:
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
            url = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return self._extract_message_content(response.json())
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
        workspace_scope: str = "global",
    ) -> List[str]:
        cache_key = scoped_cache_key(f"ai:{user_data.username}:tags:{language}", workspace_scope)
        cached_tags = await redis_client.get(cache_key)
        if cached_tags:
            logger.info("Cache hit for style tags: %s", user_data.username)
            return cached_tags.get("tags", self._get_fallback_tags(language))

        db_snapshot = await snapshot_store.get_snapshot(
            ARTIFACT_AI_STYLE_TAGS,
            user_data.username,
            language=language,
            max_age_seconds=AI_CACHE_TTL,
            tenant_scope=workspace_scope,
        )
        if db_snapshot:
            await redis_client.set(cache_key, db_snapshot, AI_CACHE_TTL)
            return db_snapshot.get("tags", self._get_fallback_tags(language))

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
                cleaned = str(tag).strip()
                if not cleaned.startswith("#"):
                    cleaned = f"#{cleaned}"
                validated_tags.append(cleaned)

            result_tags = validated_tags if validated_tags else self._get_fallback_tags(language)
            await redis_client.set(cache_key, {"tags": result_tags}, AI_CACHE_TTL)
            await snapshot_store.upsert_snapshot(
                ARTIFACT_AI_STYLE_TAGS,
                user_data.username,
                {"tags": result_tags},
                language=language,
                tenant_scope=workspace_scope,
            )
            return result_tags
        except httpx.TimeoutException:
            return self._get_fallback_tags(language)
        except ValueError as error:
            if str(error) == "AI_API_KEY not configured":
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
        workspace_scope: str = "global",
    ) -> str:
        cache_key = scoped_cache_key(f"ai:{user_data.username}:roast:{language}", workspace_scope)
        cached_roast = await redis_client.get(cache_key)
        if cached_roast:
            logger.info("Cache hit for roast comment: %s", user_data.username)
            return cached_roast.get("comment", "")

        db_snapshot = await snapshot_store.get_snapshot(
            ARTIFACT_AI_ROAST,
            user_data.username,
            language=language,
            max_age_seconds=AI_CACHE_TTL,
            tenant_scope=workspace_scope,
        )
        if db_snapshot:
            await redis_client.set(cache_key, db_snapshot, AI_CACHE_TTL)
            return db_snapshot.get("comment", "")

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
            await snapshot_store.upsert_snapshot(
                ARTIFACT_AI_ROAST,
                user_data.username,
                {"comment": comment},
                language=language,
                tenant_scope=workspace_scope,
            )
            return comment
        except ValueError as error:
            if str(error) == "AI_API_KEY not configured":
                return ""
            logger.warning("Roast generation error for %s: %s", user_data.username, error)
            return ""
        except (httpx.TimeoutException, httpx.HTTPError) as error:
            logger.warning("Skipping roast comment for %s: %s", user_data.username, error)
            return ""
        except Exception as error:
            logger.error("Unexpected error generating roast comment for %s: %s", user_data.username, error)
            return ""

    async def generate_tech_summary(
        self,
        user_data: UserData,
        language: str = "en",
        workspace_scope: str = "global",
    ) -> str:
        cache_key = scoped_cache_key(f"ai:{user_data.username}:summary:v2:{language}", workspace_scope)
        cached_summary = await redis_client.get(cache_key)
        if cached_summary:
            logger.info("Cache hit for tech summary: %s", user_data.username)
            return cached_summary.get("summary", self._get_fallback_summary(user_data, language))

        db_snapshot = await snapshot_store.get_snapshot(
            ARTIFACT_AI_TECH_SUMMARY,
            user_data.username,
            language=language,
            max_age_seconds=AI_CACHE_TTL,
            tenant_scope=workspace_scope,
        )
        if db_snapshot:
            await redis_client.set(cache_key, db_snapshot, AI_CACHE_TTL)
            return db_snapshot.get("summary", self._get_fallback_summary(user_data, language))

        top_languages = sorted(user_data.languages.items(), key=lambda item: item[1], reverse=True)[:5]
        langs_str = ", ".join(lang for lang, _ in top_languages)
        total_stars = sum(repo.stars for repo in user_data.repositories)
        total_repos = len(user_data.repositories)
        lang_instruction = "in Chinese (Simplified)" if language == "zh" else "in English"
        system_prompt = (
            "You write CV / resume bullet points (not a cover letter). "
            f"Output in {lang_instruction}. "
            "Each line must start with '- ' (markdown bullet). "
            "3-4 bullets only. Each bullet should be fact-heavy and concise. "
            "No storytelling, no exaggerated praise, no hashtags."
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
            await snapshot_store.upsert_snapshot(
                ARTIFACT_AI_TECH_SUMMARY,
                user_data.username,
                {"summary": summary},
                language=language,
                tenant_scope=workspace_scope,
            )
            return summary
        except ValueError as error:
            if str(error) == "AI_API_KEY not configured":
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
        workspace_scope: str = "global",
    ) -> RepositoryAIAnalysis:
        cache_key = scoped_cache_key(
            repository_analysis_cache_key(user_data.username, repository.name, language),
            workspace_scope,
        )
        cached = await redis_client.get(cache_key)
        if cached:
            return RepositoryAIAnalysis(
                repo_name=repository.name,
                title=cached.get("title", ""),
                summary=cached.get("summary", ""),
                highlights=cached.get("highlights", []),
                keywords=cached.get("keywords", []),
                evidence=cached.get("evidence", []),
            )

        db_snapshot = await snapshot_store.get_snapshot(
            ARTIFACT_REPOSITORY_ANALYSIS,
            f"{user_data.username}/{repository.name.lower()}",
            language=language,
            max_age_seconds=AI_CACHE_TTL,
            tenant_scope=workspace_scope,
        )
        if db_snapshot:
            await redis_client.set(cache_key, db_snapshot, AI_CACHE_TTL)
            return RepositoryAIAnalysis(
                repo_name=repository.name,
                title=db_snapshot.get("title", ""),
                summary=db_snapshot.get("summary", ""),
                highlights=db_snapshot.get("highlights", []),
                keywords=db_snapshot.get("keywords", []),
                evidence=db_snapshot.get("evidence", []),
            )

        fallback = self._get_fallback_repository_analysis(repository, language)
        readme_excerpt = (repository.readme_text or "")[:3000]
        topics_text = ", ".join(repository.topics[:8]) or "None"
        file_tree_text = ", ".join(repository.file_tree[:15]) or "Unknown"
        lang_instruction = "in Chinese (Simplified)" if language == "zh" else "in English"
        system_prompt = (
            "You are a senior engineer writing evidence-based repository analysis for a resume workspace. "
            f"Respond {lang_instruction}. Return ONLY valid JSON with keys: title, summary, highlights, keywords, evidence. "
            "Use only the provided facts. Do not invent business impact, production usage, users, code quality, "
            "architecture quality, maintainership, or team size. Avoid generic praise. "
            "title: one short factual line. summary: 1-2 concise sentences. "
            "highlights: exactly 3 short factual bullets. keywords: 3-5 short factual tags without #. "
            "evidence: 3-5 short fact strings quoted from or directly derived from the inputs."
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

Write an evidence-based analysis. If evidence is weak, say that explicitly instead of over-claiming."""

        try:
            response = await self._call_llm(user_prompt, system_prompt)
            cleaned = response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            payload = json.loads(cleaned)
            result = RepositoryAIAnalysis(
                repo_name=repository.name,
                title=str(payload.get("title", "")).strip() or fallback.title,
                summary=str(payload.get("summary", "")).strip() or fallback.summary,
                highlights=[str(item).strip() for item in payload.get("highlights", []) if str(item).strip()][:3],
                keywords=[str(item).strip() for item in payload.get("keywords", []) if str(item).strip()][:5],
                evidence=[str(item).strip() for item in payload.get("evidence", []) if str(item).strip()][:5],
            )
            while len(result.highlights) < 3:
                result.highlights.append(fallback.highlights[len(result.highlights)])
            if not result.keywords:
                result.keywords = fallback.keywords
            if not result.evidence:
                result.evidence = fallback.evidence
            await redis_client.set(
                cache_key,
                {
                    "title": result.title,
                    "summary": result.summary,
                    "highlights": result.highlights,
                    "keywords": result.keywords,
                    "evidence": result.evidence,
                },
                AI_CACHE_TTL,
            )
            await snapshot_store.upsert_snapshot(
                ARTIFACT_REPOSITORY_ANALYSIS,
                f"{user_data.username}/{repository.name.lower()}",
                {
                    "title": result.title,
                    "summary": result.summary,
                    "highlights": result.highlights,
                    "keywords": result.keywords,
                    "evidence": result.evidence,
                },
                language=language,
                tenant_scope=workspace_scope,
            )
            return result
        except Exception as error:
            logger.warning("Repository analysis fallback for %s/%s: %s", user_data.username, repository.name, error)
            await snapshot_store.upsert_snapshot(
                ARTIFACT_REPOSITORY_ANALYSIS,
                f"{user_data.username}/{repository.name.lower()}",
                {
                    "title": fallback.title,
                    "summary": fallback.summary,
                    "highlights": fallback.highlights,
                    "keywords": fallback.keywords,
                    "evidence": fallback.evidence,
                },
                language=language,
                tenant_scope=workspace_scope,
            )
            return fallback

    def _get_fallback_tags(self, language: str = "en") -> List[str]:
        if language == "zh":
            return ["#寮€婧愬紑鍙?", "#鎶€鏈帰绱?", "#浠ｇ爜瀹炶返"]
        return ["#OpenSource", "#TechExplorer", "#CodeBuilder"]

    def _get_fallback_summary(self, user_data: UserData, language: str = "en") -> str:
        top_languages = sorted(user_data.languages.items(), key=lambda item: item[1], reverse=True)[:3]
        langs = ", ".join(lang for lang, _ in top_languages) if top_languages else "various technologies"
        total_stars = sum(repo.stars for repo in user_data.repositories)
        total_repos = len(user_data.repositories)
        commits = user_data.contributions.total_commits_last_year
        prs = user_data.contributions.total_prs_last_year

        if language == "zh":
            return (
                f"- 鍏紑浠撳簱 {total_repos} 涓紝绱鏄熸爣 {total_stars}锛屼富瑕佽瑷€涓?{langs}銆?\n"
                f"- 杩戜竴骞存彁浜?{commits} 娆★紝Pull Request {prs} 娆★紝鍩轰簬鍏紑 GitHub 鏁版嵁缁熻銆?\n"
                "- 浠ヤ笅鎶€鑳藉拰椤圭洰琛ㄨ揪锛屽熀浜庡叕寮€浠撳簱鍜屾椿璺冧俊鍙锋暣鐞嗐€?"
            )
        return (
            f"- {total_repos} public repositories with {total_stars} total stars; primary languages: {langs}.\n"
            f"- {commits} commits and {prs} PRs in the last year based on public GitHub activity.\n"
            "- Skills and project signals below are inferred from public repositories."
        )

    def _get_fallback_repository_analysis(self, repository: Repository, language: str = "en") -> RepositoryAIAnalysis:
        language_label = repository.language or ("澶氭妧鏈爤" if language == "zh" else "multi-stack")
        docs_signal = "README + LICENSE" if repository.has_readme and repository.has_license else (
            "README only" if repository.has_readme else ("LICENSE only" if repository.has_license else "limited docs signals")
        )
        structure_signal = ", ".join(repository.file_tree[:4]) if repository.file_tree else (
            "浠撳簱缁撴瀯淇″彿鏈夐檺" if language == "zh" else "limited visible structure"
        )
        traction_signal = f"{repository.stars} stars / {repository.forks} forks"
        keywords = repository.topics[:4] or [repository.language or "project", "github", "resume"]

        if language == "zh":
            summary = (
                f"{repository.name} 鏄竴涓叕寮€{language_label} 浠撳簱锛屽彲瑙佷俊鍙峰寘鎷?{docs_signal}銆乼opics 浠ュ強閮ㄥ垎浠撳簱缁撴瀯銆?"
                "鐩稿浜庣┖娉涘じ璧烇紝鏇撮€傚悎鐢ㄨ繖浜涘叕寮€淇″彿鏉ヨ鏄庨」鐩柟鍚戙€?"
            )
            highlights = [
                f"鍙鎶€鏈俊鍙凤細{language_label}",
                f"鏂囨。/缁撴瀯淇″彿锛?{docs_signal}; {structure_signal}",
                f"鍏紑鍙嶉锛?{traction_signal}",
            ]
            title = f"{repository.name} 椤圭洰蹇収"
        else:
            summary = (
                f"{repository.name} is a public {language_label} repository with visible signals from {docs_signal}, "
                f"topics, and repository structure. It is better described through those concrete signals than through broad claims."
            )
            highlights = [
                f"Visible stack: {language_label}",
                f"Docs and structure: {docs_signal}; {structure_signal}",
                f"Public traction: {traction_signal}",
            ]
            title = f"{repository.name} project snapshot"

        return RepositoryAIAnalysis(
            repo_name=repository.name,
            title=title,
            summary=summary,
            highlights=highlights,
            keywords=keywords,
            evidence=[
                f"Language: {language_label}",
                f"Docs: {docs_signal}",
                f"Traction: {traction_signal}",
                f"Structure: {structure_signal}",
            ],
        )
