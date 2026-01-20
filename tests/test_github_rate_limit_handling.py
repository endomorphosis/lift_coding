"""Tests for GitHub rate limit handling and retry logic."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from handsfree.github.auth import TokenProvider
from handsfree.github.provider import LiveGitHubProvider


class MockTokenProvider(TokenProvider):
    """Mock token provider for testing."""

    def __init__(self, token: str | None = "ghp_test1234567890"):
        self._token = token

    def get_token(self) -> str | None:
        return self._token


class TestGitHubRateLimitHandling:
    """Test GitHub rate limit detection and handling."""

    @pytest.fixture
    def provider(self):
        """Create a LiveGitHubProvider with a mock token."""
        token_provider = MockTokenProvider()
        return LiveGitHubProvider(token_provider)

    def test_rate_limit_with_403_and_remaining_zero(self, provider):
        """Test that 403 with X-RateLimit-Remaining=0 is detected as rate limit."""
        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.headers = {
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int((datetime.now() + timedelta(minutes=5)).timestamp()))
            }
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            with pytest.raises(RuntimeError, match="rate limit exceeded"):
                provider._make_request("/test/endpoint")

    def test_rate_limit_with_429(self, provider):
        """Test that 429 is detected as rate limit."""
        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {
                "X-RateLimit-Reset": str(int((datetime.now() + timedelta(minutes=10)).timestamp()))
            }
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            with pytest.raises(RuntimeError, match="rate limit exceeded"):
                provider._make_request("/test/endpoint")

    def test_rate_limit_human_readable_time(self, provider):
        """Test that rate limit error includes human-readable retry time."""
        # Set reset time 5 minutes in the future
        reset_time = datetime.now() + timedelta(minutes=5, seconds=30)
        
        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.headers = {
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(reset_time.timestamp()))
            }
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            with pytest.raises(RuntimeError) as exc_info:
                provider._make_request("/test/endpoint")
            
            error_msg = str(exc_info.value)
            # Should contain minutes and seconds
            assert "minute" in error_msg or "second" in error_msg

    def test_403_without_rate_limit_not_retried(self, provider):
        """Test that 403 without rate limit headers is treated as auth error."""
        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.headers = {}  # No rate limit headers
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            with pytest.raises(RuntimeError, match="access forbidden"):
                provider._make_request("/test/endpoint")

    def test_401_not_retried(self, provider):
        """Test that 401 authentication errors are not retried."""
        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.headers = {}
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            with pytest.raises(RuntimeError, match="authentication failed"):
                provider._make_request("/test/endpoint")
            
            # Should only be called once (no retries)
            assert mock_client.return_value.__enter__.return_value.get.call_count == 1


class TestTransientErrorRetry:
    """Test retry logic for transient server errors."""

    @pytest.fixture
    def provider(self):
        """Create a LiveGitHubProvider with a mock token."""
        token_provider = MockTokenProvider()
        return LiveGitHubProvider(token_provider)

    def test_503_retries_with_backoff(self, provider):
        """Test that 503 errors trigger retries with exponential backoff."""
        with patch("httpx.Client") as mock_client, \
             patch("time.sleep") as mock_sleep:
            
            mock_response_503 = MagicMock()
            mock_response_503.status_code = 503
            mock_response_503.headers = {}
            
            mock_response_success = MagicMock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"data": "test"}
            mock_response_success.headers = {}
            
            # First two attempts fail with 503, third succeeds
            mock_get = mock_client.return_value.__enter__.return_value.get
            mock_get.side_effect = [mock_response_503, mock_response_503, mock_response_success]

            result = provider._make_request("/test/endpoint")
            
            # Should have retried and succeeded
            assert result == {"data": "test"}
            assert mock_get.call_count == 3
            
            # Should have slept between retries
            assert mock_sleep.call_count == 2

    def test_502_retries(self, provider):
        """Test that 502 errors are retried."""
        with patch("httpx.Client") as mock_client, \
             patch("time.sleep") as mock_sleep:
            
            mock_response_502 = MagicMock()
            mock_response_502.status_code = 502
            mock_response_502.headers = {}
            
            mock_response_success = MagicMock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"data": "test"}
            mock_response_success.headers = {}
            
            mock_get = mock_client.return_value.__enter__.return_value.get
            mock_get.side_effect = [mock_response_502, mock_response_success]

            result = provider._make_request("/test/endpoint")
            
            assert result == {"data": "test"}
            assert mock_get.call_count == 2
            assert mock_sleep.call_count == 1

    def test_504_retries(self, provider):
        """Test that 504 errors are retried."""
        with patch("httpx.Client") as mock_client, \
             patch("time.sleep") as mock_sleep:
            
            mock_response_504 = MagicMock()
            mock_response_504.status_code = 504
            mock_response_504.headers = {}
            
            mock_response_success = MagicMock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"data": "test"}
            mock_response_success.headers = {}
            
            mock_get = mock_client.return_value.__enter__.return_value.get
            mock_get.side_effect = [mock_response_504, mock_response_success]

            result = provider._make_request("/test/endpoint")
            
            assert result == {"data": "test"}
            assert mock_get.call_count == 2

    def test_max_retries_exceeded(self, provider):
        """Test that retries are bounded and eventually fail."""
        with patch("httpx.Client") as mock_client, \
             patch("time.sleep"):
            
            mock_response = MagicMock()
            mock_response.status_code = 503
            mock_response.headers = {}
            mock_response.text = "Service Unavailable"
            
            mock_get = mock_client.return_value.__enter__.return_value.get
            mock_get.return_value = mock_response

            with pytest.raises(RuntimeError, match="request failed with status 503"):
                provider._make_request("/test/endpoint")
            
            # Should attempt exactly 3 times total: initial attempt + 2 retries (for max_retries=3, attempts 0, 1, 2)
            assert mock_get.call_count == 3

    def test_jitter_in_backoff(self, provider):
        """Test that retry delays include proportional jitter."""
        with patch("httpx.Client") as mock_client, \
             patch("time.sleep") as mock_sleep, \
             patch("random.uniform") as mock_random:
            
            # Mock uniform to return a fixed fraction of the range
            # First call: range is (0, 0.25), return 0.15
            # Second call: range is (0, 0.5), return 0.3
            mock_random.side_effect = [0.15, 0.3]
            
            mock_response_503 = MagicMock()
            mock_response_503.status_code = 503
            mock_response_503.headers = {}
            
            mock_response_success = MagicMock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"data": "test"}
            mock_response_success.headers = {}
            
            mock_get = mock_client.return_value.__enter__.return_value.get
            mock_get.side_effect = [mock_response_503, mock_response_503, mock_response_success]

            provider._make_request("/test/endpoint")
            
            # Check that sleep was called with expected delays
            # With proportional jitter: base_delay_no_jitter * (2^attempt) + uniform(0, base_delay_no_jitter * 0.5)
            # First retry (attempt=0): 0.5 * 2^0 + 0.15 = 0.5 + 0.15 = 0.65
            # Second retry (attempt=1): 0.5 * 2^1 + 0.3 = 1.0 + 0.3 = 1.3
            assert mock_sleep.call_count == 2
            delays = [call[0][0] for call in mock_sleep.call_args_list]
            assert abs(delays[0] - 0.65) < 0.01  # First retry delay
            assert abs(delays[1] - 1.3) < 0.01  # Second retry delay


class TestRateLimitLogging:
    """Test that rate limit errors don't leak tokens in logs."""

    @pytest.fixture
    def provider(self):
        """Create a LiveGitHubProvider with a mock token."""
        token_provider = MockTokenProvider("ghp_secret_token_12345")
        return LiveGitHubProvider(token_provider)

    def test_rate_limit_logging_no_token_leak(self, provider):
        """Test that rate limit errors don't log the token."""
        with patch("httpx.Client") as mock_client, \
             patch("handsfree.github.provider.logger") as mock_logger:
            
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.headers = {
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(datetime.now().timestamp()))
            }
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            with pytest.raises(RuntimeError):
                provider._make_request("/test/endpoint")
            
            # Check that logger.error was called
            assert mock_logger.error.called
            
            # Verify no token in any log message
            for call in mock_logger.error.call_args_list:
                args = call[0]
                for arg in args:
                    assert "ghp_secret_token_12345" not in str(arg)

    def test_transient_error_logging_no_token_leak(self, provider):
        """Test that transient error logs don't leak the token."""
        with patch("httpx.Client") as mock_client, \
             patch("handsfree.github.provider.logger") as mock_logger, \
             patch("time.sleep"):
            
            mock_response = MagicMock()
            mock_response.status_code = 503
            mock_response.headers = {}
            
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            with pytest.raises(RuntimeError):
                provider._make_request("/test/endpoint")
            
            # Check that logger.warning was called for retries
            assert mock_logger.warning.called
            
            # Verify no token in any log message
            for call in mock_logger.warning.call_args_list:
                args = call[0]
                for arg in args:
                    assert "ghp_secret_token_12345" not in str(arg)


class TestFallbackBehavior:
    """Test that rate limit errors trigger fixture fallback in the wrapper."""

    def test_list_user_prs_fallback_on_rate_limit(self):
        """Test that list_user_prs falls back to fixture on rate limit."""
        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)
        
        with patch.object(provider, "_make_request") as mock_request:
            mock_request.side_effect = RuntimeError("GitHub API rate limit exceeded")
            
            # Should fall back to fixture
            result = provider.list_user_prs("testuser")
            
            assert isinstance(result, list)
            assert len(result) == 3  # From fixture

    def test_get_pr_details_fallback_on_rate_limit(self):
        """Test that get_pr_details falls back to fixture on rate limit."""
        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)
        
        with patch.object(provider, "_make_request") as mock_request:
            mock_request.side_effect = RuntimeError("GitHub API rate limit exceeded")
            
            # Should fall back to fixture
            result = provider.get_pr_details("owner/repo", 123)
            
            assert result["pr_number"] == 123
            assert result["title"] == "Add new feature X"
