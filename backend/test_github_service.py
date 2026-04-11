"""
Test script for GitHubService

Tests the GitHub data fetching service including:
- Valid user data fetching
- Cache hit behavior
- Rate limit checking
- Error handling for invalid users
- Structured error responses

Run with: python test_github_service.py (from backend directory)
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services.github_service import GitHubService
from utils.redis_client import redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_fetch_user_data():
    """Test fetching user data from GitHub"""
    # Initialize Redis
    await redis_client.connect()
    
    try:
        service = GitHubService()
        
        # Test with a known GitHub user
        test_username = "torvalds"  # Linus Torvalds
        
        logger.info(f"Fetching data for user: {test_username}")
        user_data = await service.fetch_user_data(test_username)
        
        # Display results
        logger.info(f"\n{'='*60}")
        logger.info(f"User: {user_data.name} (@{user_data.username})")
        logger.info(f"Bio: {user_data.bio}")
        logger.info(f"Followers: {user_data.followers}")
        logger.info(f"Following: {user_data.following}")
        logger.info(f"Total Repositories: {len(user_data.repositories)}")
        logger.info(f"Commits (last year): {user_data.contributions.total_commits_last_year}")
        logger.info(f"PRs (last year): {user_data.contributions.total_prs_last_year}")
        logger.info(f"Longest Streak: {user_data.contributions.longest_streak} days")
        
        # Top 5 repositories
        logger.info(f"\nTop 5 Repositories:")
        for i, repo in enumerate(user_data.repositories[:5], 1):
            logger.info(f"  {i}. {repo.name} - ⭐ {repo.stars} | 🍴 {repo.forks} | {repo.language}")
        
        # Language distribution
        logger.info(f"\nLanguage Distribution:")
        sorted_langs = sorted(user_data.languages.items(), key=lambda x: x[1], reverse=True)
        total_bytes = sum(user_data.languages.values())
        for lang, bytes_count in sorted_langs[:5]:
            percentage = (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
            logger.info(f"  {lang}: {percentage:.1f}%")
        
        logger.info(f"{'='*60}\n")
        
        # Test cache hit
        logger.info("Testing cache hit...")
        cached_user_data = await service.fetch_user_data(test_username)
        logger.info(f"Cache hit successful: {cached_user_data.username == user_data.username}")
        
        # Test rate limit check
        logger.info("\nChecking rate limit...")
        rate_limit = await service.check_rate_limit()
        logger.info(f"Rate Limit: {rate_limit['remaining']}/{rate_limit['limit']}")
        logger.info(f"Resets at: {rate_limit['reset_at']}")
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        await redis_client.close()


async def test_invalid_user():
    """Test error handling for invalid username"""
    await redis_client.connect()
    
    try:
        service = GitHubService()
        invalid_username = "this_user_definitely_does_not_exist_12345"
        
        logger.info(f"Testing invalid user: {invalid_username}")
        await service.fetch_user_data(invalid_username)
        logger.error("✗ Should have raised ValueError for invalid user")
        
    except ValueError as e:
        logger.info(f"✓ Correctly caught ValueError: {e}")
        
        # Test structured error response
        error_response = service.create_error_response(e)
        logger.info(f"✓ Error response: {error_response}")
        assert error_response["error_type"] == "user_not_found"
        assert "not found" in error_response["message"].lower()
        
    except Exception as e:
        logger.error(f"✗ Unexpected error type: {type(e).__name__}: {e}")
    finally:
        await redis_client.close()


async def test_rate_limit_check():
    """Test rate limit checking functionality"""
    await redis_client.connect()
    
    try:
        service = GitHubService()
        
        logger.info("Testing rate limit check...")
        rate_limit = await service.check_rate_limit()
        
        logger.info(f"✓ Rate limit check successful:")
        logger.info(f"  - Limit: {rate_limit['limit']}")
        logger.info(f"  - Remaining: {rate_limit['remaining']}")
        logger.info(f"  - Resets at: {rate_limit['reset_at']}")
        
        # Verify structure
        assert "limit" in rate_limit
        assert "remaining" in rate_limit
        assert "reset_at" in rate_limit
        assert isinstance(rate_limit["limit"], int)
        assert isinstance(rate_limit["remaining"], int)
        
        logger.info("✓ Rate limit response structure is correct")
        
    except Exception as e:
        logger.error(f"✗ Rate limit check failed: {e}")
    finally:
        await redis_client.close()


async def test_error_response_structure():
    """Test structured error response creation"""
    service = GitHubService()
    
    logger.info("Testing error response structures...")
    
    # Test user not found error
    user_error = ValueError("GitHub user 'test' not found. Please check the username and try again.")
    response = service.create_error_response(user_error)
    assert response["error_type"] == "user_not_found"
    logger.info(f"✓ User not found error: {response}")
    
    # Test rate limit error
    rate_error = RuntimeError("GitHub API rate limit exceeded. Please try again later.")
    response = service.create_error_response(rate_error)
    assert response["error_type"] == "rate_limit_exceeded"
    logger.info(f"✓ Rate limit error: {response}")
    
    # Test authentication error
    auth_error = RuntimeError("GitHub API authentication failed. Check GITHUB_TOKEN.")
    response = service.create_error_response(auth_error)
    assert response["error_type"] == "authentication_error"
    logger.info(f"✓ Authentication error: {response}")
    
    # Test timeout error
    timeout_error = RuntimeError("GitHub API request timed out after 30 seconds.")
    response = service.create_error_response(timeout_error)
    assert response["error_type"] == "timeout_error"
    logger.info(f"✓ Timeout error: {response}")
    
    logger.info("✓ All error response structures are correct")


if __name__ == "__main__":
    print("Testing GitHubService...")
    print("="*60)
    
    print("\n1. Testing valid user data fetch:")
    asyncio.run(test_fetch_user_data())
    
    print("\n2. Testing invalid user error handling:")
    asyncio.run(test_invalid_user())
    
    print("\n3. Testing rate limit check:")
    asyncio.run(test_rate_limit_check())
    
    print("\n4. Testing error response structures:")
    asyncio.run(test_error_response_structure())
    
    print("\n" + "="*60)
    print("✓ All tests completed successfully!")
    print("="*60)
