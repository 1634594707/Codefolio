"""
Example demonstrating ScoreEngine usage with sample data.

This script shows how to calculate GitScore from GitHub user data.
"""

from models import UserData, Repository, Contributions
from services.score_engine import ScoreEngine


def main():
    """Demonstrate ScoreEngine with sample user data."""
    
    # Create sample repositories
    repos = [
        Repository(
            name="awesome-python-lib",
            description="A popular Python library",
            stars=1500,
            forks=200,
            language="Python",
            has_readme=True,
            has_license=True,
            url="https://github.com/user/awesome-python-lib"
        ),
        Repository(
            name="react-components",
            description="Reusable React components",
            stars=800,
            forks=120,
            language="JavaScript",
            has_readme=True,
            has_license=True,
            url="https://github.com/user/react-components"
        ),
        Repository(
            name="go-microservice",
            description="Microservice in Go",
            stars=300,
            forks=45,
            language="Go",
            has_readme=True,
            has_license=False,
            url="https://github.com/user/go-microservice"
        )
    ]
    
    # Create sample contributions
    contributions = Contributions(
        total_commits_last_year=1200,
        total_prs_last_year=45,
        longest_streak=60
    )
    
    # Create sample user data
    user_data = UserData(
        username="awesome_dev",
        name="Awesome Developer",
        avatar_url="https://github.com/awesome_dev.png",
        bio="Full-stack developer passionate about open source",
        followers=350,
        following=120,
        repositories=repos,
        contributions=contributions,
        languages={
            "Python": 50000,
            "JavaScript": 35000,
            "TypeScript": 25000,
            "Go": 15000,
            "Rust": 8000
        }
    )
    
    # Calculate GitScore
    engine = ScoreEngine()
    gitscore = engine.calculate_gitscore(user_data)
    
    # Display results
    print("=" * 60)
    print(f"GitScore for {user_data.name} (@{user_data.username})")
    print("=" * 60)
    print(f"\nTotal Score: {gitscore.total:.2f}/100")
    print("\nDimension Breakdown:")
    print(f"  🎯 Project Impact:      {gitscore.dimensions['impact']:.2f}/35")
    print(f"  💻 Code Contribution:   {gitscore.dimensions['contribution']:.2f}/25")
    print(f"  👥 Community Activity:  {gitscore.dimensions['community']:.2f}/20")
    print(f"  🔧 Tech Breadth:        {gitscore.dimensions['tech_breadth']:.2f}/15")
    print(f"  📚 Documentation:       {gitscore.dimensions['documentation']:.2f}/5")
    print("\nCalculation Details:")
    print(f"  Total Stars: {sum(r.stars for r in repos)}")
    print(f"  Total Forks: {sum(r.forks for r in repos)}")
    print(f"  Commits (last year): {contributions.total_commits_last_year}")
    print(f"  Pull Requests: {contributions.total_prs_last_year}")
    print(f"  Followers: {user_data.followers}")
    print(f"  Following: {user_data.following}")
    print(f"  Languages: {len(user_data.languages)}")
    print(f"  Repos with README: {sum(1 for r in repos if r.has_readme)}")
    print(f"  Repos with LICENSE: {sum(1 for r in repos if r.has_license)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
