"""
Unit tests for ScoreEngine class.

Tests the multi-dimensional scoring algorithm for GitScore calculation.
"""

import pytest
from models import UserData, Repository, Contributions, GitScore
from services.score_engine import ScoreEngine


@pytest.fixture
def score_engine():
    """Create a ScoreEngine instance for testing."""
    return ScoreEngine()


@pytest.fixture
def sample_user_data():
    """Create sample user data for testing."""
    repos = [
        Repository(
            name="awesome-project",
            description="An awesome project",
            stars=100,
            forks=20,
            language="Python",
            has_readme=True,
            has_license=True,
            url="https://github.com/user/awesome-project"
        ),
        Repository(
            name="another-project",
            description="Another project",
            stars=50,
            forks=10,
            language="JavaScript",
            has_readme=True,
            has_license=False,
            url="https://github.com/user/another-project"
        )
    ]
    
    contributions = Contributions(
        total_commits_last_year=500,
        total_prs_last_year=20,
        longest_streak=30
    )
    
    return UserData(
        username="testuser",
        name="Test User",
        avatar_url="https://github.com/testuser.png",
        bio="A test user",
        followers=100,
        following=50,
        repositories=repos,
        contributions=contributions,
        languages={"Python": 10000, "JavaScript": 5000, "TypeScript": 3000}
    )


