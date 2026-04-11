"""
Unit tests for GitHubService error handling and structured error responses

These tests verify that error handling works correctly without requiring
external dependencies like Redis or GitHub API access.

Run with: python test_error_handling.py (from backend directory)
"""
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services.github_service import GitHubService


def test_error_response_user_not_found():
    """Test structured error response for user not found"""
    print("Testing user not found error response...")
    
    service = GitHubService()
    error = ValueError("GitHub user 'test' not found. Please check the username and try again.")
    response = service.create_error_response(error)
    
    assert response["error_type"] == "user_not_found", f"Expected 'user_not_found', got {response['error_type']}"
    assert "not found" in response["message"].lower(), "Message should contain 'not found'"
    assert "details" in response, "Response should have details field"
    
    print(f"✓ User not found error response: {response}")
    return True


def test_error_response_rate_limit():
    """Test structured error response for rate limit exceeded"""
    print("\nTesting rate limit error response...")
    
    service = GitHubService()
    error = RuntimeError("GitHub API rate limit exceeded. Please try again later.")
    response = service.create_error_response(error)
    
    assert response["error_type"] == "rate_limit_exceeded", f"Expected 'rate_limit_exceeded', got {response['error_type']}"
    assert "rate limit" in response["message"].lower(), "Message should contain 'rate limit'"
    assert "details" in response, "Response should have details field"
    
    print(f"✓ Rate limit error response: {response}")
    return True


def test_error_response_authentication():
    """Test structured error response for authentication failure"""
    print("\nTesting authentication error response...")
    
    service = GitHubService()
    error = RuntimeError("GitHub API authentication failed. Check GITHUB_TOKEN.")
    response = service.create_error_response(error)
    
    assert response["error_type"] == "authentication_error", f"Expected 'authentication_error', got {response['error_type']}"
    assert "authentication" in response["message"].lower(), "Message should contain 'authentication'"
    assert "details" in response, "Response should have details field"
    
    print(f"✓ Authentication error response: {response}")
    return True


def test_error_response_timeout():
    """Test structured error response for timeout"""
    print("\nTesting timeout error response...")
    
    service = GitHubService()
    error = RuntimeError("GitHub API request timed out after 30 seconds.")
    response = service.create_error_response(error)
    
    assert response["error_type"] == "timeout_error", f"Expected 'timeout_error', got {response['error_type']}"
    assert "timed out" in response["message"].lower(), "Message should contain 'timed out'"
    assert "details" in response, "Response should have details field"
    
    print(f"✓ Timeout error response: {response}")
    return True


def test_error_response_invalid_input():
    """Test structured error response for invalid input"""
    print("\nTesting invalid input error response...")
    
    service = GitHubService()
    error = ValueError("Invalid username format")
    response = service.create_error_response(error)
    
    assert response["error_type"] == "invalid_input", f"Expected 'invalid_input', got {response['error_type']}"
    assert "details" in response, "Response should have details field"
    
    print(f"✓ Invalid input error response: {response}")
    return True


def test_error_response_generic_api_error():
    """Test structured error response for generic API error"""
    print("\nTesting generic API error response...")
    
    service = GitHubService()
    error = RuntimeError("Something went wrong with the API")
    response = service.create_error_response(error)
    
    assert response["error_type"] == "api_error", f"Expected 'api_error', got {response['error_type']}"
    assert "details" in response, "Response should have details field"
    
    print(f"✓ Generic API error response: {response}")
    return True


def test_error_response_unknown_error():
    """Test structured error response for unknown error type"""
    print("\nTesting unknown error response...")
    
    service = GitHubService()
    error = Exception("Some unexpected error")
    response = service.create_error_response(error)
    
    assert response["error_type"] == "unknown_error", f"Expected 'unknown_error', got {response['error_type']}"
    assert "details" in response, "Response should have details field"
    
    print(f"✓ Unknown error response: {response}")
    return True


def test_all_error_responses_have_required_fields():
    """Test that all error responses have required fields"""
    print("\nTesting all error responses have required fields...")
    
    service = GitHubService()
    test_errors = [
        ValueError("User not found"),
        RuntimeError("Rate limit exceeded"),
        RuntimeError("Authentication failed"),
        RuntimeError("Request timed out"),
        Exception("Unknown error")
    ]
    
    required_fields = ["error_type", "message", "details"]
    
    for error in test_errors:
        response = service.create_error_response(error)
        for field in required_fields:
            assert field in response, f"Response missing required field: {field}"
        assert isinstance(response["error_type"], str), "error_type should be string"
        assert isinstance(response["message"], str), "message should be string"
        assert isinstance(response["details"], str), "details should be string"
    
    print(f"✓ All error responses have required fields: {required_fields}")
    return True


if __name__ == "__main__":
    print("="*60)
    print("Testing GitHubService Error Handling")
    print("="*60)
    
    tests = [
        test_error_response_user_not_found,
        test_error_response_rate_limit,
        test_error_response_authentication,
        test_error_response_timeout,
        test_error_response_invalid_input,
        test_error_response_generic_api_error,
        test_error_response_unknown_error,
        test_all_error_responses_have_required_fields
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {failed} test(s) failed")
        sys.exit(1)
