"""
ScoreEngine: Multi-dimensional GitHub developer scoring algorithm.

Calculates GitScore (0-100) from five dimensions:
- Impact (0-33): public traction and shipped-repo signals, including quality density
- Contribution (0-24): commits, PRs, issues, and streak consistency
- Community (0-20): followers, maintained projects, and public interest
- Tech Breadth (0-13): language diversity and distribution balance
- Documentation (0-10): README / LICENSE / project metadata quality
"""

import math
from typing import Dict, List

from models import Contributions, GitScore, GitScoreDimensionExplanation, Repository, UserData


class ScoreEngine:
    """Calculate multi-dimensional GitScore from GitHub data."""

    DIMENSION_MAXIMA = {
        "impact": 33.0,
        "contribution": 24.0,
        "community": 20.0,
        "tech_breadth": 13.0,
        "documentation": 10.0,
    }

    COPY = {
        "en": {
            "labels": {
                "impact": "Impact",
                "contribution": "Contribution",
                "community": "Community",
                "tech_breadth": "Tech Breadth",
                "documentation": "Documentation",
            },
            "status": {
                "strong": "strong",
                "steady": "steady",
                "needs_attention": "needs_attention",
            },
            "impact": {
                "empty": "Public repository traction is still sparse, so this score has little evidence to work with.",
                "strong": "Your public repositories already show meaningful traction and shipped-project signals.",
                "steady": "There is visible project traction, but flagship reach is still uneven.",
                "needs_attention": "Project reach is currently limited by low public traction or too few polished repositories.",
                "evidence": {
                    "stars": "{count} total stars across public repositories.",
                    "forks": "{count} total forks signal reuse beyond your own profile.",
                    "flagship": "Your strongest repository has {count} combined stars/forks.",
                    "shipped": "{count} repositories show shipped-project signals such as docs, license, or early traction.",
                },
                "actions": {
                    "stars": "Invest in one flagship repository that solves a clear problem and is easier to share.",
                    "forks": "Add contributor-friendly setup and examples so more people can reuse the work.",
                    "shipped": "Publish clearer descriptions, README files, or licenses on more repositories.",
                },
            },
            "contribution": {
                "strong": "Your recent coding activity shows strong consistency across commits, PRs, and follow-through.",
                "steady": "Your contribution volume is healthy, but one or two activity signals are still lagging.",
                "needs_attention": "Recent contribution evidence is thin, so this dimension has room to grow quickly.",
                "evidence": {
                    "commits": "{count} commits recorded in the last year.",
                    "prs": "{count} pull requests recorded in the last year.",
                    "issues": "{count} issues opened in the last year.",
                    "streak": "Your longest contribution streak is {count} days.",
                },
                "actions": {
                    "commits": "Sustain a steadier weekly commit cadence on visible repositories.",
                    "prs": "Open more pull requests, especially to projects with review history or collaboration.",
                    "issues": "File issues when you spot bugs or feature gaps to make public problem-solving visible.",
                    "streak": "Aim for shorter but more consistent contribution streaks instead of sporadic bursts.",
                },
            },
            "community": {
                "strong": "Your profile already shows clear public reach and a healthy audience-response loop.",
                "steady": "There is some audience signal, but community reach is still forming.",
                "needs_attention": "Community signal is currently limited and may reflect low visibility more than code quality.",
                "evidence": {
                    "followers": "{count} followers currently track your work.",
                    "following": "You follow {count} accounts, which adds some network context.",
                    "ratio": "Your follower-to-following ratio is {count}.",
                    "low_data": "Low public social data means this dimension has lower confidence for newer profiles.",
                },
                "actions": {
                    "followers": "Share progress updates, release notes, or demos so your best work is easier to discover.",
                    "ratio": "Build reputation through consistent public artifacts instead of optimizing this ratio directly.",
                    "network": "Participate in issue threads, discussions, and PR reviews to grow visible community presence.",
                },
            },
            "tech_breadth": {
                "empty": "No language data was available, so breadth cannot be assessed yet.",
                "strong": "Your profile shows a broad or well-balanced technical footprint.",
                "steady": "You have some stack range, but one language still dominates most of the visible work.",
                "needs_attention": "The public profile currently looks narrow or overly concentrated in one stack.",
                "evidence": {
                    "count": "{count} languages appear in your public repositories.",
                    "dominant": "Your top language accounts for about {count}% of visible code volume.",
                    "balance": "The remaining code is spread across secondary languages, improving range.",
                },
                "actions": {
                    "count": "Showcase one or two additional languages or frameworks in meaningful side projects.",
                    "balance": "Balance the portfolio with repositories where secondary technologies are first-class, not incidental.",
                },
            },
            "documentation": {
                "empty": "Without public repositories, documentation quality cannot be measured yet.",
                "strong": "Repository hygiene is a visible strength across README, licensing, and descriptions.",
                "steady": "Documentation quality is present, but coverage is inconsistent across repositories.",
                "needs_attention": "Repository hygiene is one of the easiest places to raise your score quickly.",
                "evidence": {
                    "readme": "{count}% of repositories include a README.",
                    "license": "{count}% of repositories include a license.",
                    "description": "{count}% of repositories include a description.",
                },
                "actions": {
                    "readme": "Add concise README files that explain setup, purpose, and screenshots or outputs.",
                    "license": "Add licenses to reusable repositories so adoption and forking feel safer.",
                    "description": "Write one-line repository descriptions so visitors can triage your work faster.",
                },
            },
        },
        "zh": {
            "labels": {
                "impact": "影响力",
                "contribution": "贡献度",
                "community": "社区信号",
                "tech_breadth": "技术广度",
                "documentation": "文档完善度",
            },
            "status": {
                "strong": "strong",
                "steady": "steady",
                "needs_attention": "needs_attention",
            },
            "impact": {
                "empty": "公开仓库的外部影响信号还比较少，这个维度目前证据不足。",
                "strong": "你的公开仓库已经表现出不错的传播和成品项目信号。",
                "steady": "已经有一定项目影响力，但旗舰项目的外部触达还不够稳定。",
                "needs_attention": "项目影响力目前主要受限于公开热度不足或成型仓库数量偏少。",
                "evidence": {
                    "stars": "公开仓库累计获得 {count} 个 Star。",
                    "forks": "公开仓库累计获得 {count} 个 Fork，说明已有一定复用信号。",
                    "flagship": "表现最强的仓库合计获得 {count} 个 Star/Fork 信号。",
                    "shipped": "有 {count} 个仓库具备 README、License 或早期热度等成品信号。",
                },
                "actions": {
                    "stars": "重点打磨一个解决明确问题的旗舰仓库，并提高可传播性。",
                    "forks": "补齐上手文档、示例和贡献说明，降低别人复用门槛。",
                    "shipped": "给更多仓库补充描述、README 或 License，提升成品感。",
                },
            },
            "contribution": {
                "strong": "最近一年的代码活跃度、PR 和持续性都比较扎实。",
                "steady": "贡献量整体健康，但还有个别活跃信号偏弱。",
                "needs_attention": "近期公开贡献证据偏薄，这个维度还有明显提升空间。",
                "evidence": {
                    "commits": "最近一年记录了 {count} 次 commit。",
                    "prs": "最近一年记录了 {count} 个 Pull Request。",
                    "issues": "最近一年记录了 {count} 个 issue。",
                    "streak": "最长连续贡献天数为 {count} 天。",
                },
                "actions": {
                    "commits": "在公开仓库里保持更稳定的周级提交节奏。",
                    "prs": "增加带评审记录的 PR，尤其是协作型项目中的贡献。",
                    "issues": "遇到 bug 或需求时主动提 issue，让问题分析过程可见。",
                    "streak": "相比偶发爆发，更建议建立稳定但可持续的贡献节奏。",
                },
            },
            "community": {
                "strong": "你的主页已经体现出比较明确的公开影响范围和受众反馈。",
                "steady": "已经有一定社区信号，但受众覆盖还在形成阶段。",
                "needs_attention": "社区维度当前偏低，更像是曝光不足，不一定代表技术质量差。",
                "evidence": {
                    "followers": "目前有 {count} 位关注者。",
                    "following": "你当前关注了 {count} 个账号，形成了一定网络背景。",
                    "ratio": "关注者/关注比约为 {count}。",
                    "low_data": "公开社交信号偏少，因此这个维度对新账号的判断置信度更低。",
                },
                "actions": {
                    "followers": "多分享进展、发布说明或 Demo，让代表作品更容易被发现。",
                    "ratio": "不用刻意优化比例，更重要的是持续沉淀可被引用的公开成果。",
                    "network": "多参与 issue、讨论区和 PR review，提升可见的社区存在感。",
                },
            },
            "tech_breadth": {
                "empty": "当前没有可用的语言数据，暂时无法判断技术广度。",
                "strong": "你的公开项目展示出了较好的技术覆盖面或栈内平衡。",
                "steady": "已经有一定技术范围，但大部分公开代码仍集中在单一语言上。",
                "needs_attention": "公开画像目前偏窄，或者过度集中在单一技术栈。",
                "evidence": {
                    "count": "公开仓库中出现了 {count} 种语言。",
                    "dominant": "占比最高的语言约占公开代码量的 {count}%。",
                    "balance": "其余代码分布在次要语言上，说明具备一定横向延展。",
                },
                "actions": {
                    "count": "用一两个有代表性的项目展示更多语言或框架能力。",
                    "balance": "补充以次要技术为主角的项目，而不是只在边角中出现。",
                },
            },
            "documentation": {
                "empty": "没有公开仓库时，暂时无法评估文档质量。",
                "strong": "README、License 和仓库描述这些基础卫生做得比较扎实。",
                "steady": "文档质量有基础，但不同仓库之间覆盖度还不稳定。",
                "needs_attention": "仓库卫生是当前最容易快速拉分的维度之一。",
                "evidence": {
                    "readme": "{count}% 的仓库带有 README。",
                    "license": "{count}% 的仓库带有 License。",
                    "description": "{count}% 的仓库带有描述信息。",
                },
                "actions": {
                    "readme": "补上简洁 README，至少说明用途、运行方式和结果示意。",
                    "license": "给可复用仓库补充 License，降低别人采用时的顾虑。",
                    "description": "给仓库写一句话描述，让访客更快理解项目价值。",
                },
            },
        },
    }

    @staticmethod
    def _round_score(value: float) -> float:
        return round(float(value), 1)

    def calculate_gitscore(self, user_data: UserData, language: str = "en") -> GitScore:
        """
        Calculate 0-100 GitScore with dimension breakdown.

        Args:
            user_data: Normalized GitHub user data

        Returns:
            GitScore containing total score and dimension breakdown
        """
        copy = self.COPY.get(language, self.COPY["en"])
        impact_details = self._calculate_impact_details(user_data.repositories, copy)
        contribution_details = self._calculate_contribution_details(user_data.contributions, copy)
        community_details = self._calculate_community_details(user_data.followers, user_data.following, copy)
        tech_breadth_details = self._calculate_tech_breadth_details(user_data.languages, copy)
        documentation_details = self._calculate_documentation_details(user_data.repositories, copy)

        impact = impact_details["score"]
        contribution = contribution_details["score"]
        community = community_details["score"]
        tech_breadth = tech_breadth_details["score"]
        documentation = documentation_details["score"]

        total = self._round_score(min(100.0, impact + contribution + community + tech_breadth + documentation))

        dimensions = {
            "impact": self._round_score(impact),
            "contribution": self._round_score(contribution),
            "community": self._round_score(community),
            "tech_breadth": self._round_score(tech_breadth),
            "documentation": self._round_score(documentation),
        }

        explanations = {
            "impact": self._build_explanation("impact", impact_details, copy),
            "contribution": self._build_explanation("contribution", contribution_details, copy),
            "community": self._build_explanation("community", community_details, copy),
            "tech_breadth": self._build_explanation("tech_breadth", tech_breadth_details, copy),
            "documentation": self._build_explanation("documentation", documentation_details, copy),
        }

        return GitScore(total=total, dimensions=dimensions, explanations=explanations)

    def _status_for_score(self, score: float, maximum: float) -> str:
        ratio = (score / maximum) if maximum > 0 else 0.0
        if ratio >= 0.67:
            return "strong"
        if ratio >= 0.4:
            return "steady"
        return "needs_attention"

    def _format_ratio(self, value: float) -> str:
        if value >= 10:
            return f"{value:.1f}"
        return f"{value:.2f}"

    def _format_copy(self, template: str, count: float | int) -> str:
        return template.format(count=count)

    def _build_explanation(self, key: str, details: Dict[str, object], copy: Dict[str, object]) -> GitScoreDimensionExplanation:
        maximum = self.DIMENSION_MAXIMA[key]
        status = self._status_for_score(float(details["score"]), maximum)
        summary = details["summary_by_status"].get(status) or details["summary_by_status"]["steady"]
        evidence = [item for item in details["evidence"] if item][:3]
        next_steps = [item for item in details["next_steps"] if item][:3]
        confidence = str(details.get("confidence", "high"))
        return GitScoreDimensionExplanation(
            label=copy["labels"][key],
            score=self._round_score(float(details["score"])),
            max_score=maximum,
            status=copy["status"][status],
            summary=summary,
            evidence=evidence,
            next_steps=next_steps,
            low_data=bool(details.get("low_data", False)),
            confidence=confidence,
        )

    def _calculate_quality_density(self, repos: list) -> float:
        """Quality density: log1p(total_stars + total_forks * 2) / log1p(repo_count)"""
        total_stars = sum(repo.stars for repo in repos)
        total_forks = sum(repo.forks for repo in repos)
        repo_count = len(repos)
        if repo_count == 0:
            return 0.0
        return math.log1p(total_stars + total_forks * 2) / math.log1p(repo_count)

    def _calculate_impact_details(self, repos: List[Repository], copy: Dict[str, object]) -> Dict[str, object]:
        if not repos:
            return {
                "score": 0.0,
                "summary_by_status": {
                    "strong": copy["impact"]["empty"],
                    "steady": copy["impact"]["empty"],
                    "needs_attention": copy["impact"]["empty"],
                },
                "evidence": [],
                "next_steps": [
                    copy["impact"]["actions"]["shipped"],
                    copy["impact"]["actions"]["stars"],
                ],
                "low_data": True,
                "confidence": "low",
            }

        total_stars = sum(repo.stars for repo in repos)
        total_forks = sum(repo.forks for repo in repos)
        repo_strength = max((repo.stars + repo.forks * 2) for repo in repos)
        shipped_repos = sum(
            1
            for repo in repos
            if repo.description and (repo.has_readme or repo.has_license or repo.stars + repo.forks >= 3)
        )

        stars_component = min(15.0, math.log1p(total_stars) * 3.5)
        forks_component = min(6.0, math.log1p(total_forks) * 2.2)
        flagship_component = min(4.0, math.log1p(repo_strength) * 1.5)
        shipped_component = min(4.0, shipped_repos * 1.0)

        # Quality density component: rewards high star/fork ratio relative to repo count
        quality_density = self._calculate_quality_density(repos)
        quality_density_component = min(4.0, quality_density * 1.0)

        raw = stars_component + forks_component + flagship_component + shipped_component + quality_density_component
        score = self._round_score(min(33.0, raw))
        evidence = [
            self._format_copy(copy["impact"]["evidence"]["stars"], total_stars),
            self._format_copy(copy["impact"]["evidence"]["forks"], total_forks),
            self._format_copy(copy["impact"]["evidence"]["flagship"], repo_strength),
            self._format_copy(copy["impact"]["evidence"]["shipped"], shipped_repos),
        ]
        next_steps = []
        if total_stars < 25:
            next_steps.append(copy["impact"]["actions"]["stars"])
        if total_forks < 10:
            next_steps.append(copy["impact"]["actions"]["forks"])
        if shipped_repos < max(2, math.ceil(len(repos) * 0.4)):
            next_steps.append(copy["impact"]["actions"]["shipped"])
        low_data = len(repos) < 2
        # Confidence: sparse repos means low confidence in the score
        if len(repos) < 2:
            confidence = "low"
        elif len(repos) < 5:
            confidence = "medium"
        else:
            confidence = "high"

        return {
            "score": score,
            "summary_by_status": {
                "strong": copy["impact"]["strong"],
                "steady": copy["impact"]["steady"],
                "needs_attention": copy["impact"]["needs_attention"],
            },
            "evidence": evidence,
            "next_steps": next_steps or [copy["impact"]["actions"]["stars"]],
            "low_data": low_data,
            "confidence": confidence,
        }

    def _calculate_impact_score(self, repos: List[Repository]) -> float:
        return float(self._calculate_impact_details(repos, self.COPY["en"])["score"])

    def _calculate_contribution_details(self, contributions: Contributions, copy: Dict[str, object]) -> Dict[str, object]:
        commits = contributions.total_commits_last_year
        prs = contributions.total_prs_last_year
        streak = contributions.longest_streak
        issues = getattr(contributions, 'issues_opened_last_year', 0)

        commits_component = min(10.0, math.log1p(commits) * 1.75)
        prs_component = min(7.0, math.log1p(prs) * 2.1)
        # Issue participation weight is >= 50% of PR weight (prs_component max 7.0, issues max >= 3.5)
        issues_component = min(4.0, math.log1p(issues) * 1.2)
        streak_component = min(3.0, streak / 12.0)

        raw = commits_component + prs_component + issues_component + streak_component
        score = self._round_score(min(24.0, raw))
        next_steps = []
        if commits < 120:
            next_steps.append(copy["contribution"]["actions"]["commits"])
        if prs < 20:
            next_steps.append(copy["contribution"]["actions"]["prs"])
        if issues < 10:
            next_steps.append(copy["contribution"]["actions"]["issues"])
        if streak < 14:
            next_steps.append(copy["contribution"]["actions"]["streak"])
        return {
            "score": score,
            "summary_by_status": {
                "strong": copy["contribution"]["strong"],
                "steady": copy["contribution"]["steady"],
                "needs_attention": copy["contribution"]["needs_attention"],
            },
            "evidence": [
                self._format_copy(copy["contribution"]["evidence"]["commits"], commits),
                self._format_copy(copy["contribution"]["evidence"]["prs"], prs),
                self._format_copy(copy["contribution"]["evidence"]["issues"], issues),
                self._format_copy(copy["contribution"]["evidence"]["streak"], streak),
            ],
            "next_steps": next_steps or [copy["contribution"]["actions"]["commits"]],
            "low_data": commits + prs + issues < 25,
            "confidence": "low" if commits + prs + issues < 10 else ("medium" if commits + prs + issues < 25 else "high"),
        }

    def _calculate_contribution_score(self, contributions: Contributions) -> float:
        return float(self._calculate_contribution_details(contributions, self.COPY["en"])["score"])

    def _calculate_community_details(self, followers: int, following: int, copy: Dict[str, object]) -> Dict[str, object]:
        # Reduce follower-heavy bias: cap followers component at 8 instead of 12,
        # shift weight to activity-based signals (following engagement, network breadth)
        followers_component = min(8.0, math.log1p(followers) * 1.8)
        following_component = min(4.0, math.log1p(following) * 1.2)
        relationship_component = 0.0
        if followers > 0:
            ratio = followers / max(following, 1)
            relationship_component = min(5.0, math.log1p(ratio) * 2.2)
        # New: network breadth bonus for active following (engagement signal, not just passive followers)
        network_breadth = min(3.0, math.log1p(following) * 0.6) if following >= 5 else 0.0

        raw = followers_component + following_component + relationship_component + network_breadth
        # Low-data floor: give new users a small baseline so 0 followers ≠ 0 community
        low_data = followers + following < 15
        if low_data and raw < 1.5:
            raw = 1.5  # minimal baseline to distinguish sparse data from absent data

        score = self._round_score(min(20.0, raw))

        # Confidence: how much evidence backs this score
        if followers + following < 5:
            confidence = "low"
        elif low_data:
            confidence = "medium"
        else:
            confidence = "high"

        evidence = [
            self._format_copy(copy["community"]["evidence"]["followers"], followers),
            self._format_copy(copy["community"]["evidence"]["following"], following),
            self._format_copy(copy["community"]["evidence"]["ratio"], self._format_ratio(followers / max(following, 1))),
        ]
        if low_data:
            evidence.append(copy["community"]["evidence"]["low_data"])
        next_steps = []
        if followers < 25:
            next_steps.append(copy["community"]["actions"]["followers"])
        if followers / max(following, 1) < 1.0:
            next_steps.append(copy["community"]["actions"]["ratio"])
        next_steps.append(copy["community"]["actions"]["network"])
        return {
            "score": score,
            "summary_by_status": {
                "strong": copy["community"]["strong"],
                "steady": copy["community"]["steady"],
                "needs_attention": copy["community"]["needs_attention"],
            },
            "evidence": evidence,
            "next_steps": next_steps[:3],
            "low_data": low_data,
            "confidence": confidence,
        }

    def _calculate_community_score(self, followers: int, following: int) -> float:
        return float(self._calculate_community_details(followers, following, self.COPY["en"])["score"])

    def _calculate_tech_breadth_details(self, languages: Dict[str, int], copy: Dict[str, object]) -> Dict[str, object]:
        lang_count = len(languages)
        if lang_count == 0:
            return {
                "score": 0.0,
                "summary_by_status": {
                    "strong": copy["tech_breadth"]["empty"],
                    "steady": copy["tech_breadth"]["empty"],
                    "needs_attention": copy["tech_breadth"]["empty"],
                },
                "evidence": [],
                "next_steps": [
                    copy["tech_breadth"]["actions"]["count"],
                    copy["tech_breadth"]["actions"]["balance"],
                ],
                "low_data": True,
                "confidence": "low",
            }

        diversity_component = min(7.0, math.log1p(lang_count) * 3.6)
        total_bytes = sum(max(value, 0) for value in languages.values())
        dominant_share = (max(languages.values()) / total_bytes) if total_bytes > 0 else 1.0
        balance_component = min(6.0, max(0.0, (1.0 - dominant_share) * 8.0))

        score = self._round_score(min(13.0, diversity_component + balance_component))
        dominant_pct = round(dominant_share * 100)
        next_steps = []
        if lang_count < 3:
            next_steps.append(copy["tech_breadth"]["actions"]["count"])
        if dominant_share > 0.8:
            next_steps.append(copy["tech_breadth"]["actions"]["balance"])
        return {
            "score": score,
            "summary_by_status": {
                "strong": copy["tech_breadth"]["strong"],
                "steady": copy["tech_breadth"]["steady"],
                "needs_attention": copy["tech_breadth"]["needs_attention"],
            },
            "evidence": [
                self._format_copy(copy["tech_breadth"]["evidence"]["count"], lang_count),
                self._format_copy(copy["tech_breadth"]["evidence"]["dominant"], dominant_pct),
                copy["tech_breadth"]["evidence"]["balance"],
            ],
            "next_steps": next_steps or [copy["tech_breadth"]["actions"]["balance"]],
            "low_data": lang_count < 2,
            "confidence": "low" if lang_count < 2 else ("medium" if lang_count < 4 else "high"),
        }

    def _calculate_tech_breadth_score(self, languages: Dict[str, int]) -> float:
        return float(self._calculate_tech_breadth_details(languages, self.COPY["en"])["score"])

    def _calculate_documentation_details(self, repos: List[Repository], copy: Dict[str, object]) -> Dict[str, object]:
        if not repos:
            return {
                "score": 0.0,
                "summary_by_status": {
                    "strong": copy["documentation"]["empty"],
                    "steady": copy["documentation"]["empty"],
                    "needs_attention": copy["documentation"]["empty"],
                },
                "evidence": [],
                "next_steps": [
                    copy["documentation"]["actions"]["readme"],
                    copy["documentation"]["actions"]["description"],
                ],
                "low_data": True,
                "confidence": "low",
            }

        repo_count = len(repos)
        readme_ratio = sum(1 for repo in repos if repo.has_readme) / repo_count
        license_ratio = sum(1 for repo in repos if repo.has_license) / repo_count
        described_ratio = sum(1 for repo in repos if repo.description) / repo_count

        score = (readme_ratio * 4.8) + (license_ratio * 3.2) + (described_ratio * 2.0)
        rounded = self._round_score(min(10.0, score))
        next_steps = []
        if readme_ratio < 0.8:
            next_steps.append(copy["documentation"]["actions"]["readme"])
        if license_ratio < 0.65:
            next_steps.append(copy["documentation"]["actions"]["license"])
        if described_ratio < 0.9:
            next_steps.append(copy["documentation"]["actions"]["description"])
        return {
            "score": rounded,
            "summary_by_status": {
                "strong": copy["documentation"]["strong"],
                "steady": copy["documentation"]["steady"],
                "needs_attention": copy["documentation"]["needs_attention"],
            },
            "evidence": [
                self._format_copy(copy["documentation"]["evidence"]["readme"], round(readme_ratio * 100)),
                self._format_copy(copy["documentation"]["evidence"]["license"], round(license_ratio * 100)),
                self._format_copy(copy["documentation"]["evidence"]["description"], round(described_ratio * 100)),
            ],
            "next_steps": next_steps or [copy["documentation"]["actions"]["readme"]],
            "low_data": repo_count < 2,
            "confidence": "low" if repo_count < 2 else ("medium" if repo_count < 4 else "high"),
        }

    def _calculate_documentation_score(self, repos: List[Repository]) -> float:
        return float(self._calculate_documentation_details(repos, self.COPY["en"])["score"])
