"""
ScoreEngine: Multi-dimensional GitHub developer scoring algorithm.

Calculates GitScore (0-100) from five dimensions:
- Impact (0-35): public traction and shipped-repo signals
- Contribution (0-25): commits, PRs, and streak consistency
- Community (0-20): followers, maintained projects, and public interest
- Tech Breadth (0-15): language diversity and distribution balance
- Documentation (0-5): README / LICENSE / project metadata quality
"""

import math
from typing import Dict, List

from models import Contributions, GitScore, Repository, UserData


class ScoreEngine:
    """Calculate multi-dimensional GitScore from GitHub data."""

    @staticmethod
    def _round_score(value: float) -> float:
        return round(float(value), 1)

    def calculate_gitscore(self, user_data: UserData) -> GitScore:
        """
        Calculate 0-100 GitScore with dimension breakdown.

        Args:
            user_data: Normalized GitHub user data

        Returns:
            GitScore containing total score and dimension breakdown
        """
        impact = self._calculate_impact_score(user_data.repositories)
        contribution = self._calculate_contribution_score(user_data.contributions)
        community = self._calculate_community_score(user_data.followers, user_data.following)
        tech_breadth = self._calculate_tech_breadth_score(user_data.languages)
        documentation = self._calculate_documentation_score(user_data.repositories)

        total = self._round_score(min(100.0, impact + contribution + community + tech_breadth + documentation))

        dimensions = {
            "impact": self._round_score(impact),
            "contribution": self._round_score(contribution),
            "community": self._round_score(community),
            "tech_breadth": self._round_score(tech_breadth),
            "documentation": self._round_score(documentation),
        }

        return GitScore(total=total, dimensions=dimensions)

    def _calculate_impact_score(self, repos: List[Repository]) -> float:
        total_stars = sum(repo.stars for repo in repos)
        total_forks = sum(repo.forks for repo in repos)
        repo_strength = max((repo.stars + repo.forks * 2) for repo in repos) if repos else 0
        shipped_repos = sum(
            1
            for repo in repos
            if repo.description and (repo.has_readme or repo.has_license or repo.stars + repo.forks >= 3)
        )

        stars_component = min(18.0, math.log1p(total_stars) * 4.2)
        forks_component = min(7.0, math.log1p(total_forks) * 2.6)
        flagship_component = min(5.0, math.log1p(repo_strength) * 1.8)
        shipped_component = min(5.0, shipped_repos * 1.25)

        return self._round_score(stars_component + forks_component + flagship_component + shipped_component)

    def _calculate_contribution_score(self, contributions: Contributions) -> float:
        commits = contributions.total_commits_last_year
        prs = contributions.total_prs_last_year
        streak = contributions.longest_streak

        commits_component = min(12.0, math.log1p(commits) * 2.1)
        prs_component = min(8.0, math.log1p(prs) * 2.4)
        streak_component = min(5.0, streak / 12.0)

        return self._round_score(commits_component + prs_component + streak_component)

    def _calculate_community_score(self, followers: int, following: int) -> float:
        followers_component = min(12.0, math.log1p(followers) * 2.4)
        following_component = min(3.0, math.log1p(following) * 0.9)
        relationship_component = 0.0
        if followers > 0:
            ratio = followers / max(following, 1)
            relationship_component = min(5.0, math.log1p(ratio) * 2.2)

        return self._round_score(followers_component + following_component + relationship_component)

    def _calculate_tech_breadth_score(self, languages: Dict[str, int]) -> float:
        lang_count = len(languages)
        if lang_count == 0:
            return 0.0

        diversity_component = min(9.0, math.log1p(lang_count) * 4.6)
        total_bytes = sum(max(value, 0) for value in languages.values())
        dominant_share = (max(languages.values()) / total_bytes) if total_bytes > 0 else 1.0
        balance_component = min(6.0, max(0.0, (1.0 - dominant_share) * 8.0))

        return self._round_score(diversity_component + balance_component)

    def _calculate_documentation_score(self, repos: List[Repository]) -> float:
        if not repos:
            return 0.0

        repo_count = len(repos)
        readme_ratio = sum(1 for repo in repos if repo.has_readme) / repo_count
        license_ratio = sum(1 for repo in repos if repo.has_license) / repo_count
        described_ratio = sum(1 for repo in repos if repo.description) / repo_count

        score = (readme_ratio * 2.4) + (license_ratio * 1.6) + (described_ratio * 1.0)
        return self._round_score(min(5.0, score))
