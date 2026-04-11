"""
ScoreEngine: Multi-dimensional GitHub developer scoring algorithm.

Calculates GitScore (0-100) from five dimensions:
- Impact (0-35): Project stars and forks
- Contribution (0-25): Commits and PRs in last year
- Community (0-20): Followers and following
- Tech Breadth (0-15): Programming language diversity
- Documentation (0-5): README and LICENSE presence
"""

from typing import List, Set
from models import UserData, Repository, Contributions, GitScore


class ScoreEngine:
    """Calculate multi-dimensional GitScore from GitHub data."""
    
    def calculate_gitscore(self, user_data: UserData) -> GitScore:
        """
        Calculate 0-100 GitScore with dimension breakdown.
        
        Args:
            user_data: Normalized GitHub user data
            
        Returns:
            GitScore containing total score and dimension breakdown
        """
        # Calculate individual dimension scores
        impact = self._calculate_impact_score(user_data.repositories)
        contribution = self._calculate_contribution_score(user_data.contributions)
        community = self._calculate_community_score(user_data.followers, user_data.following)
        tech_breadth = self._calculate_tech_breadth_score(set(user_data.languages.keys()))
        documentation = self._calculate_documentation_score(user_data.repositories)
        
        # Calculate total score (capped at 100 to ensure bounds)
        total = min(100.0, impact + contribution + community + tech_breadth + documentation)
        
        # Build dimension breakdown
        dimensions = {
            "impact": impact,
            "contribution": contribution,
            "community": community,
            "tech_breadth": tech_breadth,
            "documentation": documentation
        }
        
        return GitScore(total=total, dimensions=dimensions)
    
    def _calculate_impact_score(self, repos: List[Repository]) -> float:
        """
        Calculate project impact from stars and forks.
        
        Formula: (total_stars * 0.3 + total_forks * 0.5) / 15
        Maximum: 35.0 points
        
        Args:
            repos: List of user repositories
            
        Returns:
            Impact score (0-35)
        """
        total_stars = sum(repo.stars for repo in repos)
        total_forks = sum(repo.forks for repo in repos)
        
        raw_score = (total_stars * 0.3 + total_forks * 0.5) / 15
        return min(35.0, raw_score)
    
    def _calculate_contribution_score(self, contributions: Contributions) -> float:
        """
        Calculate code contribution from commits and PRs.
        
        Formula: commits * 0.01 + prs * 0.5
        Maximum: 25.0 points
        
        Args:
            contributions: User contribution statistics
            
        Returns:
            Contribution score (0-25)
        """
        commits = contributions.total_commits_last_year
        prs = contributions.total_prs_last_year
        
        raw_score = commits * 0.01 + prs * 0.5
        return min(25.0, raw_score)
    
    def _calculate_community_score(self, followers: int, following: int) -> float:
        """
        Calculate community activity score.
        
        Formula: followers * 0.05 + following * 0.02
        Maximum: 20.0 points
        
        Args:
            followers: Number of followers
            following: Number of users being followed
            
        Returns:
            Community score (0-20)
        """
        raw_score = followers * 0.05 + following * 0.02
        return min(20.0, raw_score)
    
    def _calculate_tech_breadth_score(self, languages: Set[str]) -> float:
        """
        Calculate tech breadth from language diversity.
        
        Formula: language_count * 1.5
        Maximum: 15.0 points
        
        Args:
            languages: Set of unique programming languages used
            
        Returns:
            Tech breadth score (0-15)
        """
        lang_count = len(languages)
        return min(15.0, lang_count * 1.5)
    
    def _calculate_documentation_score(self, repos: List[Repository]) -> float:
        """
        Calculate documentation quality score.
        
        Formula: 
        - 2 points if any repo has README
        - 3 points if any repo has LICENSE
        Maximum: 5.0 points
        
        Args:
            repos: List of user repositories
            
        Returns:
            Documentation score (0-5)
        """
        has_readme = any(repo.has_readme for repo in repos)
        has_license = any(repo.has_license for repo in repos)
        
        score = 0.0
        if has_readme:
            score += 2.0
        if has_license:
            score += 3.0
        
        return score
