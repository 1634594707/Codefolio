"""
Unit tests for AIService.

Tests cover:
- Style tag generation
- Roast comment generation
- Tech summary generation
- Fallback behavior on failures
- Timeout handling
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from config import settings
from backend.services.ai_service import AIService
from backend.models import UserData, GitScore, Repository, Contributions


@pytest.fixture
def sample_user_data():
    """Create sample user data for testing."""
    return UserData(
        username="testuser",
        name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        bio="Full-stack developer",
        followers=100,
        following=50,
        repositories=[
            Repository(
                name="awesome-project",
                description="An awesome project",
                stars=500,
                forks=50,
                language="Python",
                has_readme=True,
                has_license=True,
                url="https://github.com/testuser/awesome-project"
            ),
            Repository(
                name="react-app",
                description="A React application",
                stars=200,
                forks=20,
                language="JavaScript",
                has_readme=True,
                has_license=False,
                url="https://github.com/testuser/react-app"
            )
        ],
        contributions=Contributions(
            total_commits_last_year=500,
            total_prs_last_year=50,
            longest_streak=30
        ),
        languages={
            "Python": 100000,
            "JavaScript": 80000,
            "TypeScript": 50000
        }
    )


@pytest.fixture
def sample_gitscore():
    """Create sample GitScore for testing."""
    return GitScore(
        total=75.5,
        dimensions={
            "impact": 28.0,
            "contribution": 20.0,
            "community": 15.0,
            "tech_breadth": 9.0,
            "documentation": 3.5
        }
    )


@pytest.mark.asyncio
async def test_generate_style_tags_success(sample_user_data, sample_gitscore):
    """Test successful style tag generation."""
    ai_service = AIService()
    
    # Mock the LLM response
    mock_response = '["#FullStack", "#PythonPro", "#OpenSource"]'
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        
        tags = await ai_service.generate_style_tags(
            sample_user_data,
            sample_gitscore,
            language="en"
        )
        
        assert len(tags) == 3
        assert all(tag.startswith("#") for tag in tags)
        assert "#FullStack" in tags
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_generate_style_tags_chinese(sample_user_data, sample_gitscore):
    """Test style tag generation in Chinese."""
    ai_service = AIService()
    
    mock_response = '["#全栈开发", "#Python大师", "#开源贡献者"]'
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        
        tags = await ai_service.generate_style_tags(
            sample_user_data,
            sample_gitscore,
            language="zh"
        )
        
        assert len(tags) == 3
        assert all(tag.startswith("#") for tag in tags)
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_generate_style_tags_adds_hash_prefix(sample_user_data, sample_gitscore):
    """Test that tags without # prefix get it added."""
    ai_service = AIService()
    
    # Mock response without # prefix
    mock_response = '["FullStack", "PythonPro", "OpenSource"]'
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        
        tags = await ai_service.generate_style_tags(
            sample_user_data,
            sample_gitscore,
            language="en"
        )
        
        assert all(tag.startswith("#") for tag in tags)
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_generate_style_tags_fallback_on_error(sample_user_data, sample_gitscore):
    """Test fallback behavior when LLM call fails."""
    ai_service = AIService()
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = httpx.TimeoutException("Timeout")
        
        tags = await ai_service.generate_style_tags(
            sample_user_data,
            sample_gitscore,
            language="en"
        )
        
        # Should return fallback tags
        assert len(tags) == 3
        assert all(tag.startswith("#") for tag in tags)
        assert "#CodeEnthusiast" in tags
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_generate_style_tags_fallback_chinese(sample_user_data, sample_gitscore):
    """Test fallback behavior in Chinese."""
    ai_service = AIService()
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = Exception("API Error")
        
        tags = await ai_service.generate_style_tags(
            sample_user_data,
            sample_gitscore,
            language="zh"
        )
        
        # Should return Chinese fallback tags
        assert len(tags) == 3
        assert "#代码爱好者" in tags
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_generate_roast_comment_success(sample_user_data, sample_gitscore):
    """Test successful roast comment generation."""
    ai_service = AIService()
    
    mock_response = "Looks like Python is your weekend companion!"
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        
        comment = await ai_service.generate_roast_comment(
            sample_user_data,
            sample_gitscore,
            language="en"
        )
        
        assert isinstance(comment, str)
        assert len(comment) > 0
        assert len(comment) <= 60  # English limit
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_generate_roast_comment_chinese(sample_user_data, sample_gitscore):
    """Test roast comment generation in Chinese."""
    ai_service = AIService()
    
    mock_response = "看来你的周末都献给了Python"
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        
        comment = await ai_service.generate_roast_comment(
            sample_user_data,
            sample_gitscore,
            language="zh"
        )
        
        assert isinstance(comment, str)
        assert len(comment) > 0
        assert len(comment) <= 30  # Chinese limit
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_generate_roast_comment_truncates_long_text(sample_user_data, sample_gitscore):
    """Test that long roast comments are truncated."""
    ai_service = AIService()
    
    # Very long response
    mock_response = "This is a very long roast comment that exceeds the maximum character limit and should be truncated properly"
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        
        comment = await ai_service.generate_roast_comment(
            sample_user_data,
            sample_gitscore,
            language="en"
        )
        
        assert len(comment) <= 60
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_generate_roast_comment_returns_empty_on_error(sample_user_data, sample_gitscore):
    """Test that roast comment returns empty string on failure."""
    ai_service = AIService()
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = httpx.TimeoutException("Timeout")
        
        comment = await ai_service.generate_roast_comment(
            sample_user_data,
            sample_gitscore,
            language="en"
        )
        
        # Should return empty string on failure
        assert comment == ""
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_generate_tech_summary_success(sample_user_data):
    """Test successful tech summary generation."""
    ai_service = AIService()
    
    mock_response = "Full-stack developer specializing in Python and JavaScript."
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        
        summary = await ai_service.generate_tech_summary(
            sample_user_data,
            language="en"
        )
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "Python" in summary or "JavaScript" in summary
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_generate_tech_summary_chinese(sample_user_data):
    """Test tech summary generation in Chinese."""
    ai_service = AIService()
    
    mock_response = "全栈开发者，专注于Python和JavaScript开发。"
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        
        summary = await ai_service.generate_tech_summary(
            sample_user_data,
            language="zh"
        )
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_generate_tech_summary_fallback_on_error(sample_user_data):
    """Test fallback behavior when tech summary generation fails."""
    ai_service = AIService()
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = Exception("API Error")
        
        summary = await ai_service.generate_tech_summary(
            sample_user_data,
            language="en"
        )
        
        # Should return fallback summary
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "Python" in summary  # Should mention top language
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_generate_tech_summary_fallback_chinese(sample_user_data):
    """Test fallback behavior in Chinese."""
    ai_service = AIService()
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = httpx.HTTPError("HTTP Error")
        
        summary = await ai_service.generate_tech_summary(
            sample_user_data,
            language="zh"
        )
        
        # Should return Chinese fallback summary
        assert isinstance(summary, str)
        assert len(summary) > 0
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_call_llm_timeout_handling():
    """Test that LLM calls respect timeout settings."""
    ai_service = AIService()
    
    with patch.object(ai_service.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Request timed out")
        
        with pytest.raises(httpx.TimeoutException):
            await ai_service._call_llm("Test prompt")
    
    await ai_service.close()


@pytest.mark.asyncio
async def test_call_llm_http_error_handling():
    """Test that LLM calls handle HTTP errors properly."""
    ai_service = AIService()
    
    with patch.object(ai_service.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=MagicMock()
        )
        mock_post.return_value = mock_response
        
        with pytest.raises(httpx.HTTPError):
            await ai_service._call_llm("Test prompt")
    
    await ai_service.close()


@pytest.mark.asyncio
async def test_style_tags_handles_markdown_code_blocks(sample_user_data, sample_gitscore):
    """Test that style tags can parse JSON from markdown code blocks."""
    ai_service = AIService()
    
    # Mock response with markdown code block
    mock_response = '```json\n["#FullStack", "#PythonPro"]\n```'
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        
        tags = await ai_service.generate_style_tags(
            sample_user_data,
            sample_gitscore,
            language="en"
        )
        
        assert len(tags) == 2
        assert "#FullStack" in tags
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_style_tags_limits_to_five_tags(sample_user_data, sample_gitscore):
    """Test that style tags are limited to maximum 5 tags."""
    ai_service = AIService()
    
    # Mock response with more than 5 tags
    mock_response = '["#Tag1", "#Tag2", "#Tag3", "#Tag4", "#Tag5", "#Tag6", "#Tag7"]'
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        
        tags = await ai_service.generate_style_tags(
            sample_user_data,
            sample_gitscore,
            language="en"
        )
        
        assert len(tags) <= 5
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_roast_comment_strips_quotes(sample_user_data, sample_gitscore):
    """Test that roast comments strip surrounding quotes."""
    ai_service = AIService()
    
    mock_response = '"This is a roast comment"'
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        
        comment = await ai_service.generate_roast_comment(
            sample_user_data,
            sample_gitscore,
            language="en"
        )
        
        assert not comment.startswith('"')
        assert not comment.endswith('"')
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_timeout_is_15_seconds():
    """Test that AI service timeout is set to 15 seconds as per requirements."""
    ai_service = AIService()
    
    assert ai_service.timeout == settings.AI_REQUEST_TIMEOUT
    
    await ai_service.close()


@pytest.mark.asyncio
async def test_style_tags_timeout_returns_fallback(sample_user_data, sample_gitscore):
    """Test that style tags return fallback on timeout (15 seconds)."""
    ai_service = AIService()
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = httpx.TimeoutException("Request timed out after 15 seconds")
        
        tags = await ai_service.generate_style_tags(
            sample_user_data,
            sample_gitscore,
            language="en"
        )
        
        # Should return fallback tags
        assert len(tags) == 3
        assert "#CodeEnthusiast" in tags
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_roast_comment_timeout_returns_empty(sample_user_data, sample_gitscore):
    """Test that roast comment returns empty string on timeout (15 seconds)."""
    ai_service = AIService()
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = httpx.TimeoutException("Request timed out after 15 seconds")
        
        comment = await ai_service.generate_roast_comment(
            sample_user_data,
            sample_gitscore,
            language="en"
        )
        
        # Should return empty string on timeout
        assert comment == ""
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_tech_summary_timeout_returns_fallback(sample_user_data):
    """Test that tech summary returns fallback on timeout (15 seconds)."""
    ai_service = AIService()
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = httpx.TimeoutException("Request timed out after 15 seconds")
        
        summary = await ai_service.generate_tech_summary(
            sample_user_data,
            language="en"
        )
        
        # Should return fallback summary
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "Python" in summary  # Should mention top language
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_http_error_returns_fallback_tags(sample_user_data, sample_gitscore):
    """Test that HTTP errors return fallback tags."""
    ai_service = AIService()
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = httpx.HTTPError("Service unavailable")
        
        tags = await ai_service.generate_style_tags(
            sample_user_data,
            sample_gitscore,
            language="en"
        )
        
        # Should return fallback tags
        assert len(tags) == 3
        assert "#CodeEnthusiast" in tags
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_http_error_skips_roast_comment(sample_user_data, sample_gitscore):
    """Test that HTTP errors skip roast comment."""
    ai_service = AIService()
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = httpx.HTTPError("Service unavailable")
        
        comment = await ai_service.generate_roast_comment(
            sample_user_data,
            sample_gitscore,
            language="en"
        )
        
        # Should return empty string
        assert comment == ""
        
    await ai_service.close()


@pytest.mark.asyncio
async def test_json_decode_error_returns_fallback(sample_user_data, sample_gitscore):
    """Test that JSON decode errors return fallback tags."""
    ai_service = AIService()
    
    with patch.object(ai_service, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "This is not valid JSON"
        
        tags = await ai_service.generate_style_tags(
            sample_user_data,
            sample_gitscore,
            language="en"
        )
        
        # Should return fallback tags
        assert len(tags) == 3
        assert "#CodeEnthusiast" in tags
        
    await ai_service.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
