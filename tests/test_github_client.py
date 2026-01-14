"""Unit tests for GitHub API client write operations."""

import json

import pytest

from handsfree.github.client import request_reviewers


class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        """Return JSON data."""
        if not self._json_data:
            # Raise JSONDecodeError for empty response
            raise json.JSONDecodeError("Expecting value", "", 0)
        return self._json_data


class TestRequestReviewers:
    """Tests for request_reviewers function."""

    def test_successful_request(self, monkeypatch):
        """Test successful reviewer request with mocked httpx."""
        # Mock httpx.post to avoid real network calls
        mock_response = MockResponse(
            status_code=201,
            json_data={
                "id": 1,
                "node_id": "MDEwOlB1bGxSZXF1ZXN0MQ==",
                "number": 42,
            },
        )

        def mock_post(*args, **kwargs):
            return mock_response

        # Patch httpx module
        import handsfree.github.client as client_module

        # Import httpx to populate the lazy-loaded module
        client_module._import_httpx()

        monkeypatch.setattr(client_module._httpx, "post", mock_post)

        # Call the function
        result = request_reviewers(
            repo="test/repo",
            pr_number=42,
            reviewers=["alice", "bob"],
            token="test_token",
        )

        # Verify result
        assert result["ok"] is True
        assert "alice" in result["message"]
        assert "bob" in result["message"]
        assert result["status_code"] == 201
        assert "response_data" in result

    def test_github_api_error(self, monkeypatch):
        """Test handling of GitHub API error responses."""
        # Mock httpx.post to return an error
        mock_response = MockResponse(
            status_code=422,
            json_data={"message": "Validation Failed"},
        )

        def mock_post(*args, **kwargs):
            return mock_response

        import handsfree.github.client as client_module

        client_module._import_httpx()
        monkeypatch.setattr(client_module._httpx, "post", mock_post)

        result = request_reviewers(
            repo="test/repo",
            pr_number=42,
            reviewers=["invalid-user"],
            token="test_token",
        )

        assert result["ok"] is False
        assert result["status_code"] == 422
        assert "Validation Failed" in result["message"]

    def test_network_error(self, monkeypatch):
        """Test handling of network errors."""

        def mock_post(*args, **kwargs):
            raise ConnectionError("Network unreachable")

        import handsfree.github.client as client_module

        client_module._import_httpx()
        monkeypatch.setattr(client_module._httpx, "post", mock_post)

        result = request_reviewers(
            repo="test/repo",
            pr_number=42,
            reviewers=["alice"],
            token="test_token",
        )

        assert result["ok"] is False
        assert "ConnectionError" in result["message"]
        assert result["status_code"] == 0

    def test_timeout_error(self, monkeypatch):
        """Test handling of timeout errors."""
        import handsfree.github.client as client_module

        client_module._import_httpx()

        def mock_post(*args, **kwargs):
            # Simulate timeout by raising the httpx TimeoutException
            raise client_module._httpx.TimeoutException("Request timed out")

        monkeypatch.setattr(client_module._httpx, "post", mock_post)

        result = request_reviewers(
            repo="test/repo",
            pr_number=42,
            reviewers=["alice"],
            token="test_token",
            timeout=5.0,
        )

        assert result["ok"] is False
        assert "TimeoutException" in result["message"]
        assert result["status_code"] == 0

    def test_invalid_repo_format(self):
        """Test validation of repo format."""
        with pytest.raises(ValueError, match="Invalid repo format"):
            request_reviewers(
                repo="invalid-repo-format",
                pr_number=42,
                reviewers=["alice"],
                token="test_token",
            )

    def test_invalid_pr_number(self):
        """Test validation of pr_number."""
        with pytest.raises(ValueError, match="Invalid pr_number"):
            request_reviewers(
                repo="test/repo",
                pr_number=0,
                reviewers=["alice"],
                token="test_token",
            )

    def test_empty_reviewers(self):
        """Test validation of empty reviewers list."""
        with pytest.raises(ValueError, match="reviewers list cannot be empty"):
            request_reviewers(
                repo="test/repo",
                pr_number=42,
                reviewers=[],
                token="test_token",
            )

    def test_empty_token(self):
        """Test validation of empty token."""
        with pytest.raises(ValueError, match="token cannot be empty"):
            request_reviewers(
                repo="test/repo",
                pr_number=42,
                reviewers=["alice"],
                token="",
            )

    def test_correct_api_endpoint_and_headers(self, monkeypatch):
        """Test that correct endpoint and headers are used."""
        captured_args = {}

        def mock_post(url, *args, **kwargs):
            captured_args["url"] = url
            captured_args["headers"] = kwargs.get("headers", {})
            captured_args["json"] = kwargs.get("json", {})
            return MockResponse(status_code=201, json_data={})

        import handsfree.github.client as client_module

        client_module._import_httpx()
        monkeypatch.setattr(client_module._httpx, "post", mock_post)

        request_reviewers(
            repo="octocat/hello-world",
            pr_number=123,
            reviewers=["alice"],
            token="test_token_123",
        )

        # Verify endpoint
        assert captured_args["url"] == (
            "https://api.github.com/repos/octocat/hello-world/pulls/123/requested_reviewers"
        )

        # Verify headers
        headers = captured_args["headers"]
        assert headers["Authorization"] == "Bearer test_token_123"
        assert headers["Accept"] == "application/vnd.github+json"
        assert "HandsFree" in headers["User-Agent"]

        # Verify payload
        assert captured_args["json"] == {"reviewers": ["alice"]}
