"""Tests for GitHub rate limit handling and retry logic."""

import time
from datetime import datetime, timedelta

import httpx
import pytest
import respx

from handsfree.github.auth import TokenProvider
from handsfree.github.provider import LiveGitHubProvider


class MockTokenProvider(TokenProvider):
    """Mock token provider for testing."""

    def __init__(self, token: str | None = "test_token"):
        self._token = token

    def get_token(self) -> str | None:
        return self._token


class MockResponse:
    """Mock response for testing rate limit messages."""

    def __init__(self, status_code: int, headers: dict | None = None):
        self.status_code = status_code
        self.headers = headers or {}


class TestRateLimitDetection:
    """Test rate limit detection logic."""

    @respx.mock
    def test_rate_limit_with_429(self):
        """Test that 429 response is detected as rate limit."""
        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        # Mock a 429 response with rate limit headers
        reset_time = int((datetime.now() + timedelta(minutes=5)).timestamp())
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(
                429,
                headers={
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                },
            )
        )

        # Should raise RuntimeError about rate limit
        with pytest.raises(RuntimeError, match="rate limit exceeded"):
            provider._make_request("/user")

    @respx.mock
    def test_rate_limit_with_403_and_remaining_zero(self):
        """Test that 403 with X-RateLimit-Remaining=0 is detected as rate limit."""
        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        # Mock a 403 response with remaining=0 (GitHub's typical rate limit response)
        reset_time = int((datetime.now() + timedelta(hours=1)).timestamp())
        respx.get("https://api.github.com/repos/owner/repo/pulls/1").mock(
            return_value=httpx.Response(
                403,
                headers={
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                },
            )
        )

        # Should raise RuntimeError about rate limit
        with pytest.raises(RuntimeError, match="rate limit exceeded"):
            provider._make_request("/repos/owner/repo/pulls/1")

    @respx.mock
    def test_403_without_rate_limit_not_retried(self):
        """Test that 403 without rate limit headers is treated as permission error."""
        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        # Mock a 403 response without rate limit (permission denied)
        respx.get("https://api.github.com/repos/private/repo/pulls/1").mock(
            return_value=httpx.Response(
                403,
                headers={
                    "X-RateLimit-Remaining": "100",  # Still have quota
                },
            )
        )

        # Should raise RuntimeError about forbidden access, not rate limit
        with pytest.raises(RuntimeError, match="access forbidden"):
            provider._make_request("/repos/private/repo/pulls/1")

    @respx.mock
    def test_401_not_retried(self):
        """Test that 401 authentication errors are not retried."""
        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        # Mock a 401 response
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(401)
        )

        # Should raise RuntimeError about authentication
        with pytest.raises(RuntimeError, match="authentication failed"):
            provider._make_request("/user")


class TestRetryTimeMessage:
    """Test human-readable retry time message generation."""

    def test_retry_time_message_seconds(self):
        """Test retry message for times less than a minute."""
        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        # Mock response with reset in 30 seconds
        reset_time = int((datetime.now() + timedelta(seconds=30)).timestamp())
        response = MockResponse(429, {"X-RateLimit-Reset": str(reset_time)})

        msg = provider._get_retry_time_message(response)
        assert "second" in msg.lower()

    def test_retry_time_message_minutes(self):
        """Test retry message for times in minutes."""
        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        # Mock response with reset in 5 minutes
        reset_time = int((datetime.now() + timedelta(minutes=5)).timestamp())
        response = MockResponse(429, {"X-RateLimit-Reset": str(reset_time)})

        msg = provider._get_retry_time_message(response)
        assert "minute" in msg.lower()

    def test_retry_time_message_hours(self):
        """Test retry message for times in hours."""
        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        # Mock response with reset in 2 hours
        reset_time = int((datetime.now() + timedelta(hours=2)).timestamp())
        response = MockResponse(429, {"X-RateLimit-Reset": str(reset_time)})

        msg = provider._get_retry_time_message(response)
        assert "hour" in msg.lower()

    def test_retry_time_message_missing_header(self):
        """Test retry message when reset header is missing."""
        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        response = MockResponse(429, {})

        msg = provider._get_retry_time_message(response)
        assert msg == "unknown time"


