"""Tests for live GitHub API with mocked HTTP responses."""

from unittest.mock import MagicMock, patch

import pytest

from handsfree.github.auth import EnvTokenProvider
from handsfree.github.provider import LiveGitHubProvider


class TestLiveGitHubAPIWithMockedHTTP:
    """Test live GitHub API calls with mocked HTTP responses."""

    @pytest.fixture
    def mock_token_provider(self):
        """Create a token provider with a test token."""
        provider = EnvTokenProvider()
        provider.token = "ghp_test_token_12345"
        return provider

    @pytest.fixture
    def live_provider(self, mock_token_provider):
        """Create a live provider with a mocked token."""
        return LiveGitHubProvider(mock_token_provider)

    def test_list_user_prs_success(self, live_provider):
        """Test successful list_user_prs with mocked HTTP response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_count": 2,
            "items": [
                {
                    "number": 123,
                    "title": "Test PR 1",
                    "html_url": "https://github.com/owner/repo/pull/123",
                    "state": "open",
                    "user": {"login": "testuser"},
                    "repository_url": "https://api.github.com/repos/owner/repo",
                    "labels": [{"name": "bug"}],
                    "assignee": {"login": "testuser"},
                    "updated_at": "2026-01-10T12:00:00Z",
                },
                {
                    "number": 124,
                    "title": "Test PR 2",
                    "html_url": "https://github.com/owner/other-repo/pull/124",
                    "state": "open",
                    "user": {"login": "author2"},
                    "repository_url": "https://api.github.com/repos/owner/other-repo",
                    "labels": [],
                    "assignee": None,
                    "updated_at": "2026-01-11T14:00:00Z",
                },
            ],
        }

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = live_provider.list_user_prs("testuser")

            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]["pr_number"] == 123
            assert result[0]["title"] == "Test PR 1"
            assert result[0]["repo"] == "owner/repo"
            assert result[0]["labels"] == ["bug"]
            assert result[1]["pr_number"] == 124

    def test_get_pr_details_success(self, live_provider):
        """Test successful get_pr_details with mocked HTTP response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "number": 123,
            "title": "Add new feature",
            "body": "This PR adds a new feature",
            "html_url": "https://github.com/owner/repo/pull/123",
            "state": "open",
            "user": {"login": "contributor"},
            "created_at": "2026-01-08T10:00:00Z",
            "updated_at": "2026-01-10T15:30:00Z",
            "labels": [{"name": "feature"}, {"name": "needs-review"}],
            "base": {"ref": "main", "repo": {"full_name": "owner/repo"}},
            "head": {"ref": "feature/new", "sha": "abc123"},
            "additions": 450,
            "deletions": 120,
            "changed_files": 12,
            "draft": False,
            "mergeable": True,
        }

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = live_provider.get_pr_details("owner/repo", 123)

            assert result["pr_number"] == 123
            assert result["title"] == "Add new feature"
            assert result["repo"] == "owner/repo"
            assert result["author"] == "contributor"
            assert result["additions"] == 450
            assert result["deletions"] == 120
            assert result["changed_files"] == 12
            assert result["labels"] == ["feature", "needs-review"]

    def test_get_pr_checks_success(self, live_provider):
        """Test successful get_pr_checks with mocked HTTP responses."""
        # First response for getting PR details (to get head SHA)
        mock_pr_response = MagicMock()
        mock_pr_response.status_code = 200
        mock_pr_response.json.return_value = {
            "head": {"sha": "abc123def456"},
        }

        # Second response for getting check runs
        mock_checks_response = MagicMock()
        mock_checks_response.status_code = 200
        mock_checks_response.json.return_value = {
            "check_runs": [
                {
                    "name": "ci / build",
                    "status": "completed",
                    "conclusion": "success",
                    "started_at": "2026-01-10T15:00:00Z",
                    "completed_at": "2026-01-10T15:10:00Z",
                    "html_url": "https://github.com/owner/repo/actions/runs/123456",
                },
                {
                    "name": "ci / test",
                    "status": "completed",
                    "conclusion": "failure",
                    "started_at": "2026-01-10T15:10:00Z",
                    "completed_at": "2026-01-10T15:25:00Z",
                    "html_url": "https://github.com/owner/repo/actions/runs/123457",
                },
            ]
        }

        with patch("httpx.Client") as mock_client:
            mock_get = mock_client.return_value.__enter__.return_value.get
            mock_get.side_effect = [mock_pr_response, mock_checks_response]

            result = live_provider.get_pr_checks("owner/repo", 123)

            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]["name"] == "ci / build"
            assert result[0]["conclusion"] == "success"
            assert result[1]["name"] == "ci / test"
            assert result[1]["conclusion"] == "failure"

    def test_get_pr_reviews_success(self, live_provider):
        """Test successful get_pr_reviews with mocked HTTP response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "user": {"login": "reviewer1"},
                "state": "APPROVED",
                "submitted_at": "2026-01-09T14:00:00Z",
                "body": "LGTM!",
            },
            {
                "user": {"login": "reviewer2"},
                "state": "CHANGES_REQUESTED",
                "submitted_at": "2026-01-10T11:00:00Z",
                "body": "Please fix the tests",
            },
        ]

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = live_provider.get_pr_reviews("owner/repo", 123)

            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]["user"] == "reviewer1"
            assert result[0]["state"] == "APPROVED"
            assert result[1]["user"] == "reviewer2"
            assert result[1]["state"] == "CHANGES_REQUESTED"

    def test_missing_token_error(self):
        """Test that missing token raises clear error."""
        from handsfree.github.auth import FixtureTokenProvider

        provider = LiveGitHubProvider(FixtureTokenProvider())

        # Should fall back to fixtures when no token
        result = provider.list_user_prs("testuser")
        assert isinstance(result, list)
        assert len(result) == 3  # From fixture

    def test_401_authentication_error(self, live_provider):
        """Test 401 authentication error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            # Should fall back to fixture on auth error
            result = live_provider.list_user_prs("testuser")
            assert isinstance(result, list)
            assert len(result) == 3  # From fixture fallback

    def test_403_forbidden_error(self, live_provider):
        """Test 403 forbidden error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            # Should fall back to fixture on permission error
            result = live_provider.list_user_prs("testuser")
            assert isinstance(result, list)
            assert len(result) == 3  # From fixture fallback

    def test_429_rate_limit_error(self, live_provider):
        """Test 429 rate limit error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_response.headers = {"X-RateLimit-Reset": "1640000000"}

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            # Should fall back to fixture on rate limit
            result = live_provider.list_user_prs("testuser")
            assert isinstance(result, list)
            assert len(result) == 3  # From fixture fallback

    def test_timeout_error(self, live_provider):
        """Test timeout error handling."""
        import httpx

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = (
                httpx.TimeoutException("Request timed out")
            )

            # Should fall back to fixture on timeout
            result = live_provider.list_user_prs("testuser")
            assert isinstance(result, list)
            assert len(result) == 3  # From fixture fallback

    def test_network_error(self, live_provider):
        """Test network error handling."""
        import httpx

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.RequestError(
                "Network error"
            )

            # Should fall back to fixture on network error
            result = live_provider.list_user_prs("testuser")
            assert isinstance(result, list)
            assert len(result) == 3  # From fixture fallback

    def test_make_request_includes_query_params(self, live_provider):
        """Test that _make_request properly includes query parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}

        with patch("httpx.Client") as mock_client:
            mock_get = mock_client.return_value.__enter__.return_value.get
            mock_get.return_value = mock_response

            live_provider._make_request("/search/issues", params={"q": "test", "per_page": 100})

            # Verify the call was made with the correct parameters
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["params"] == {"q": "test", "per_page": 100}

    def test_headers_format(self, live_provider):
        """Test that headers are properly formatted."""
        headers = live_provider._get_headers()

        assert headers["Accept"] == "application/vnd.github.v3+json"
        assert headers["User-Agent"] == "HandsFree-Dev-Companion/1.0"
        assert headers["Authorization"] == "Bearer ghp_test_token_12345"
