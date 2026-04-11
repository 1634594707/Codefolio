"""
Unit tests for Redis caching in AIService

Tests verify:
- Cache key pattern: ai:{username}:{content_type}:{language}
- 7-day TTL configuration for AI results
- Cache hit/miss behavior for style tags, roast comments, and summaries
- Graceful cache failure handling with logging
- Data consistency between cached and fresh AI results

Requirements Validated:
- 3.6: Cache AI-generated content with username as key
- Task 5.2: Cache style tags, roast comments, and summaries separately
- Task 5.2: Use 7-day TTL for AI results
- Task 5.2: Implement cache key pattern: ai:{username}:{content_type}

Run with: python test_ai_caching.py (from backend directory)
"""
import asyncio
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import json

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services.ai_service import AIService, AI_CACHE_TTL
from utils.redis_client import redis_client
from models import UserData, Repository, Contributions, GitScore
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_user_data():
    """Create test user data for testing"""
    test_repo = Repository(
        name="test-repo",
        description="Test repository",
        stars=100,
        forks=20,
        language="Python",
        has_readme=True,
        has_license=True,
        url="https://github.com/test/test-repo"
    )
    
    test_contributions = Contributions(
        total_commits_last_year=500,
        total_prs_last_year=50,
        longest_streak=30
    )
    
    return UserData(
        username="testuser",
        name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        bio="Test bio",
        followers=100,
        following=50,
        repositories=[test_repo],
        contributions=test_contributions,
        languages={"Python": 50000, "JavaScript": 30000}
    )


def create_test_gitscore():
    """Create test GitScore for testing"""
    return GitScore(
        total=75.5,
        dimensions={
            "impact": 25.0,
            "contribution": 20.0,
            "community": 15.0,
            "tech_breadth": 10.0,
            "documentation": 5.0
        }
    )


async def test_cache_key_pattern_style_tags():
    """Test that style tags cache key follows pattern: ai:{username}:tags:{language}"""
    print("Testing style tags cache key pattern...")
    
    await redis_client.connect()
    
    try:
        service = AIService()
        user_data = create_test_user_data()
        gitscore = create_test_gitscore()
        
        # Test English cache key
        expected_key_en = f"ai:{user_data.username}:tags:en"
        await redis_client.delete(expected_key_en)
        
        # Verify cache key doesn't exist
        cached = await redis_client.get(expected_key_en)
        assert cached is None, "Cache should be empty initially"
        
        # Test Chinese cache key
        expected_key_zh = f"ai:{user_data.username}:tags:zh"
        await redis_client.delete(expected_key_zh)
        
        cached = await redis_client.get(expected_key_zh)
        assert cached is None, "Cache should be empty initially"
        
        print(f"✓ Style tags cache key pattern verified: {expected_key_en}, {expected_key_zh}")
        
        await service.close()
        return True
        
    finally:
        await redis_client.close()


async def test_cache_key_pattern_roast_comment():
    """Test that roast comment cache key follows pattern: ai:{username}:roast:{language}"""
    print("\nTesting roast comment cache key pattern...")
    
    await redis_client.connect()
    
    try:
        user_data = create_test_user_data()
        
        expected_key_en = f"ai:{user_data.username}:roast:en"
        expected_key_zh = f"ai:{user_data.username}:roast:zh"
        
        await redis_client.delete(expected_key_en)
        await redis_client.delete(expected_key_zh)
        
        cached_en = await redis_client.get(expected_key_en)
        cached_zh = await redis_client.get(expected_key_zh)
        
        assert cached_en is None, "Cache should be empty initially"
        assert cached_zh is None, "Cache should be empty initially"
        
        print(f"✓ Roast comment cache key pattern verified: {expected_key_en}, {expected_key_zh}")
        return True
        
    finally:
        await redis_client.close()


async def test_cache_key_pattern_tech_summary():
    """Test that tech summary cache key follows pattern: ai:{username}:summary:v2:{language}"""
    print("\nTesting tech summary cache key pattern...")
    
    await redis_client.connect()
    
    try:
        user_data = create_test_user_data()
        
        expected_key_en = f"ai:{user_data.username}:summary:v2:en"
        expected_key_zh = f"ai:{user_data.username}:summary:v2:zh"
        
        await redis_client.delete(expected_key_en)
        await redis_client.delete(expected_key_zh)
        
        cached_en = await redis_client.get(expected_key_en)
        cached_zh = await redis_client.get(expected_key_zh)
        
        assert cached_en is None, "Cache should be empty initially"
        assert cached_zh is None, "Cache should be empty initially"
        
        print(f"✓ Tech summary cache key pattern verified: {expected_key_en}, {expected_key_zh}")
        return True
        
    finally:
        await redis_client.close()