class TestTransientErrorRetry:
    """Test retry logic for transient server errors."""

    @respx.mock
    def test_503_retries_with_backoff(self, monkeypatch):
        """Test that 503 errors are retried with exponential backoff."""
        # Mock time.sleep to avoid actual delays
        sleep_calls = []

        def mock_sleep(seconds):
            sleep_calls.append(seconds)

        monkeypatch.setattr(time, "sleep", mock_sleep)

        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        # Mock 503 responses for first 2 attempts, then success
        responses = [
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(200, json={"id": 123, "login": "testuser"}),
        ]
        response_iter = iter(responses)

        respx.get("https://api.github.com/user").mock(side_effect=lambda request: next(response_iter))

        # Should eventually succeed after retries
        result = provider._make_request("/user")
        assert result["login"] == "testuser"

        # Should have slept twice (for first two failures)
        assert len(sleep_calls) == 2
        # First sleep should be around 1 second (base_delay=1, jitter up to 0.5)
        assert 1.0 <= sleep_calls[0] <= 1.5
        # Second sleep should be around 2 seconds (base_delay=2, jitter up to 1.0)
        assert 2.0 <= sleep_calls[1] <= 3.0

    @respx.mock
    def test_502_retries(self, monkeypatch):
        """Test that 502 Bad Gateway errors are retried."""
        sleep_calls = []
        monkeypatch.setattr(time, "sleep", lambda s: sleep_calls.append(s))

        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        # Mock 502 then success
        responses = [
            httpx.Response(502),
            httpx.Response(200, json={"id": 456}),
        ]
        response_iter = iter(responses)

        respx.get("https://api.github.com/repos/owner/repo/pulls/1").mock(
            side_effect=lambda request: next(response_iter)
        )

        result = provider._make_request("/repos/owner/repo/pulls/1")
        assert result["id"] == 456
        assert len(sleep_calls) == 1  # One retry

    @respx.mock
    def test_504_retries(self, monkeypatch):
        """Test that 504 Gateway Timeout errors are retried."""
        sleep_calls = []
        monkeypatch.setattr(time, "sleep", lambda s: sleep_calls.append(s))

        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        # Mock 504 then success
        responses = [
            httpx.Response(504),
            httpx.Response(200, json={"total_count": 5}),
        ]
        response_iter = iter(responses)

        respx.get("https://api.github.com/search/issues").mock(
            side_effect=lambda request: next(response_iter)
        )

        result = provider._make_request("/search/issues")
        assert result["total_count"] == 5
        assert len(sleep_calls) == 1

    @respx.mock
    def test_max_retries_exceeded(self, monkeypatch):
        """Test that retries stop after max attempts."""
        sleep_calls = []
        monkeypatch.setattr(time, "sleep", lambda s: sleep_calls.append(s))

        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        # Mock 503 responses beyond max retries
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(503)
        )

        # Should fail after max retries
        with pytest.raises(RuntimeError, match="request failed with status 503"):
            provider._make_request("/user")

        # Should have attempted 3 retries (slept 3 times)
        assert len(sleep_calls) == 3

    @respx.mock
    def test_400_not_retried(self):
        """Test that 400 Bad Request is not retried."""
        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        # Mock 400 response (client error, should not retry)
        respx.get("https://api.github.com/repos/owner/repo/pulls/1").mock(
            return_value=httpx.Response(400)
        )

        # Should fail immediately without retries
        with pytest.raises(RuntimeError, match="request failed with status 400"):
            provider._make_request("/repos/owner/repo/pulls/1")

    @respx.mock
    def test_404_not_retried(self):
        """Test that 404 Not Found is not retried."""
        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        # Mock 404 response
        respx.get("https://api.github.com/repos/nonexistent/repo/pulls/1").mock(
            return_value=httpx.Response(404)
        )

        # Should fail immediately without retries
        with pytest.raises(RuntimeError, match="request failed with status 404"):
            provider._make_request("/repos/nonexistent/repo/pulls/1")


class TestRateLimitWithFallback:
    """Test that rate limiting properly triggers fixture fallback."""

    @respx.mock
    def test_list_user_prs_falls_back_on_rate_limit(self):
        """Test that list_user_prs falls back to fixtures when rate limited."""
        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        # Mock rate limit response
        reset_time = int((datetime.now() + timedelta(hours=1)).timestamp())
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(
                403,
                headers={
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                },
            )
        )

        # Should fall back to fixtures
        prs = provider.list_user_prs("testuser")
        assert isinstance(prs, list)
        assert len(prs) == 3  # From fixture

    @respx.mock
    def test_get_pr_details_falls_back_on_rate_limit(self):
        """Test that get_pr_details falls back to fixtures when rate limited."""
        token_provider = MockTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        # Mock rate limit response
        reset_time = int((datetime.now() + timedelta(minutes=30)).timestamp())
        respx.get("https://api.github.com/repos/owner/repo/pulls/123").mock(
            return_value=httpx.Response(
                429,
                headers={
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                },
            )
        )

        # Should fall back to fixtures
        details = provider.get_pr_details("owner/repo", 123)
        assert details["pr_number"] == 123
        assert details["title"] == "Add new feature X"


class TestTokenNotLogged:
    """Test that tokens are never logged."""

    @respx.mock
    def test_rate_limit_error_does_not_log_token(self, caplog):
        """Test that rate limit errors don't leak tokens in logs."""
        token_provider = MockTokenProvider("ghp_secrettoken123456")
        provider = LiveGitHubProvider(token_provider)

        reset_time = int((datetime.now() + timedelta(hours=1)).timestamp())
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(
                403,
                headers={
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                },
            )
        )

        with pytest.raises(RuntimeError):
            provider._make_request("/user")

        # Check that token is not in any log messages
        for record in caplog.records:
            assert "ghp_secrettoken123456" not in record.message

    @respx.mock
    def test_transient_error_does_not_log_token(self, caplog, monkeypatch):
        """Test that transient errors don't leak tokens in logs."""
        monkeypatch.setattr(time, "sleep", lambda s: None)

        token_provider = MockTokenProvider("ghp_secrettoken789012")
        provider = LiveGitHubProvider(token_provider)

        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(503)
        )

        with pytest.raises(RuntimeError):
            provider._make_request("/user")

        # Check that token is not in any log messages
        for record in caplog.records:
            assert "ghp_secrettoken789012" not in record.message
