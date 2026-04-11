"""
Unit tests for RenderService.

Tests the Markdown resume generation functionality including:
- Complete resume structure
- GitScore breakdown formatting
- Language distribution calculation
- Top repositories sorting
- AI insights inclusion
- Contribution stats display
"""

import pytest
from services.render_service import RenderService
from models import UserData, Repository, Contributions, GitScore, AIInsights


@pytest.fixture
def sample_user_data():
    """Create sample user data for testing."""
    return UserData(
        username="testuser",
        name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        bio="Full-stack developer passionate about open source",
        followers=150,
        following=75,
        repositories=[
            Repository(
                name="awesome-project",
                description="An awesome open source project",
                stars=500,
                forks=50,
                language="Python",
                has_readme=True,
                has_license=True,
                url="https://github.com/testuser/awesome-project"
            ),
            Repository(
                name="cool-library",
                description="A cool utility library",
                stars=200,
                forks=20,
                language="JavaScript",
                has_readme=True,
                has_license=False,
                url="https://github.com/testuser/cool-library"
            ),
            Repository(
                name="small-tool",
                description="A small CLI tool",
                stars=10,
                forks=2,
                language="Go",
                has_readme=True,
                has_license=True,
                url="https://github.com/testuser/small-tool"
            )
        ],
        contributions=Contributions(
            total_commits_last_year=450,
            total_prs_last_year=35,
            longest_streak=42,
            contribution_days=[],
        ),
        languages={
            "Python": 50000,
            "JavaScript": 30000,
            "Go": 15000,
            "TypeScript": 5000
        }
    )


@pytest.fixture
def sample_gitscore():
    """Create sample GitScore for testing."""
    return GitScore(
        total=75.5,
        dimensions={
            "impact": 28.5,
            "contribution": 20.0,
            "community": 15.5,
            "tech_breadth": 9.0,
            "documentation": 2.5
        }
    )


@pytest.fixture
def sample_ai_insights():
    """Create sample AI insights for testing."""
    return AIInsights(
        style_tags=["#全栈夜猫子", "#提交狂魔", "#开源强迫症"],
        roast_comment="看来你的周末都献给了React，不愧是组件抽象艺术家。",
        tech_summary="Full-stack developer specializing in Python and JavaScript, with strong focus on open-source contributions."
    )


@pytest.fixture
def render_service():
    """Create RenderService instance."""
    return RenderService()


