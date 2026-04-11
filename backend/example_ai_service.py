"""
Example usage of AIService with sample data.

This demonstrates how to use the AIService to generate:
- Style tags
- Roast comments
- Tech summaries

Run with: python backend/example_ai_service.py
"""

import asyncio
from backend.services.ai_service import AIService
from backend.models import UserData, GitScore, Repository, Contributions


async def main():
    """Demonstrate AIService functionality."""
    
    # Create sample user data
    user_data = UserData(
        username="octocat",
        name="The Octocat",
        avatar_url="https://github.com/octocat.png",
        bio="GitHub's mascot and all-around cool cat",
        followers=5000,
        following=100,
        repositories=[
            Repository(
                name="Hello-World",
                description="My first repository on GitHub!",
                stars=1500,
                forks=300,
                language="Python",
                has_readme=True,
                has_license=True,
                url="https://github.com/octocat/Hello-World"
            ),
            Repository(
                name="Spoon-Knife",
                description="This repo is for demonstration purposes only.",
                stars=800,
                forks=200,
                language="JavaScript",
                has_readme=True,
                has_license=False,
                url="https://github.com/octocat/Spoon-Knife"
            )
        ],
        contributions=Contributions(
            total_commits_last_year=800,
            total_prs_last_year=120,
            longest_streak=45
        ),
        languages={
            "Python": 150000,
            "JavaScript": 120000,
            "TypeScript": 80000,
            "Go": 50000
        }
    )
    
    # Create sample GitScore
    gitscore = GitScore(
        total=82.5,
        dimensions={
            "impact": 30.0,
            "contribution": 22.0,
            "community": 18.0,
            "tech_breadth": 9.0,
            "documentation": 3.5
        }
    )
    
    # Initialize AI service
    ai_service = AIService()
    
    print("=" * 60)
    print("AIService Example - Generating AI Insights")
    print("=" * 60)
    print()
    
    try:
        # Generate style tags (English)
        print("Generating style tags (English)...")
        tags_en = await ai_service.generate_style_tags(user_data, gitscore, language="en")
        print(f"Style Tags (EN): {', '.join(tags_en)}")
        print()
        
        # Generate style tags (Chinese)
        print("Generating style tags (Chinese)...")
        tags_zh = await ai_service.generate_style_tags(user_data, gitscore, language="zh")
        print(f"Style Tags (ZH): {', '.join(tags_zh)}")
        print()
        
        # Generate roast comment (English)
        print("Generating roast comment (English)...")
        roast_en = await ai_service.generate_roast_comment(user_data, gitscore, language="en")
        print(f"Roast Comment (EN): {roast_en}")
        print()
        
        # Generate roast comment (Chinese)
        print("Generating roast comment (Chinese)...")
        roast_zh = await ai_service.generate_roast_comment(user_data, gitscore, language="zh")
        print(f"Roast Comment (ZH): {roast_zh}")
        print()
        
        # Generate tech summary (English)
        print("Generating tech summary (English)...")
        summary_en = await ai_service.generate_tech_summary(user_data, language="en")
        print(f"Tech Summary (EN): {summary_en}")
        print()
        
        # Generate tech summary (Chinese)
        print("Generating tech summary (Chinese)...")
        summary_zh = await ai_service.generate_tech_summary(user_data, language="zh")
        print(f"Tech Summary (ZH): {summary_zh}")
        print()
        
        print("=" * 60)
        print("All AI insights generated successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nNote: Make sure you have set AI_API_KEY in your .env file")
        print("The service will use fallback values if the API is not configured.")
    
    finally:
        # Clean up
        await ai_service.close()


if __name__ == "__main__":
    asyncio.run(main())