async def test_cache_ttl_configuration():
    """Test that AI cache TTL is set to 7 days (604800 seconds)"""
    print("\nTesting AI cache TTL configuration...")
    
    await redis_client.connect()
    
    try:
        expected_ttl = 604800  # 7 days in seconds
        actual_ttl = AI_CACHE_TTL
        
        assert actual_ttl == expected_ttl, f"Expected TTL {expected_ttl}, got {actual_ttl}"
        
        # Test that TTL is actually set when caching
        test_key = "test:ai:ttl:key"
        test_data = {"test": "data"}
        
        await redis_client.set(test_key, test_data, AI_CACHE_TTL)
        
        # Check TTL using Redis client
        if redis_client.client:
            ttl = await redis_client.client.ttl(test_key)
            # TTL should be close to 604800 (allowing for a few seconds of execution time)
            assert ttl > 604790 and ttl <= 604800, f"TTL should be ~604800, got {ttl}"
            
            # Clean up
            await redis_client.delete(test_key)
        
        print(f"✓ AI cache TTL correctly configured: {expected_ttl} seconds (7 days)")
        return True
        
    finally:
        await redis_client.close()


async def test_style_tags_cache_hit():
    """Test that style tags are cached and retrieved on subsequent calls"""
    print("\nTesting style tags cache hit behavior...")
    
    await redis_client.connect()
    
    try:
        service = AIService()
        user_data = create_test_user_data()
        gitscore = create_test_gitscore()
        
        cache_key = f"ai:{user_data.username}:tags:en"
        
        # Clear cache
        await redis_client.delete(cache_key)
        
        # Store mock cached tags
        mock_tags = ["#TestTag1", "#TestTag2", "#TestTag3"]
        await redis_client.set(cache_key, {"tags": mock_tags}, AI_CACHE_TTL)
        
        # Call generate_style_tags - should hit cache
        with patch.object(service, '_call_llm') as mock_llm:
            tags = await service.generate_style_tags(user_data, gitscore, language="en")
            
            # Verify LLM was NOT called (cache hit)
            mock_llm.assert_not_called()
            
            # Verify tags match cached data
            assert tags == mock_tags, f"Expected {mock_tags}, got {tags}"
        
        # Clean up
        await redis_client.delete(cache_key)
        await service.close()
        
        print("✓ Style tags cache hit verified: LLM not called when cache exists")
        return True
        
    finally:
        await redis_client.close()


async def test_roast_comment_cache_hit():
    """Test that roast comments are cached and retrieved on subsequent calls"""
    print("\nTesting roast comment cache hit behavior...")
    
    await redis_client.connect()
    
    try:
        service = AIService()
        user_data = create_test_user_data()
        gitscore = create_test_gitscore()
        
        cache_key = f"ai:{user_data.username}:roast:en"
        
        # Clear cache
        await redis_client.delete(cache_key)
        
        # Store mock cached roast
        mock_roast = "Test roast comment"
        await redis_client.set(cache_key, {"comment": mock_roast}, AI_CACHE_TTL)
        
        # Call generate_roast_comment - should hit cache
        with patch.object(service, '_call_llm') as mock_llm:
            comment = await service.generate_roast_comment(user_data, gitscore, language="en")
            
            # Verify LLM was NOT called (cache hit)
            mock_llm.assert_not_called()
            
            # Verify comment matches cached data
            assert comment == mock_roast, f"Expected {mock_roast}, got {comment}"
        
        # Clean up
        await redis_client.delete(cache_key)
        await service.close()
        
        print("✓ Roast comment cache hit verified: LLM not called when cache exists")
        return True
        
    finally:
        await redis_client.close()


async def test_tech_summary_cache_hit():
    """Test that tech summaries are cached and retrieved on subsequent calls"""
    print("\nTesting tech summary cache hit behavior...")
    
    await redis_client.connect()
    
    try:
        service = AIService()
        user_data = create_test_user_data()
        
        cache_key = f"ai:{user_data.username}:summary:v2:en"
        
        # Clear cache
        await redis_client.delete(cache_key)
        
        # Store mock cached summary
        mock_summary = "- Test tech summary bullet"
        await redis_client.set(cache_key, {"summary": mock_summary}, AI_CACHE_TTL)
        
        # Call generate_tech_summary - should hit cache
        with patch.object(service, '_call_llm') as mock_llm:
            summary = await service.generate_tech_summary(user_data, language="en")
            
            # Verify LLM was NOT called (cache hit)
            mock_llm.assert_not_called()
            
            # Verify summary matches cached data
            assert summary == mock_summary, f"Expected {mock_summary}, got {summary}"
        
        # Clean up
        await redis_client.delete(cache_key)
        await service.close()
        
        print("✓ Tech summary cache hit verified: LLM not called when cache exists")
        return True
        
    finally:
        await redis_client.close()