class TestScoreEngine:
    """Test suite for ScoreEngine."""
    
    def test_calculate_gitscore_returns_valid_score(self, score_engine, sample_user_data):
        """Test that calculate_gitscore returns a valid GitScore object."""
        result = score_engine.calculate_gitscore(sample_user_data)
        
        assert isinstance(result, GitScore)
        assert 0 <= result.total <= 100
        assert "impact" in result.dimensions
        assert "contribution" in result.dimensions
        assert "community" in result.dimensions
        assert "tech_breadth" in result.dimensions
        assert "documentation" in result.dimensions
    
    def test_calculate_impact_score(self, score_engine):
        """Test impact score calculation from stars and forks."""
        repos = [
            Repository("repo1", "desc", 100, 20, "Python", True, True, "url1"),
            Repository("repo2", "desc", 50, 10, "JS", True, False, "url2")
        ]
        
        # Formula: (150 * 0.3 + 30 * 0.5) / 15 = (45 + 15) / 15 = 4.0
        score = score_engine._calculate_impact_score(repos)
        assert score == 4.0
    
    def test_calculate_impact_score_caps_at_35(self, score_engine):
        """Test that impact score is capped at 35."""
        repos = [
            Repository("mega-repo", "desc", 100000, 50000, "Python", True, True, "url")
        ]
        
        score = score_engine._calculate_impact_score(repos)
        assert score == 35.0
    
    def test_calculate_contribution_score(self, score_engine):
        """Test contribution score calculation from commits and PRs."""
        contributions = Contributions(
            total_commits_last_year=500,
            total_prs_last_year=20,
            longest_streak=30
        )
        
        # Formula: 500 * 0.01 + 20 * 0.5 = 5 + 10 = 15.0
        score = score_engine._calculate_contribution_score(contributions)
        assert score == 15.0
    
    def test_calculate_contribution_score_caps_at_25(self, score_engine):
        """Test that contribution score is capped at 25."""
        contributions = Contributions(
            total_commits_last_year=10000,
            total_prs_last_year=1000,
            longest_streak=365
        )
        
        score = score_engine._calculate_contribution_score(contributions)
        assert score == 25.0
    
    def test_calculate_community_score(self, score_engine):
        """Test community score calculation from followers and following."""
        # Formula: 100 * 0.05 + 50 * 0.02 = 5 + 1 = 6.0
        score = score_engine._calculate_community_score(100, 50)
        assert score == 6.0
    
    def test_calculate_community_score_caps_at_20(self, score_engine):
        """Test that community score is capped at 20."""
        score = score_engine._calculate_community_score(10000, 5000)
        assert score == 20.0
    
    def test_calculate_tech_breadth_score(self, score_engine):
        """Test tech breadth score calculation from language diversity."""
        languages = {"Python", "JavaScript", "TypeScript", "Go", "Rust"}
        
        # Formula: 5 * 1.5 = 7.5
        score = score_engine._calculate_tech_breadth_score(languages)
        assert score == 7.5
    
    def test_calculate_tech_breadth_score_caps_at_15(self, score_engine):
        """Test that tech breadth score is capped at 15."""
        languages = {f"lang{i}" for i in range(20)}
        
        score = score_engine._calculate_tech_breadth_score(languages)
        assert score == 15.0
    
    def test_calculate_documentation_score_both_present(self, score_engine):
        """Test documentation score when both README and LICENSE are present."""
        repos = [
            Repository("repo1", "desc", 10, 5, "Python", True, True, "url")
        ]
        
        # 2 (README) + 3 (LICENSE) = 5
        score = score_engine._calculate_documentation_score(repos)
        assert score == 5.0
    
    def test_calculate_documentation_score_only_readme(self, score_engine):
        """Test documentation score when only README is present."""
        repos = [
            Repository("repo1", "desc", 10, 5, "Python", True, False, "url")
        ]
        
        score = score_engine._calculate_documentation_score(repos)
        assert score == 2.0
    
    def test_calculate_documentation_score_only_license(self, score_engine):
        """Test documentation score when only LICENSE is present."""
        repos = [
            Repository("repo1", "desc", 10, 5, "Python", False, True, "url")
        ]
        
        score = score_engine._calculate_documentation_score(repos)
        assert score == 3.0
    
    def test_calculate_documentation_score_none_present(self, score_engine):
        """Test documentation score when neither README nor LICENSE is present."""
        repos = [
            Repository("repo1", "desc", 10, 5, "Python", False, False, "url")
        ]
        
        score = score_engine._calculate_documentation_score(repos)
        assert score == 0.0
    
    def test_empty_repositories(self, score_engine):
        """Test scoring with empty repository list."""
        user_data = UserData(
            username="emptyuser",
            name="Empty User",
            avatar_url="url",
            bio="bio",
            followers=10,
            following=5,
            repositories=[],
            contributions=Contributions(0, 0, 0),
            languages={}
        )
        
        result = score_engine.calculate_gitscore(user_data)
        
        # Should have minimal scores
        assert result.dimensions["impact"] == 0.0
        assert result.dimensions["contribution"] == 0.0
        assert result.dimensions["documentation"] == 0.0
        assert result.dimensions["tech_breadth"] == 0.0
        assert result.dimensions["community"] > 0  # Has some followers
    
    def test_zero_contributions(self, score_engine):
        """Test scoring with zero contributions."""
        contributions = Contributions(
            total_commits_last_year=0,
            total_prs_last_year=0,
            longest_streak=0
        )
        
        score = score_engine._calculate_contribution_score(contributions)
        assert score == 0.0
    
    def test_single_language_developer(self, score_engine):
        """Test tech breadth score for single language developer."""
        languages = {"Python"}
        
        # Formula: 1 * 1.5 = 1.5
        score = score_engine._calculate_tech_breadth_score(languages)
        assert score == 1.5
    
    def test_total_score_is_sum_of_dimensions(self, score_engine, sample_user_data):
        """Test that total score equals sum of all dimension scores."""
        result = score_engine.calculate_gitscore(sample_user_data)
        
        dimension_sum = sum(result.dimensions.values())
        assert result.total == dimension_sum
    
    def test_all_dimensions_within_bounds(self, score_engine, sample_user_data):
        """Test that all dimension scores are within their specified bounds."""
        result = score_engine.calculate_gitscore(sample_user_data)
        
        assert 0 <= result.dimensions["impact"] <= 35
        assert 0 <= result.dimensions["contribution"] <= 25
        assert 0 <= result.dimensions["community"] <= 20
        assert 0 <= result.dimensions["tech_breadth"] <= 15
        assert 0 <= result.dimensions["documentation"] <= 5
    
    def test_total_score_capped_at_100(self, score_engine):
        """Test that total score is explicitly capped at 100."""
        # Create user with maximum possible values in all dimensions
        repos = [
            Repository(f"repo{i}", "desc", 100000, 50000, f"Lang{i}", True, True, f"url{i}")
            for i in range(20)
        ]
        
        contributions = Contributions(
            total_commits_last_year=10000,
            total_prs_last_year=1000,
            longest_streak=365
        )
        
        user_data = UserData(
            username="maxuser",
            name="Max User",
            avatar_url="url",
            bio="bio",
            followers=10000,
            following=5000,
            repositories=repos,
            contributions=contributions,
            languages={f"Lang{i}": 10000 for i in range(20)}
        )
        
        result = score_engine.calculate_gitscore(user_data)
        
        # Total should be capped at 100
        assert result.total == 100.0
        assert result.total <= 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
