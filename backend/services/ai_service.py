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
    def _extract_readme_headings(readme_text: str) -> List[str]:
        headings: List[str] = []
        for line in readme_text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue
            heading = stripped.lstrip("#").strip()
            if heading:
                headings.append(heading)
            if len(headings) >= 8:
                break
        return headings

    @staticmethod
    def _collect_repository_signals(repository: Repository) -> dict[str, bool]:
        file_entries = [item.lower() for item in repository.file_tree]
        joined_files = " ".join(file_entries)
        readme_lower = (repository.readme_text or "").lower()
        readme_headings = [heading.lower() for heading in AIService._extract_readme_headings(repository.readme_text or "")]
        joined_headings = " ".join(readme_headings)

        return {
            "has_tests": any(token in joined_files for token in ("test", "tests", "__tests__", "spec", "specs", "pytest", "vitest", "jest")),
            "has_ci": ".github/workflows" in joined_files or "gitlab-ci" in joined_files or "azure-pipelines" in joined_files,
            "has_docs_dir": any(token in joined_files for token in ("docs/", "doc/", "wiki/")),
            "has_examples": any(token in joined_files for token in ("example", "examples", "demo", "demos")),
            "has_container": any(token in joined_files for token in ("dockerfile", "docker-compose", "compose.yml", "compose.yaml")),
            "has_frontend_app": any(token in joined_files for token in ("src/app", "src/pages", "public/", "index.html", "vite.config", "next.config", "app/")),
            "has_backend_api": any(token in joined_files for token in ("api/", "server", "fastapi", "flask", "django", "express", "routes/", "controllers/")),
            "mentions_architecture": "architecture" in joined_headings or "design" in joined_headings or "架构" in joined_headings,
            "mentions_setup": ("install" in joined_headings or "setup" in joined_headings or "getting started" in joined_headings or "quick start" in joined_headings or "安装" in joined_headings),
            "mentions_demo": ("demo" in joined_headings or "screenshot" in joined_headings or "preview" in joined_headings or "演示" in joined_headings or "效果" in joined_headings),
            "mentions_api": ("api" in joined_headings or "endpoint" in readme_lower or "swagger" in readme_lower),
        }

    @staticmethod
    def _format_repository_signal_notes(signals: dict[str, bool], language: str = "en") -> List[str]:
        copy = {
            "has_tests": ("Visible test-related files detected", "检测到测试相关文件"),
            "has_ci": ("CI/workflow configuration is present", "存在 CI / 工作流配置"),
            "has_docs_dir": ("Dedicated docs directory is present", "存在独立文档目录"),
            "has_examples": ("Examples or demo-related files are present", "存在示例或演示相关文件"),
            "has_container": ("Container or deployment packaging files are present", "存在容器或部署打包文件"),
            "has_frontend_app": ("Frontend application structure is visible", "可见前端应用结构"),
            "has_backend_api": ("Backend/API structure is visible", "可见后端 / API 结构"),
            "mentions_architecture": ("README mentions architecture/design", "README 提到了架构或设计"),
            "mentions_setup": ("README includes setup/getting-started cues", "README 包含安装或上手说明"),
            "mentions_demo": ("README includes demo/preview cues", "README 包含演示或预览线索"),
            "mentions_api": ("README references API surface", "README 提到了 API 能力"),
        }
        notes: List[str] = []
        for key, enabled in signals.items():
            if enabled and key in copy:
                notes.append(copy[key][1] if language == "zh" else copy[key][0])
        return notes

    @staticmethod
    def _derive_repository_fit(repository: Repository) -> tuple[str, str]:
        signals = AIService._collect_repository_signals(repository)
        score = 0
        if repository.has_readme:
            score += 2
        if repository.has_license:
            score += 1
        if len(repository.file_tree) >= 4:
            score += 1
        if len(repository.topics) >= 2:
            score += 1
        if repository.stars + repository.forks >= 20:
            score += 1
        if signals["has_tests"]:
            score += 1
        if signals["has_ci"]:
            score += 1
        if signals["mentions_demo"] or signals["has_examples"]:
            score += 1

        evidence_count = 0
        evidence_count += 1 if repository.has_readme else 0
        evidence_count += 1 if repository.has_license else 0
        evidence_count += 1 if len(repository.file_tree) >= 3 else 0
        evidence_count += 1 if len(repository.topics) >= 2 else 0
        evidence_count += 1 if repository.stars + repository.forks >= 5 else 0
        evidence_count += 1 if signals["has_tests"] else 0
        evidence_count += 1 if signals["has_ci"] else 0
        evidence_count += 1 if signals["mentions_demo"] or signals["has_examples"] else 0

        if score >= 7:
            fit = "resume_ready"
        elif score >= 4:
            fit = "portfolio_ready"
        else:
            fit = "needs_hardening"

        if evidence_count >= 6:
            confidence = "high"
        elif evidence_count >= 3:
            confidence = "medium"
        else:
            confidence = "low"

        return fit, confidence

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
                strengths=cached.get("strengths", []),
                risks=cached.get("risks", []),
                resume_bullets=cached.get("resume_bullets", []),
                next_steps=cached.get("next_steps", []),
                showcase_fit=cached.get("showcase_fit", ""),
                confidence=cached.get("confidence", "medium"),
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
                strengths=db_snapshot.get("strengths", []),
                risks=db_snapshot.get("risks", []),
                resume_bullets=db_snapshot.get("resume_bullets", []),
                next_steps=db_snapshot.get("next_steps", []),
                showcase_fit=db_snapshot.get("showcase_fit", ""),
                confidence=db_snapshot.get("confidence", "medium"),
            )

        fallback = self._get_fallback_repository_analysis(repository, language)
        readme_excerpt = (repository.readme_text or "")[:3000]
        readme_headings = self._extract_readme_headings(repository.readme_text or "")
        observed_signals = self._collect_repository_signals(repository)
        topics_text = ", ".join(repository.topics[:8]) or "None"
        file_tree_text = ", ".join(repository.file_tree[:15]) or "Unknown"
        readme_headings_text = ", ".join(readme_headings[:8]) or "None"
        observed_signals_text = "; ".join(self._format_repository_signal_notes(observed_signals, language)) or "None"
        lang_instruction = "in Chinese (Simplified)" if language == "zh" else "in English"
        system_prompt = (
            "You are a senior engineer writing evidence-based repository analysis for a resume workspace. "
            f"Respond {lang_instruction}. Return ONLY valid JSON with keys: title, summary, highlights, keywords, evidence, strengths, risks, resume_bullets, next_steps, showcase_fit, confidence. "
            "Use only the provided facts. Do not invent business impact, production usage, users, code quality, "
            "architecture quality, maintainership, or team size. Avoid generic praise. "
            "title: one short factual line. summary: 2-4 concise sentences that explain what the repository demonstrates and what remains unclear. "
            "highlights: exactly 3 short factual bullets. keywords: 3-5 short factual tags without #. "
            "evidence: 3-5 short fact strings quoted from or directly derived from the inputs. "
            "strengths: 2-4 concrete strengths visible from docs, structure, activity, topics, or traction. "
            "risks: 1-3 concrete gaps, ambiguities, or missing trust signals. "
            "resume_bullets: 2-3 sharper bullets the user could adapt into a resume or portfolio description, still factual and non-hyped. "
            "next_steps: 2-3 specific improvements that would make the repository easier to trust, review, or present. "
            "showcase_fit: one of resume_ready, portfolio_ready, needs_hardening. "
            "confidence: one of high, medium, low based on how much direct public evidence exists."
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
- README headings: {readme_headings_text}
- Observed engineering signals: {observed_signals_text}
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
                strengths=[str(item).strip() for item in payload.get("strengths", []) if str(item).strip()][:4],
                risks=[str(item).strip() for item in payload.get("risks", []) if str(item).strip()][:3],
                resume_bullets=[str(item).strip() for item in payload.get("resume_bullets", []) if str(item).strip()][:3],
                next_steps=[str(item).strip() for item in payload.get("next_steps", []) if str(item).strip()][:3],
                showcase_fit=str(payload.get("showcase_fit", "")).strip() or fallback.showcase_fit,
                confidence=str(payload.get("confidence", "")).strip() or fallback.confidence,
            )
            while len(result.highlights) < 3:
                result.highlights.append(fallback.highlights[len(result.highlights)])
            if not result.keywords:
                result.keywords = fallback.keywords
            if not result.evidence:
                result.evidence = fallback.evidence
            if not result.strengths:
                result.strengths = fallback.strengths
            if not result.risks:
                result.risks = fallback.risks
            if not result.resume_bullets:
                result.resume_bullets = fallback.resume_bullets
            if not result.next_steps:
                result.next_steps = fallback.next_steps
            await redis_client.set(
                cache_key,
                {
                    "title": result.title,
                    "summary": result.summary,
                    "highlights": result.highlights,
                    "keywords": result.keywords,
                    "evidence": result.evidence,
                    "strengths": result.strengths,
                    "risks": result.risks,
                    "resume_bullets": result.resume_bullets,
                    "next_steps": result.next_steps,
                    "showcase_fit": result.showcase_fit,
                    "confidence": result.confidence,
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
                    "strengths": result.strengths,
                    "risks": result.risks,
                    "resume_bullets": result.resume_bullets,
                    "next_steps": result.next_steps,
                    "showcase_fit": result.showcase_fit,
                    "confidence": result.confidence,
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
                    "strengths": fallback.strengths,
                    "risks": fallback.risks,
                    "resume_bullets": fallback.resume_bullets,
                    "next_steps": fallback.next_steps,
                    "showcase_fit": fallback.showcase_fit,
                    "confidence": fallback.confidence,
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

    def _get_fallback_repository_analysis(self, repository: Repository, language: str = "en") -> RepositoryAIAnalysis:
        language_label = repository.language or ("多技术栈" if language == "zh" else "multi-stack")
        docs_signal = "README + LICENSE" if repository.has_readme and repository.has_license else (
            "README only" if repository.has_readme else ("LICENSE only" if repository.has_license else "limited docs signals")
        )
        structure_signal = ", ".join(repository.file_tree[:4]) if repository.file_tree else (
            "公开结构信息有限" if language == "zh" else "limited visible structure"
        )
        traction_signal = f"{repository.stars} stars / {repository.forks} forks"
        keywords = repository.topics[:4] or [repository.language or "project", "github", "resume"]
        observed_signals = self._collect_repository_signals(repository)
        signal_notes = self._format_repository_signal_notes(observed_signals, language)
        showcase_fit, confidence = self._derive_repository_fit(repository)

        if language == "zh":
            title = f"{repository.name} 仓库快照"
            summary = (
                f"{repository.name} 是一个公开的 {language_label} 仓库，目前能看到的主要证据来自 {docs_signal}、主题标签、"
                f"文件结构和基础互动数据。它可以被视为一个有明确工程痕迹的项目，但如果缺少演示、测试或架构说明，"
                "外部读者仍然很难快速判断实现深度。"
            )
            highlights = [
                f"技术栈可见：{language_label}",
                f"文档与结构信号：{docs_signal}；{structure_signal}",
                f"公开互动信号：{traction_signal}",
            ]
            strengths = [
                f"至少能直接看出主要实现语言或技术栈：{language_label}",
                f"仓库基础可信度信号为 {docs_signal}",
                f"存在公开互动数据，可作为外部关注度参考：{traction_signal}",
            ]
            if signal_notes:
                strengths.append(f"额外工程信号：{signal_notes[0]}")
            risks = [
                "当前判断主要依赖公开 README、文件结构和基础元数据，证据面仍然偏窄。",
                "如果缺少演示、测试说明或架构说明，读者很难判断工程完成度和复杂度。",
            ]
            if not observed_signals["has_tests"]:
                risks.append("未看到明显测试目录或测试配置，工程可验证性不足。")
            resume_bullets = [
                f"独立构建并维护 {repository.name}，采用 {language_label} 实现，公开仓库可直接查看结构与基础文档。",
                f"仓库当前已有 {traction_signal} 的公开互动数据，可作为项目可见度的辅助证明。",
            ]
            next_steps = [
                "在 README 中补齐问题定义、核心方案、运行方式和结果展示。",
                "补充测试、CI、截图或架构说明，降低别人评估项目价值的成本。",
            ]
            if not observed_signals["has_ci"]:
                next_steps.append("补充 CI 或自动化检查，让外部读者更容易相信项目持续可维护。")
            evidence = [
                f"语言：{language_label}",
                f"文档：{docs_signal}",
                f"互动：{traction_signal}",
                f"结构：{structure_signal}",
            ]
        else:
            title = f"{repository.name} project snapshot"
            summary = (
                f"{repository.name} is a public {language_label} repository with visible signals from {docs_signal}, topics, "
                f"file structure, and basic traction. It can be presented as a real engineering project, but if demos, tests, "
                "or architecture notes are missing, reviewers still have limited evidence for implementation depth."
            )
            highlights = [
                f"Visible stack: {language_label}",
                f"Docs and structure: {docs_signal}; {structure_signal}",
                f"Public traction: {traction_signal}",
            ]
            strengths = [
                f"The implementation stack is visible: {language_label}",
                f"Baseline trust signals are present: {docs_signal}",
                f"Public traction is measurable: {traction_signal}",
            ]
            if signal_notes:
                strengths.append(f"Extra engineering signal: {signal_notes[0]}")
            risks = [
                "The assessment is still limited to public README, file structure, and repository metadata.",
                "Without demos, tests, or architecture notes, depth and completeness are harder for reviewers to verify.",
            ]
            if not observed_signals["has_tests"]:
                risks.append("No obvious test directory or test tooling is visible, which weakens implementation trust.")
            resume_bullets = [
                f"Built and maintained {repository.name} in {language_label}, with public repository structure and baseline documentation available for review.",
                f"Repository currently shows {traction_signal}, providing some external proof that the work is visible and reusable.",
            ]
            next_steps = [
                "Add a clearer README section covering the problem, approach, setup, and outputs.",
                "Surface tests, CI, screenshots, or architecture notes so reviewers can evaluate implementation depth faster.",
            ]
            if not observed_signals["has_ci"]:
                next_steps.append("Add CI or automated checks so the repository feels actively maintained and verifiable.")
            evidence = [
                f"Language: {language_label}",
                f"Docs: {docs_signal}",
                f"Traction: {traction_signal}",
                f"Structure: {structure_signal}",
            ]

        return RepositoryAIAnalysis(
            repo_name=repository.name,
            title=title,
            summary=summary,
            highlights=highlights,
            keywords=keywords,
            evidence=evidence,
            strengths=strengths,
            risks=risks,
            resume_bullets=resume_bullets,
            next_steps=next_steps,
            showcase_fit=showcase_fit,
            confidence=confidence,
        )