def test_generate_markdown_resume_structure(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that generated resume has all required sections."""
    resume = render_service.generate_markdown_resume(
        sample_user_data,
        sample_gitscore,
        sample_ai_insights
    )
    
    assert "# Test User" in resume
    assert "## Contact" in resume
    assert "## Professional highlights" in resume
    assert "## Technical Skills" in resume
    assert "## Selected projects" in resume
    assert "## Public activity" in resume
    assert "## Profile metrics (reference)" in resume
    assert "### Score Breakdown" in resume
    assert "## Keywords" in resume


def test_generate_markdown_resume_includes_bio(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that bio is included when present."""
    resume = render_service.generate_markdown_resume(
        sample_user_data,
        sample_gitscore,
        sample_ai_insights
    )
    
    assert "Full-stack developer passionate about open source" in resume


def test_generate_markdown_resume_includes_technical_skills(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that technical skills section is included with proficiency levels."""
    resume = render_service.generate_markdown_resume(
        sample_user_data,
        sample_gitscore,
        sample_ai_insights
    )
    
    # Check Technical Skills section exists
    assert "## Technical Skills" in resume
    
    # Check proficiency levels are present
    assert "**Expert:**" in resume
    assert "**Proficient:**" in resume
    
    # Check skills are listed
    assert "Python" in resume
    assert "JavaScript" in resume


def test_generate_markdown_resume_gitscore_breakdown(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that GitScore breakdown is correctly formatted."""
    resume = render_service.generate_markdown_resume(
        sample_user_data,
        sample_gitscore,
        sample_ai_insights
    )
    
    assert "**Project Impact:** 28.5 / 35" in resume
    assert "**Code Contribution:** 20.0 / 25" in resume
    assert "**Community Activity:** 15.5 / 20" in resume
    assert "**Tech Breadth:** 9.0 / 15" in resume
    assert "**Documentation:** 2.5 / 5" in resume


def test_generate_markdown_resume_language_distribution(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that language distribution is calculated correctly."""
    resume = render_service.generate_markdown_resume(
        sample_user_data,
        sample_gitscore,
        sample_ai_insights
    )
    
    # Total bytes: 100000
    # Python: 50000 / 100000 = 50%
    # JavaScript: 30000 / 100000 = 30%
    # Go: 15000 / 100000 = 15%
    # TypeScript: 5000 / 100000 = 5%
    assert "**Python:** 50.0%" in resume
    assert "**JavaScript:** 30.0%" in resume
    assert "**Go:** 15.0%" in resume
    assert "**TypeScript:** 5.0%" in resume


def test_generate_markdown_resume_top_projects_sorted(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that top projects are sorted by stars."""
    resume = render_service.generate_markdown_resume(
        sample_user_data,
        sample_gitscore,
        sample_ai_insights
    )
    
    # Check projects are in correct order (by stars)
    assert resume.index("awesome-project") < resume.index("cool-library")
    assert resume.index("cool-library") < resume.index("small-tool")
    
    # Check star counts are displayed
    assert "⭐ 500" in resume
    assert "⭐ 200" in resume
    assert "⭐ 10" in resume


def test_generate_markdown_resume_includes_forks(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that fork counts are included when > 0."""
    resume = render_service.generate_markdown_resume(
        sample_user_data,
        sample_gitscore,
        sample_ai_insights
    )
    
    assert "🔀 50" in resume
    assert "🔀 20" in resume
    assert "🔀 2" in resume


def test_generate_markdown_resume_ai_insights(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that AI insights are included correctly."""
    resume = render_service.generate_markdown_resume(
        sample_user_data,
        sample_gitscore,
        sample_ai_insights
    )
    
    assert "#全栈夜猫子" in resume
    assert "#提交狂魔" in resume
    assert "#开源强迫症" in resume
    assert "- Full-stack developer specializing in Python and JavaScript" in resume


def test_generate_markdown_resume_contribution_stats(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that contribution stats are displayed correctly."""
    resume = render_service.generate_markdown_resume(
        sample_user_data,
        sample_gitscore,
        sample_ai_insights
    )
    
    assert "**Total Commits (Last Year):** 450" in resume
    assert "**Total Pull Requests:** 35" in resume
    assert "**Followers:** 150" in resume
    assert "**Following:** 75" in resume
    assert "**Longest Streak:** 42 days" in resume


def test_generate_markdown_resume_empty_bio(render_service, sample_gitscore, sample_ai_insights):
    """Test resume generation with empty bio."""
    user_data = UserData(
        username="testuser",
        name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        bio="",
        followers=10,
        following=5,
        repositories=[],
        contributions=Contributions(
            total_commits_last_year=0,
            total_prs_last_year=0,
            longest_streak=0,
            contribution_days=[],
        ),
        languages={}
    )
    
    resume = render_service.generate_markdown_resume(
        user_data,
        sample_gitscore,
        sample_ai_insights
    )
    
    assert "# Test User" in resume
    lines = resume.split('\n')
    assert lines[0] == "# Test User"


def test_generate_markdown_resume_empty_repositories(render_service, sample_gitscore, sample_ai_insights):
    """Test resume generation with no repositories."""
    user_data = UserData(
        username="testuser",
        name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        bio="Developer",
        followers=10,
        following=5,
        repositories=[],
        contributions=Contributions(
            total_commits_last_year=50,
            total_prs_last_year=5,
            longest_streak=10,
            contribution_days=[],
        ),
        languages={"Python": 1000}
    )
    
    resume = render_service.generate_markdown_resume(
        user_data,
        sample_gitscore,
        sample_ai_insights
    )
    
    assert "## Selected projects" in resume


def test_generate_markdown_resume_empty_languages(render_service, sample_gitscore, sample_ai_insights):
    """Test resume generation with no languages."""
    user_data = UserData(
        username="testuser",
        name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        bio="Developer",
        followers=10,
        following=5,
        repositories=[
            Repository(
                name="test-repo",
                description="Test",
                stars=5,
                forks=0,
                language="",
                has_readme=True,
                has_license=False,
                url="https://github.com/testuser/test-repo"
            )
        ],
        contributions=Contributions(
            total_commits_last_year=50,
            total_prs_last_year=5,
            longest_streak=10,
            contribution_days=[],
        ),
        languages={}
    )
    
    resume = render_service.generate_markdown_resume(
        user_data,
        sample_gitscore,
        sample_ai_insights
    )
    
    assert "## Technical Skills" in resume


def test_generate_markdown_resume_missing_ai_insights(render_service, sample_user_data, sample_gitscore):
    """Test resume generation with missing AI insights."""
    ai_insights = AIInsights(
        style_tags=[],
        roast_comment="",
        tech_summary=""
    )
    
    resume = render_service.generate_markdown_resume(
        sample_user_data,
        sample_gitscore,
        ai_insights
    )
    
    assert "## Professional highlights" not in resume
    assert "## Keywords" not in resume


def test_generate_markdown_resume_zero_longest_streak(render_service, sample_gitscore, sample_ai_insights):
    """Test that longest streak is not shown when zero."""
    user_data = UserData(
        username="testuser",
        name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        bio="Developer",
        followers=10,
        following=5,
        repositories=[],
        contributions=Contributions(
            total_commits_last_year=50,
            total_prs_last_year=5,
            longest_streak=0,
            contribution_days=[],
        ),
        languages={}
    )
    
    resume = render_service.generate_markdown_resume(
        user_data,
        sample_gitscore,
        sample_ai_insights
    )
    
    assert "Longest Streak" not in resume


def test_generate_markdown_resume_limits_top_languages(render_service, sample_gitscore, sample_ai_insights):
    """Test that only top 10 languages are shown."""
    user_data = UserData(
        username="testuser",
        name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        bio="Polyglot developer",
        followers=10,
        following=5,
        repositories=[],
        contributions=Contributions(
            total_commits_last_year=50,
            total_prs_last_year=5,
            longest_streak=10,
            contribution_days=[],
        ),
        languages={
            f"Lang{i}": 1000 - (i * 50) for i in range(15)
        }
    )
    
    resume = render_service.generate_markdown_resume(
        user_data,
        sample_gitscore,
        sample_ai_insights
    )
    
    lang_section_start = resume.find("**Language Distribution**")
    lang_section_end = resume.find("## ", lang_section_start + 1)
    lang_section = resume[lang_section_start:lang_section_end]
    language_count = lang_section.count("- **Lang")
    assert language_count <= 5


def test_generate_markdown_resume_limits_top_repositories(render_service, sample_gitscore, sample_ai_insights):
    """Test that only top 5 repositories are shown."""
    repos = [
        Repository(
            name=f"repo-{i}",
            description=f"Repository {i}",
            stars=100 - i,
            forks=10 - i,
            language="Python",
            has_readme=True,
            has_license=True,
            url=f"https://github.com/testuser/repo-{i}"
        )
        for i in range(10)
    ]
    
    user_data = UserData(
        username="testuser",
        name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        bio="Developer",
        followers=10,
        following=5,
        repositories=repos,
        contributions=Contributions(
            total_commits_last_year=50,
            total_prs_last_year=5,
            longest_streak=10,
            contribution_days=[],
        ),
        languages={"Python": 1000}
    )
    
    resume = render_service.generate_markdown_resume(
        user_data,
        sample_gitscore,
        sample_ai_insights
    )
    
    # Should show top 5 repos
    assert "repo-0" in resume
    assert "repo-1" in resume
    assert "repo-2" in resume
    assert "repo-3" in resume
    assert "repo-4" in resume
    # Should not show repo-5 and beyond
    assert "repo-5" not in resume



def test_generate_social_card_html_dark_theme(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that social card HTML is generated with dark theme colors."""
    card_data = render_service.build_card_data(sample_user_data, sample_gitscore, sample_ai_insights)
    
    html = render_service.generate_social_card_html(
        card_data,
        tech_summary=sample_ai_insights.tech_summary,
        theme="dark",
        language="en"
    )
    
    # Check dark theme colors are present
    assert "#17181c" in html  # background
    assert "#232428" in html  # panel
    assert "#f2ede3" in html  # text
    assert "#b8afa1" in html  # muted
    assert "#d2ab67" in html  # accent
    
    # Check HTML structure
    assert "<!DOCTYPE html>" in html
    assert "1200px" in html  # width
    assert "630px" in html  # height
    assert card_data.username in html
    assert str(int(card_data.gitscore)) in html


def test_generate_social_card_html_light_theme(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that social card HTML is generated with light theme colors."""
    card_data = render_service.build_card_data(sample_user_data, sample_gitscore, sample_ai_insights)
    
    html = render_service.generate_social_card_html(
        card_data,
        tech_summary=sample_ai_insights.tech_summary,
        theme="light",
        language="en"
    )
    
    # Check light theme colors are present
    assert "#efe8dc" in html  # background
    assert "#fbf7f0" in html  # panel
    assert "#2a2621" in html  # text
    assert "#6d6458" in html  # muted
    assert "#8b6b3f" in html  # accent
    
    # Check HTML structure
    assert "<!DOCTYPE html>" in html
    assert "1200px" in html  # width
    assert "630px" in html  # height
    assert card_data.username in html


def test_generate_social_card_html_includes_avatar(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that social card includes avatar URL."""
    card_data = render_service.build_card_data(sample_user_data, sample_gitscore, sample_ai_insights)
    
    html = render_service.generate_social_card_html(
        card_data,
        tech_summary=sample_ai_insights.tech_summary,
        theme="dark",
        language="en"
    )
    
    assert card_data.avatar_url in html


def test_generate_social_card_html_includes_gitscore(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that social card includes GitScore."""
    card_data = render_service.build_card_data(sample_user_data, sample_gitscore, sample_ai_insights)
    
    html = render_service.generate_social_card_html(
        card_data,
        tech_summary=sample_ai_insights.tech_summary,
        theme="dark",
        language="en"
    )
    
    # Check GitScore is displayed
    assert "GitScore" in html
    assert str(int(card_data.gitscore)) in html


def test_generate_social_card_html_includes_style_tags(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that social card includes style tags."""
    card_data = render_service.build_card_data(sample_user_data, sample_gitscore, sample_ai_insights)
    
    html = render_service.generate_social_card_html(
        card_data,
        tech_summary=sample_ai_insights.tech_summary,
        theme="dark",
        language="en"
    )
    
    # Check style tags are included
    for tag in card_data.style_tags[:4]:
        assert tag in html


def test_generate_social_card_html_includes_roast_comment(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that social card includes roast comment."""
    card_data = render_service.build_card_data(sample_user_data, sample_gitscore, sample_ai_insights)
    
    html = render_service.generate_social_card_html(
        card_data,
        tech_summary=sample_ai_insights.tech_summary,
        theme="dark",
        language="en"
    )
    
    # Check roast comment is included
    assert card_data.roast_comment in html


def test_generate_social_card_html_includes_tech_icons(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that social card includes tech stack icons."""
    card_data = render_service.build_card_data(sample_user_data, sample_gitscore, sample_ai_insights)
    
    html = render_service.generate_social_card_html(
        card_data,
        tech_summary=sample_ai_insights.tech_summary,
        theme="dark",
        language="en"
    )
    
    # Check tech icons are included
    for icon in card_data.tech_icons[:4]:
        assert icon in html


def test_generate_social_card_html_includes_metrics(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that social card includes metric cells."""
    card_data = render_service.build_card_data(sample_user_data, sample_gitscore, sample_ai_insights)
    
    html = render_service.generate_social_card_html(
        card_data,
        tech_summary=sample_ai_insights.tech_summary,
        theme="dark",
        language="en"
    )
    
    # Check metric labels are present
    assert "Impact" in html
    assert "Code" in html
    assert "Community" in html
    assert "Breadth" in html
    assert "Docs" in html


def test_generate_social_card_html_chinese_language(render_service, sample_user_data, sample_gitscore, sample_ai_insights):
    """Test that social card HTML is generated with Chinese language."""
    card_data = render_service.build_card_data(sample_user_data, sample_gitscore, sample_ai_insights)
    
    html = render_service.generate_social_card_html(
        card_data,
        tech_summary=sample_ai_insights.tech_summary,
        theme="dark",
        language="zh"
    )
    
    # Check Chinese language is set
    assert 'lang="zh-CN"' in html
    # Check Chinese labels are present
    assert "影响" in html or "代码" in html or "社区" in html
