import importlib

_hypothesis = importlib.import_module("hypothesis")
given = _hypothesis.given
settings = _hypothesis.settings
st = importlib.import_module("hypothesis.strategies")

from models import ContributionDay, Contributions, Repository, UserData
from services.score_engine import ScoreEngine


DIMENSION_MAXIMA = {
    "impact": 33.0,
    "contribution": 24.0,
    "community": 20.0,
    "tech_breadth": 13.0,
    "documentation": 10.0,
}


@st.composite
def repository_strategy(draw) -> Repository:
    return Repository(
        name=draw(st.text(min_size=1, max_size=30)),
        description=draw(st.text(max_size=120)),
        stars=draw(st.integers(min_value=0, max_value=1_000_000)),
        forks=draw(st.integers(min_value=0, max_value=250_000)),
        language=draw(st.text(max_size=20)),
        has_readme=draw(st.booleans()),
        has_license=draw(st.booleans()),
        url=draw(st.from_regex(r"https://github\.com/[A-Za-z0-9-]{1,20}/[A-Za-z0-9_.-]{1,30}", fullmatch=True)),
        pushed_at="",
        topics=draw(st.lists(st.text(min_size=1, max_size=12), max_size=5)),
        readme_text=draw(st.text(max_size=200)),
        file_tree=draw(st.lists(st.text(min_size=1, max_size=40), max_size=10)),
        languages=draw(st.dictionaries(st.text(min_size=1, max_size=16), st.integers(min_value=0, max_value=500_000), max_size=6)),
    )


@st.composite
def contributions_strategy(draw) -> Contributions:
    contribution_days = [
        ContributionDay(date=f"2025-01-{index + 1:02d}", contribution_count=count)
        for index, count in enumerate(draw(st.lists(st.integers(min_value=0, max_value=50), max_size=14)))
    ]
    return Contributions(
        total_commits_last_year=draw(st.integers(min_value=0, max_value=100_000)),
        total_prs_last_year=draw(st.integers(min_value=0, max_value=20_000)),
        longest_streak=draw(st.integers(min_value=0, max_value=366)),
        contribution_days=contribution_days,
        issues_opened_last_year=draw(st.integers(min_value=0, max_value=20_000)),
    )


@st.composite
def user_data_strategy(draw) -> UserData:
    username = draw(st.from_regex(r"[A-Za-z0-9-]{1,20}", fullmatch=True))
    return UserData(
        username=username,
        name=draw(st.text(max_size=40)),
        avatar_url=f"https://avatars.example.com/{username}.png",
        bio=draw(st.text(max_size=160)),
        followers=draw(st.integers(min_value=0, max_value=1_000_000)),
        following=draw(st.integers(min_value=0, max_value=100_000)),
        repositories=draw(st.lists(repository_strategy(), max_size=20)),
        contributions=draw(contributions_strategy()),
        languages=draw(st.dictionaries(st.text(min_size=1, max_size=16), st.integers(min_value=0, max_value=2_000_000), max_size=8)),
    )


@settings(max_examples=200)
@given(user_data=user_data_strategy())
def test_gitscore_total_stays_within_bounds(user_data: UserData) -> None:
    score = ScoreEngine().calculate_gitscore(user_data)
    assert 0.0 <= score.total <= 100.0


@settings(max_examples=200)
@given(user_data=user_data_strategy())
def test_gitscore_dimension_scores_stay_within_bounds(user_data: UserData) -> None:
    score = ScoreEngine().calculate_gitscore(user_data)
    for dimension, maximum in DIMENSION_MAXIMA.items():
        assert 0.0 <= score.dimensions.get(dimension, 0.0) <= maximum


@settings(max_examples=200)
@given(
    repo_count=st.integers(min_value=1, max_value=50),
    lower_total=st.integers(min_value=0, max_value=10_000),
    extra_total=st.integers(min_value=1, max_value=10_000),
)
def test_quality_density_is_monotonic_for_higher_traction(repo_count: int, lower_total: int, extra_total: int) -> None:
    engine = ScoreEngine()
    lower_repos = [
        Repository(
            name=f"repo-{index}",
            description="",
            stars=lower_total if index == 0 else 0,
            forks=0,
            language="Python",
            has_readme=False,
            has_license=False,
            url=f"https://github.com/acme/repo-{index}",
        )
        for index in range(repo_count)
    ]
    higher_repos = [
        Repository(
            name=f"repo-{index}",
            description="",
            stars=lower_total + extra_total if index == 0 else 0,
            forks=0,
            language="Python",
            has_readme=False,
            has_license=False,
            url=f"https://github.com/acme/repo-{index}",
        )
        for index in range(repo_count)
    ]

    assert engine._calculate_quality_density(higher_repos) > engine._calculate_quality_density(lower_repos)
