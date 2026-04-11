"""
Example usage of RenderService to generate a Markdown resume.

This script demonstrates how to use the RenderService to create
a professional resume from GitHub data.
"""

from services.render_service import RenderService
from models import UserData, Repository, Contributions, GitScore, AIInsights


def main():
    """Demonstrate RenderService with sample data."""
    
    # Create sample user data
    user_data = UserData(
        username="octocat",
        name="The Octocat",
        avatar_url="https://avatars.githubusercontent.com/u/583231",
        bio="GitHub's mascot and the world's most famous cat-octopus hybrid",
        followers=5000,
        following=10,
        repositories=[
            Repository(
                name="Hello-World",
                description="My first repository on GitHub!",
                stars=2500,
                forks=1200,
                language="JavaScript",
                has_readme=True,
                has_license=True,
                url="https://github.com/octocat/Hello-World"
            ),
            Repository(
                name="Spoon-Knife",
                description="This repo is for demonstration purposes only.",
                stars=12000,
                forks=140000,
                language="HTML",
                has_readme=True,
                has_license=False,
                url="https://github.com/octocat/Spoon-Knife"
            ),
            Repository(
                name="octocat.github.io",
                description="Personal website",
                stars=150,
                forks=50,
                language="CSS",
                has_readme=True,
                has_license=True,
                url="https://github.com/octocat/octocat.github.io"
            )
        ],
        contributions=Contributions(
            total_commits_last_year=850,
            total_prs_last_year=120,
            longest_streak=65,
            contribution_days=[],
        ),
        languages={
            "JavaScript": 45000,
            "HTML": 30000,
            "CSS": 15000,
            "Python": 8000,
            "TypeScript": 2000
        }
    )
    
    # Create sample GitScore
    gitscore = GitScore(
        total=88.5,
        dimensions={
            "impact": 35.0,
            "contribution": 23.5,
            "community": 18.0,
            "tech_breadth": 9.5,
            "documentation": 2.5
        }
    )
    
    # Create sample AI insights
    ai_insights = AIInsights(
        style_tags=["#开源传奇", "#全栈大师", "#社区领袖"],
        roast_comment="你的仓库比你的粉丝还多，真是个代码囤积狂。",
        tech_summary="Legendary open-source contributor and GitHub mascot, specializing in JavaScript and web technologies with massive community impact."
    )
    
    # Generate resume
    render_service = RenderService()
    resume = render_service.generate_markdown_resume(
        user_data,
        gitscore,
        ai_insights
    )
    
    # Print the generated resume
    print("=" * 80)
    print("GENERATED MARKDOWN RESUME")
    print("=" * 80)
    print(resume)
    print("=" * 80)


if __name__ == "__main__":
    main()