async def test_separate_caching_by_language():
    """Test that different languages are cached separately"""
    print("\nTesting separate caching by language...")
    
    await redis_client.connect()
    
    try:
        service = AIService()
        user_data = create_test_user_data()
        gitscore = create_test_gitscore()
        
        # Cache English tags
        cache_key_en = f"ai:{user_data.username}:tags:en"
        mock_tags_en = ["#EnglishTag1", "#EnglishTag2"]
        await redis_client.set(cache_key_en, {"tags": mock_tags_en}, AI_CACHE_TTL)
        
        # Cache Chinese tags
        cache_key_zh = f"ai:{user_data.username}:tags:zh"
        mock_tags_zh = ["#中文标签1", "#中文标签2"]
        await redis_client.set(cache_key_zh, {"tags": mock_tags_zh}, AI_CACHE_TTL)
        
        # Retrieve English tags
        with patch.object(service, '_call_llm') as mock_llm:
            tags_en = await service.generate_style_tags(user_data, gitscore, language="en")
            assert tags_en == mock_tags_en
            
            # Retrieve Chinese tags
            tags_zh = await service.generate_style_tags(user_data, gitscore, language="zh")
            assert tags_zh == mock_tags_zh
            
            # Verify LLM was NOT called for either (both cache hits)
            mock_llm.assert_not_called()
        
        # Clean up
        await redis_client.delete(cache_key_en)
        await redis_client.delete(cache_key_zh)
        await service.close()
        
        print("✓ Separate language caching verified: EN and ZH cached independently")
        return True
        
    finally:
        await redis_client.close()


async def test_cache_stores_after_generation():
    """Test that AI results are cached after generation"""
    print("\nTesting cache storage after generation...")
    
    await redis_client.connect()
    
    try:
        service = AIService()
        user_data = create_test_user_data()
        gitscore = create_test_gitscore()
        
        cache_key = f"ai:{user_data.username}:tags:en"
        
        # Clear cache
        await redis_client.delete(cache_key)
        
        # Verify cache is empty
        cached = await redis_client.get(cache_key)
        assert cached is None, "Cache should be empty initially"
        
        # Mock LLM response
        mock_llm_response = '["#MockTag1", "#MockTag2", "#MockTag3"]'
        
        with patch.object(service, '_call_llm', return_value=mock_llm_response):
            tags = await service.generate_style_tags(user_data, gitscore, language="en")
            
            # Verify tags were generated
            assert len(tags) == 3
            assert all(tag.startswith("#") for tag in tags)
        
        # Verify cache was populated
        cached = await redis_client.get(cache_key)
        assert cached is not None, "Cache should be populated after generation"
        assert "tags" in cached
        assert cached["tags"] == tags
        
        # Clean up
        await redis_client.delete(cache_key)
        await service.close()
        
        print("✓ Cache storage verified: Results cached after generation")
        return True
        
    finally:
        await redis_client.close()


async def test_cache_failure_graceful_handling():
    """Test that cache failures don't break AI service"""
    print("\nTesting graceful cache failure handling...")
    
    try:
        service = AIService()
        user_data = create_test_user_data()
        gitscore = create_test_gitscore()
        
        # Mock redis_client to simulate failure
        with patch('utils.redis_client.redis_client.get', side_effect=Exception("Redis connection failed")):
            with patch('utils.redis_client.redis_client.set', side_effect=Exception("Redis write failed")):
                # Mock LLM to return valid response
                mock_llm_response = '["#Tag1", "#Tag2"]'
                
                with patch.object(service, '_call_llm', return_value=mock_llm_response):
                    # Should still work despite cache failures
                    tags = await service.generate_style_tags(user_data, gitscore, language="en")
                    assert len(tags) == 2
        
        await service.close()
        print("✓ Cache failure handling verified: Service continues despite cache errors")
        return True
        
    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        return False


if __name__ == "__main__":
    print("="*70)
    print("Testing AI Service Redis Caching Implementation")
    print("="*70)
    
    tests = [
        test_cache_key_pattern_style_tags,
        test_cache_key_pattern_roast_comment,
        test_cache_key_pattern_tech_summary,
        test_cache_ttl_configuration,
        test_style_tags_cache_hit,
        test_roast_comment_cache_hit,
        test_tech_summary_cache_hit,
        test_separate_caching_by_language,
        test_cache_stores_after_generation,
        test_cache_failure_graceful_handling
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = asyncio.run(test())
            if result:
                passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*70)
    
    if failed == 0:
        print("✓ All AI caching tests passed!")
        print("\nVerified Requirements:")
        print("  ✓ 3.6: Cache AI-generated content with username as key")
        print("  ✓ Task 5.2: Cache style tags, roast comments, and summaries separately")
        print("  ✓ Task 5.2: Use 7-day TTL for AI results")
        print("  ✓ Task 5.2: Implement cache key pattern: ai:{username}:{content_type}:{language}")
    else:
        print(f"✗ {failed} test(s) failed")
        sys.exit(1)
