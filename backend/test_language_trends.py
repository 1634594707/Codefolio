"""Tests for compute_language_trends."""
from models import ContributionDay, Contributions, Repository, UserData
from services.language_trends import compute_language_trends


def _minimal_user(repos):
    return UserData(
        username="u",
        name="U",
        avatar_url="",
        bio="",
        followers=0,
        following=0,
        repositories=repos,
        contributions=Contributions(
            total_commits_last_year=0,
            total_prs_last_year=0,
            longest_streak=0,
            contribution_days=[ContributionDay(date="2025-01-01", contribution_count=0)],
        ),
        languages={},
    )


def test_language_trends_empty_repos():
    assert compute_language_trends(_minimal_user([])) == []


def test_language_trends_single_repo():
    r = Repository(
        name="a",
        description="",
        stars=1,
        forks=0,
        language="Python",
        has_readme=True,
        has_license=False,
        url="http://x",
        pushed_at="2020-01-15",
        languages={"Python": 100, "Shell": 10},
    )
    out = compute_language_trends(_minimal_user([r]), locale="en")
    assert len(out) >= 1
    assert out[0]["language"] == "Python"
    assert len(out[0]["data"]) == 12
    for row in out[0]["data"]:
        assert "month" in row and "percentage" in row
