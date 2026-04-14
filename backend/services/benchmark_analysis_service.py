"""
Benchmark analysis orchestration service.
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Callable

from fastapi.encoders import jsonable_encoder

from benchmark_models import (
    ActionItem,
    AnalysisDimension,
    BenchmarkReport,
    BucketDescription,
    DimensionScore,
    Evidence,
    FeatureMatrix,
    FeatureMatrixCell,
    FeatureMatrixRow,
    Narrative,
    RepositoryProfile,
    SuccessHypothesis,
)
from cache_keys import benchmark_cache_key
from database import ARTIFACT_BENCHMARK_REPORT, snapshot_store
from services.action_generator import generate_action_items
from services.bucket_service import determine_bucket
from services.dimension_analyzer import (
    analyze_community,
    analyze_compliance,
    analyze_discovery,
    analyze_engineering_quality,
    analyze_first_impression,
    analyze_onboarding,
    analyze_positioning,
    analyze_releases,
)
from services.repository_profile_service import RepositoryProfileService
from utils.redis_client import redis_client

logger = logging.getLogger(__name__)


DimensionFn = Callable[[RepositoryProfile], DimensionScore]

_DEFAULT_MAX_README_CHARS = 12000


class BenchmarkAnalysisService:
    def __init__(
        self,
        profile_service: RepositoryProfileService | None = None,
        ai_service=None,
    ):
        self.profile_service = profile_service or RepositoryProfileService()
        self.ai_service = ai_service  # Optional AIService; None disables LLM narrative
        self._analyzers: list[tuple[AnalysisDimension, DimensionFn]] = [
            (AnalysisDimension.POSITIONING, analyze_positioning),
            (AnalysisDimension.FIRST_IMPRESSION, analyze_first_impression),
            (AnalysisDimension.ONBOARDING, analyze_onboarding),
            (AnalysisDimension.ENGINEERING_QUALITY, analyze_engineering_quality),
            (AnalysisDimension.RELEASES, analyze_releases),
            (AnalysisDimension.COMMUNITY, analyze_community),
            (AnalysisDimension.DISCOVERY, analyze_discovery),
            (AnalysisDimension.COMPLIANCE, analyze_compliance),
        ]
        self._labels = {
            "en": {
                AnalysisDimension.POSITIONING: "Positioning",
                AnalysisDimension.FIRST_IMPRESSION: "First impression",
                AnalysisDimension.ONBOARDING: "Onboarding",
                AnalysisDimension.ENGINEERING_QUALITY: "Engineering quality",
                AnalysisDimension.RELEASES: "Releases",
                AnalysisDimension.COMMUNITY: "Community",
                AnalysisDimension.DISCOVERY: "Discovery",
                AnalysisDimension.COMPLIANCE: "Compliance",
            },
            "zh": {
                AnalysisDimension.POSITIONING: "定位表达",
                AnalysisDimension.FIRST_IMPRESSION: "第一印象",
                AnalysisDimension.ONBOARDING: "上手体验",
                AnalysisDimension.ENGINEERING_QUALITY: "工程质量",
                AnalysisDimension.RELEASES: "发布节奏",
                AnalysisDimension.COMMUNITY: "社区协作",
                AnalysisDimension.DISCOVERY: "可发现性",
                AnalysisDimension.COMPLIANCE: "许可合规",
            },
        }
        self._copy = {
            "en": {
                "summary": "The benchmark highlights visible packaging, trust, and onboarding gaps between repositories.",
                "disclaimer": "This is a rule-based comparison built from public repository signals.",
                "partial_failure": "Some benchmark repositories could not be analyzed and were skipped.",
                "narrative_fallback": "Narrative generation is not enabled yet, so this summary remains rule-based.",
            },
            "zh": {
                "summary": "这份对标结果主要突出仓库包装、可信度和上手体验上的可见差距。",
                "disclaimer": "这是基于公开仓库信号的规则分析，不代表因果关系。",
                "partial_failure": "部分标杆仓库分析失败，已自动跳过。",
                "narrative_fallback": "叙述总结暂未接入 LLM，因此当前仍为规则生成。",
            },
        }

    async def compare_repositories(
        self,
        mine: str,
        benchmarks: list[str],
        language: str = "en",
        include_narrative: bool = False,
        force_refresh: bool = False,
        max_readme_chars: int = _DEFAULT_MAX_README_CHARS,
    ) -> BenchmarkReport:
        cache_key = benchmark_cache_key(mine, benchmarks, language, include_narrative)
        if not force_refresh:
            cached = await redis_client.get(cache_key)
            if cached:
                return self._deserialize_report(cached)
            db_snapshot = await snapshot_store.get_snapshot(
                ARTIFACT_BENCHMARK_REPORT,
                cache_key,
                language=language,
                max_age_seconds=3600,
            )
            if db_snapshot:
                await redis_client.set(cache_key, db_snapshot, 3600)
                return self._deserialize_report(db_snapshot)

        mine_profile = await self.profile_service.get_profile(mine, force_refresh=force_refresh)

        benchmark_profiles: list[RepositoryProfile] = []
        skipped = 0
        for full_name in benchmarks:
            try:
                profile = await self.profile_service.get_profile(full_name, force_refresh=force_refresh)
            except Exception:
                skipped += 1
                continue
            benchmark_profiles.append(profile)

        if not benchmark_profiles:
            raise ValueError("No benchmark repositories could be analyzed.")

        all_profiles = [mine_profile, *benchmark_profiles]
        score_table = {profile.full_name: self._analyze_profile(profile) for profile in all_profiles}

        feature_matrix = self._build_feature_matrix(all_profiles, score_table, language)

        narrative, llm_calls = await self._generate_narrative(
            all_profiles=all_profiles,
            feature_matrix=feature_matrix,
            include_narrative=include_narrative,
            language=language,
            max_readme_chars=max_readme_chars,
        )

        report = BenchmarkReport(
            bucket=self._build_bucket(all_profiles, skipped, language),
            profiles={profile.full_name: profile for profile in all_profiles},
            feature_matrix=feature_matrix,
            hypotheses=self._build_hypotheses(mine_profile, benchmark_profiles, score_table, language),
            actions=generate_action_items(
                mine_scores=score_table[mine_profile.full_name],
                benchmark_scores=self._invert_scores(benchmark_profiles, score_table),
                language=language,
            ),
            narrative=narrative,
            generated_at=datetime.now(timezone.utc),
            llm_calls=llm_calls,
        )
        serialized = self._serialize_report(report)
        await redis_client.set(cache_key, serialized, 3600)
        await snapshot_store.upsert_snapshot(
            ARTIFACT_BENCHMARK_REPORT,
            cache_key,
            serialized,
            language=language,
        )
        return report

    def _analyze_profile(self, profile: RepositoryProfile) -> dict[str, DimensionScore]:
        return {dimension.value: analyzer(profile) for dimension, analyzer in self._analyzers}

    def _build_bucket(self, profiles: list[RepositoryProfile], skipped: int, language: str) -> BucketDescription:
        bucket = determine_bucket(profiles)
        if skipped:
            note = self._copy.get(language, self._copy["en"])["partial_failure"]
            bucket = BucketDescription(
                label=bucket.label,
                warning=f"{bucket.warning} {note}".strip() if bucket.warning else note,
            )
        return bucket

    def _build_feature_matrix(
        self,
        profiles: list[RepositoryProfile],
        score_table: dict[str, dict[str, DimensionScore]],
        language: str,
    ) -> FeatureMatrix:
        labels = self._labels.get(language, self._labels["en"])
        rows: list[FeatureMatrixRow] = []

        for dimension, _ in self._analyzers:
            rows.append(
                FeatureMatrixRow(
                    dimension_id=dimension.value,
                    label_key=f"benchmark.dimension.{dimension.value}",
                    label=labels[dimension],
                    cells=[
                        FeatureMatrixCell(
                            repo=profile.full_name,
                            level=score_table[profile.full_name][dimension.value].level,
                            raw={
                                **score_table[profile.full_name][dimension.value].raw_features,
                                "score": score_table[profile.full_name][dimension.value].to_numeric(),
                            },
                        )
                        for profile in profiles
                    ],
                )
            )
        return FeatureMatrix(rows=rows)

    def _build_hypotheses(
        self,
        mine_profile: RepositoryProfile,
        benchmark_profiles: list[RepositoryProfile],
        score_table: dict[str, dict[str, DimensionScore]],
        language: str,
    ) -> list[SuccessHypothesis]:
        labels = self._labels.get(language, self._labels["en"])
        hypotheses: list[SuccessHypothesis] = []

        for dimension, _ in self._analyzers:
            mine_score = score_table[mine_profile.full_name][dimension.value]
            leader = self._find_dimension_leader(benchmark_profiles, score_table, dimension)
            if leader is None:
                continue

            leader_score = score_table[leader.full_name][dimension.value]
            if leader_score.to_numeric() <= mine_score.to_numeric():
                continue

            hypotheses.append(
                SuccessHypothesis(
                    hypothesis_id=f"hypothesis_{dimension.value}",
                    title=self._build_hypothesis_title(labels[dimension], leader.full_name, language),
                    category=dimension.value,
                    evidence=self._build_hypothesis_evidence(
                        dimension=dimension,
                        label=labels[dimension],
                        mine_score=mine_score,
                        leader=leader,
                        leader_score=leader_score,
                        language=language,
                    ),
                    transferability=self._transferability_for_dimension(dimension),
                    caveats=self._build_caveats(dimension, language),
                    confidence="rule_based",
                )
            )

        return hypotheses

    def _find_dimension_leader(
        self,
        benchmark_profiles: list[RepositoryProfile],
        score_table: dict[str, dict[str, DimensionScore]],
        dimension: AnalysisDimension,
    ) -> RepositoryProfile | None:
        if not benchmark_profiles:
            return None
        return max(
            benchmark_profiles,
            key=lambda profile: score_table[profile.full_name][dimension.value].to_numeric(),
        )

    def _build_hypothesis_title(self, label: str, repo_name: str, language: str) -> str:
        if language == "zh":
            return f"{repo_name} 在“{label}”维度更强"
        return f"{repo_name} is ahead on {label.lower()}"

    def _build_hypothesis_evidence(
        self,
        dimension: AnalysisDimension,
        label: str,
        mine_score: DimensionScore,
        leader: RepositoryProfile,
        leader_score: DimensionScore,
        language: str,
    ) -> list[Evidence]:
        evidence = [
            Evidence(
                type="metric",
                detail=self._format_score_gap(label, leader_score.to_numeric(), mine_score.to_numeric(), language),
                repo=leader.full_name,
            )
        ]

        for key, value in leader_score.raw_features.items():
            if value in (False, None, 0, "", [], {}):
                continue
            detail, evidence_type = self._format_feature_evidence(dimension, key, value, language)
            if detail:
                evidence.append(Evidence(type=evidence_type, detail=detail, repo=leader.full_name))
            if len(evidence) >= 3:
                break

        if len(evidence) < 3:
            evidence.extend(self._fallback_profile_evidence(dimension, leader, language)[: 3 - len(evidence)])
        return evidence[:3]

    def _format_score_gap(self, label: str, peer_score: int, mine_score: int, language: str) -> str:
        if language == "zh":
            return f"{label} 评分 {peer_score} 对比 {mine_score}"
        return f"{label} score {peer_score} vs {mine_score}"

    def _format_feature_evidence(
        self,
        dimension: AnalysisDimension,
        key: str,
        value,
        language: str,
    ) -> tuple[str | None, str]:
        messages: dict[AnalysisDimension, dict[str, tuple[str, str]]] = {
            AnalysisDimension.POSITIONING: {
                "has_description": ("Repository description is present", "仓库提供了描述"),
                "description_quality": (f"Description quality score is {value}", f"描述质量评分为 {value}"),
                "readme_h2_count": (f"README has {value} major sections", f"README 有 {value} 个主要分节"),
                "has_clear_purpose": ("README structure suggests a clear purpose", "README 结构体现了明确用途"),
            },
            AnalysisDimension.FIRST_IMPRESSION: {
                "has_screenshot": ("README includes product visuals", "README 包含产品视觉内容"),
                "badge_count": (f"README shows {value} badges", f"README 展示了 {value} 个徽章"),
                "has_toc": ("README includes a table of contents", "README 包含目录"),
            },
            AnalysisDimension.ONBOARDING: {
                "has_quickstart": ("Quickstart guidance is present", "包含快速上手说明"),
                "has_installation": ("Installation steps are documented", "记录了安装步骤"),
                "has_examples_dir": ("Repository includes an examples directory", "仓库包含 examples 目录"),
                "has_demo_link": ("A demo or homepage link is visible", "提供了 demo 或主页链接"),
            },
            AnalysisDimension.ENGINEERING_QUALITY: {
                "has_tests": ("Testing signals are visible", "可以看到测试相关信号"),
                "has_ci": ("CI workflows are configured", "已配置 CI workflow"),
                "has_type_checking": ("Type-checking signals are visible", "可以看到类型检查相关信号"),
                "has_security_policy": ("Security policy is published", "公开了安全策略"),
            },
            AnalysisDimension.RELEASES: {
                "has_releases": ("The project ships public releases", "项目公开发布版本"),
                "release_frequency": (f"{value} releases in the last year", f"最近一年发布 {value} 次"),
                "has_changelog": ("A changelog or release history is visible", "可见 changelog 或版本历史"),
            },
            AnalysisDimension.COMMUNITY: {
                "has_contributing": ("Contribution guidelines are available", "提供了贡献指南"),
                "has_code_of_conduct": ("A code of conduct is published", "公开了行为准则"),
                "has_issue_templates": ("Issue templates are configured", "配置了 Issue Template"),
            },
            AnalysisDimension.DISCOVERY: {
                "topics_count": (f"Repository uses {value} GitHub topics", f"仓库使用了 {value} 个 GitHub topics"),
                "has_description": ("Repository description is present", "仓库提供了描述"),
                "description_length": (f"Description length is {value} characters", f"描述长度为 {value} 个字符"),
                "repo_type": (f"Repository positioning suggests a {value} project", f"仓库定位更像 {value} 类型项目"),
            },
            AnalysisDimension.COMPLIANCE: {
                "has_license_file": ("A license file is present", "存在许可证文件"),
                "license_type": (f"License is {value}", f"许可证为 {value}"),
                "is_permissive": ("The license is permissive", "许可证属于宽松许可"),
            },
        }
        message = messages.get(dimension, {}).get(key)
        if not message:
            return None, "metric"
        return (message[1] if language == "zh" else message[0]), "metric"

    def _fallback_profile_evidence(
        self,
        dimension: AnalysisDimension,
        profile: RepositoryProfile,
        language: str,
    ) -> list[Evidence]:
        evidence: list[Evidence] = []
        if profile.readme_h2_sections:
            detail = (
                f"README section: {profile.readme_h2_sections[0]}"
                if language != "zh"
                else f"README 分节：{profile.readme_h2_sections[0]}"
            )
            evidence.append(Evidence(type="readme_section", detail=detail, repo=profile.full_name))
        if profile.topics:
            detail = f"Topic: {profile.topics[0]}" if language != "zh" else f"Topic：{profile.topics[0]}"
            evidence.append(Evidence(type="topic", detail=detail, repo=profile.full_name))
        if dimension == AnalysisDimension.COMMUNITY and profile.has_contributing:
            detail = "File: CONTRIBUTING" if language != "zh" else "文件：CONTRIBUTING"
            evidence.append(Evidence(type="file", detail=detail, repo=profile.full_name))
        if dimension == AnalysisDimension.COMPLIANCE and profile.has_license_file:
            detail = "File: LICENSE" if language != "zh" else "文件：LICENSE"
            evidence.append(Evidence(type="file", detail=detail, repo=profile.full_name))
        return evidence

    def _transferability_for_dimension(self, dimension: AnalysisDimension) -> str:
        if dimension in {
            AnalysisDimension.POSITIONING,
            AnalysisDimension.FIRST_IMPRESSION,
            AnalysisDimension.ONBOARDING,
            AnalysisDimension.COMPLIANCE,
        }:
            return "high"
        if dimension in {
            AnalysisDimension.ENGINEERING_QUALITY,
            AnalysisDimension.COMMUNITY,
            AnalysisDimension.DISCOVERY,
        }:
            return "medium"
        return "low"

    def _build_caveats(self, dimension: AnalysisDimension, language: str) -> list[str]:
        if language == "zh":
            caveats = ["该判断仅基于公开仓库信号，无法观测团队资源、分发渠道和私有流程。"]
            if dimension == AnalysisDimension.RELEASES:
                caveats.append("发布节奏可能受项目阶段或维护策略影响，不一定代表执行力差异。")
            if dimension == AnalysisDimension.DISCOVERY:
                caveats.append("topics 和描述会影响可发现性，但不直接代表真实产品价值。")
            return caveats

        caveats = ["This is based only on public repository signals, not on team size, distribution, or private process."]
        if dimension == AnalysisDimension.RELEASES:
            caveats.append("Release cadence may reflect project stage or maintenance policy rather than execution quality.")
        if dimension == AnalysisDimension.DISCOVERY:
            caveats.append("Topics and metadata influence discoverability, but they do not directly prove product value.")
        return caveats

    def _invert_scores(
        self,
        benchmark_profiles: list[RepositoryProfile],
        score_table: dict[str, dict[str, DimensionScore]],
    ) -> dict[str, dict[str, DimensionScore]]:
        return {
            dimension.value: {
                profile.full_name: score_table[profile.full_name][dimension.value]
                for profile in benchmark_profiles
            }
            for dimension, _ in self._analyzers
        }

    def _build_narrative(self, language: str, include_narrative: bool) -> Narrative:
        copy = self._copy.get(language, self._copy["en"])
        summary = copy["summary"]
        if include_narrative:
            summary = f"{summary} {copy['narrative_fallback']}"
        return Narrative(summary=summary, disclaimer=copy["disclaimer"])

    async def _generate_narrative(
        self,
        all_profiles: list[RepositoryProfile],
        feature_matrix: FeatureMatrix,
        include_narrative: bool,
        language: str,
        max_readme_chars: int,
    ) -> tuple[Narrative | None, int]:
        """Generate LLM narrative (one call) or return None when disabled.

        Returns (narrative, llm_calls) where llm_calls is 0 when narrative is
        disabled and 1 on a successful LLM call.  On LLM failure the report is
        returned without a narrative field (None) and llm_calls stays 0.
        """
        disclaimer = (
            "Correlation does not imply causation. "
            "This analysis is based on public repository signals only."
        )
        if language == "zh":
            disclaimer = (
                "相关性不代表因果关系。"
                "本分析仅基于公开仓库信号。"
            )

        if not include_narrative:
            return None, 0

        if self.ai_service is None:
            logger.warning("Narrative requested but AIService is not configured; skipping LLM call.")
            copy = self._copy.get(language, self._copy["en"])
            return Narrative(summary=copy["summary"], disclaimer=disclaimer), 0

        # Build the prompt -------------------------------------------------------
        # Feature matrix summary (dimension → levels per repo)
        matrix_lines = []
        for row in feature_matrix.rows:
            cells_str = ", ".join(f"{c.repo}: {c.level}" for c in row.cells)
            matrix_lines.append(f"- {row.label}: {cells_str}")
        matrix_text = "\n".join(matrix_lines)

        # Truncated README content per repository (Req 6.2)
        readme_sections: list[str] = []
        for profile in all_profiles:
            readme_raw = getattr(profile, "readme_text", None) or ""
            truncated = readme_raw[:max_readme_chars]
            if truncated:
                readme_sections.append(f"### {profile.full_name} README (truncated)\n{truncated}")

        readme_text = "\n\n".join(readme_sections) if readme_sections else "(no README content available)"

        if language == "zh":
            system_prompt = (
                "你是一位资深开源开发者，正在对比多个 GitHub 仓库。"
                "请根据下方的特征矩阵和 README 摘要，用中文写一段简洁的对比总结（3-5 句话）。"
                "只描述可观测的差异，不要推断因果关系。"
            )
            user_prompt = (
                f"特征矩阵：\n{matrix_text}\n\n"
                f"README 摘要：\n{readme_text}\n\n"
                "请写一段简洁的对比总结。"
            )
        else:
            system_prompt = (
                "You are a senior open-source developer comparing GitHub repositories. "
                "Write a concise 3-5 sentence narrative summary based on the feature matrix "
                "and README excerpts below. Describe only observable differences; "
                "do not infer causation."
            )
            user_prompt = (
                f"Feature Matrix:\n{matrix_text}\n\n"
                f"README excerpts:\n{readme_text}\n\n"
                "Write a concise comparison narrative."
            )

        try:
            summary = await self.ai_service._call_llm(user_prompt, system_prompt)
            logger.info("LLM narrative generated successfully (llm_calls=1)")
            return Narrative(summary=summary.strip(), disclaimer=disclaimer), 1
        except Exception as exc:
            logger.warning("LLM narrative generation failed; returning report without narrative: %s", exc)
            return None, 0

    def _serialize_report(self, report: BenchmarkReport) -> dict:
        return jsonable_encoder(asdict(report))

    def _deserialize_report(self, payload: dict) -> BenchmarkReport:
        profiles = {
            name: self._deserialize_profile(profile_data)
            for name, profile_data in payload.get("profiles", {}).items()
        }
        rows = [
            FeatureMatrixRow(
                dimension_id=row["dimension_id"],
                label_key=row["label_key"],
                label=row.get("label", row["dimension_id"]),
                cells=[FeatureMatrixCell(**cell) for cell in row.get("cells", [])],
            )
            for row in payload.get("feature_matrix", {}).get("rows", [])
        ]
        hypotheses = [
            SuccessHypothesis(
                hypothesis_id=item["hypothesis_id"],
                title=item["title"],
                category=item["category"],
                evidence=[Evidence(**evidence) for evidence in item.get("evidence", [])],
                transferability=item["transferability"],
                caveats=item.get("caveats", []),
                confidence=item["confidence"],
            )
            for item in payload.get("hypotheses", [])
        ]

        generated_at = payload.get("generated_at")
        if isinstance(generated_at, str):
            generated_at = datetime.fromisoformat(generated_at)

        return BenchmarkReport(
            bucket=BucketDescription(**payload["bucket"]),
            profiles=profiles,
            feature_matrix=FeatureMatrix(rows=rows),
            hypotheses=hypotheses,
            actions=[ActionItem(**action) for action in payload.get("actions", [])],
            narrative=Narrative(**payload["narrative"]) if payload.get("narrative") else None,
            generated_at=generated_at or datetime.now(timezone.utc),
            llm_calls=payload.get("llm_calls", 0),
        )

    def _deserialize_profile(self, payload: dict) -> RepositoryProfile:
        data = dict(payload)
        for field_name in ("created_at", "pushed_at", "fetched_at"):
            value = data.get(field_name)
            if isinstance(value, str):
                try:
                    data[field_name] = datetime.fromisoformat(value)
                except ValueError:
                    data[field_name] = None if field_name != "fetched_at" else datetime.now(timezone.utc)
        return RepositoryProfile(**data)
