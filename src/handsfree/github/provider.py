"""GitHub provider interface and fixture-backed implementation."""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from handsfree.github.auth import GitHubAuthProvider, get_default_auth_provider

logger = logging.getLogger(__name__)


class GitHubProviderInterface(ABC):
    """Abstract interface for GitHub data providers."""

    @abstractmethod
    def list_user_prs(self, user: str, user_id: str | None = None) -> list[dict[str, Any]]:
        """List PRs where user is requested reviewer or assignee."""
        pass

    @abstractmethod
    def get_pr_details(
        self, repo: str, pr_number: int, user_id: str | None = None
    ) -> dict[str, Any]:
        """Get PR details including title, description, labels, checks, and reviews."""
        pass

    @abstractmethod
    def get_pr_checks(
        self, repo: str, pr_number: int, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get check runs for a PR."""
        pass

    @abstractmethod
    def get_pr_reviews(
        self, repo: str, pr_number: int, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get reviews for a PR."""
        pass


class GitHubProvider(GitHubProviderInterface):
    """GitHub provider that supports both fixture and live modes.

    In fixture mode (default), returns data from fixture files.
    In live mode (when GITHUB_LIVE_MODE=true and GITHUB_TOKEN is set),
    calls the real GitHub API.
    """

    def __init__(
        self,
        fixtures_dir: Path | None = None,
        auth_provider: GitHubAuthProvider | None = None,
    ):
        """Initialize with optional fixtures directory path and auth provider.

        Args:
            fixtures_dir: Path to fixture files (defaults to tests/fixtures/github/api).
            auth_provider: Auth provider for GitHub tokens (defaults to environment-based).
        """
        if fixtures_dir is None:
            # Default to tests/fixtures/github/api relative to repo root
            fixtures_dir = Path(__file__).parent.parent.parent.parent / "tests/fixtures/github/api"
        self.fixtures_dir = Path(fixtures_dir)

        if auth_provider is None:
            auth_provider = get_default_auth_provider()
        self.auth_provider = auth_provider

    def _load_fixture(self, fixture_name: str) -> Any:
        """Load a fixture file by name."""
        fixture_path = self.fixtures_dir / fixture_name
        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture not found: {fixture_path}")
        with open(fixture_path) as f:
            return json.load(f)

    def _is_live_mode(self, user_id: str | None) -> bool:
        """Check if live mode should be used for this request.

        Args:
            user_id: User ID for the request.

        Returns:
            True if live mode is enabled and a token is available.
        """
        if not self.auth_provider.supports_live_mode():
            return False
        if user_id is None:
            return False
        token = self.auth_provider.get_token(user_id)
        return token is not None

    def list_user_prs(self, user: str, user_id: str | None = None) -> list[dict[str, Any]]:
        """List PRs where user is requested reviewer or assignee.

        Args:
            user: GitHub username.
            user_id: User ID for auth (optional).

        Returns:
            List of PR dictionaries.
        """
        if self._is_live_mode(user_id):
            # TODO: Call real GitHub API in future PR
            # For now, fall back to fixtures even in live mode
            pass
        return self._load_fixture("user_prs.json")

    def get_pr_details(
        self, repo: str, pr_number: int, user_id: str | None = None
    ) -> dict[str, Any]:
        """Get PR details including title, description, labels, checks, and reviews.

        Args:
            repo: Repository in owner/name format.
            pr_number: Pull request number.
            user_id: User ID for auth (optional).

        Returns:
            PR details dictionary.
        """
        if self._is_live_mode(user_id):
            # TODO: Call real GitHub API in future PR
            # For now, fall back to fixtures even in live mode
            pass
        return self._load_fixture(f"pr_{pr_number}_details.json")

    def get_pr_checks(
        self, repo: str, pr_number: int, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get check runs for a PR.

        Args:
            repo: Repository in owner/name format.
            pr_number: Pull request number.
            user_id: User ID for auth (optional).

        Returns:
            List of check run dictionaries.
        """
        if self._is_live_mode(user_id):
            # TODO: Call real GitHub API in future PR
            # For now, fall back to fixtures even in live mode
            pass
        return self._load_fixture(f"pr_{pr_number}_checks.json")

    def get_pr_reviews(
        self, repo: str, pr_number: int, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get reviews for a PR.

        Args:
            repo: Repository in owner/name format.
            pr_number: Pull request number.
            user_id: User ID for auth (optional).

        Returns:
            List of review dictionaries.
        """
        if self._is_live_mode(user_id):
            # TODO: Call real GitHub API in future PR
            # For now, fall back to fixtures even in live mode
            pass
        return self._load_fixture(f"pr_{pr_number}_reviews.json")


class LiveGitHubProvider(GitHubProviderInterface):
    """Live GitHub provider that makes real API calls.

    Uses a token provider to get authentication credentials.
    Falls back to fixture behavior if no token is available.
    """

    def __init__(self, token_provider):
        """Initialize with a token provider.

        Args:
            token_provider: TokenProvider instance for authentication
        """
        from handsfree.github.auth import TokenProvider

        if not isinstance(token_provider, TokenProvider):
            raise TypeError(
                f"token_provider must be an instance of TokenProvider, "
                f"got {type(token_provider).__name__}"
            )

        self._token_provider = token_provider
        self._fallback_provider = GitHubProvider()  # For fixture fallback

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for GitHub API requests.

        Returns:
            Dict of headers including Authorization if token available
        """
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "HandsFree-Dev-Companion/1.0",
        }

        token = self._token_provider.get_token()
        if token:
            # SECURITY: Token is in memory only, never logged
            headers["Authorization"] = f"Bearer {token}"

        return headers

    def _make_request(self, endpoint: str) -> dict[str, Any]:
        """Make a GET request to GitHub API.

        Args:
            endpoint: API endpoint path (e.g., "/repos/owner/repo/pulls/123")

        Returns:
            JSON response as dict

        Note:
            This is a stub implementation. Full implementation would:
            - Use httpx or requests library
            - Handle rate limiting
            - Handle errors and retries
            - Parse and validate responses
        """
        token = self._token_provider.get_token()
        if not token:
            logger.warning(
                "No GitHub token available, cannot make live API request to %s", endpoint
            )
            raise RuntimeError("GitHub token not available for live API calls")

        # TODO: Implement actual HTTP request
        # import httpx
        # response = httpx.get(
        #     f"https://api.github.com{endpoint}",
        #     headers=self._get_headers(),
        #     timeout=10.0
        # )
        # response.raise_for_status()
        # return response.json()

        logger.warning(
            "Live GitHub API not yet implemented. Returning fixture data. "
            "TODO: Implement HTTP client integration."
        )
        # For now, fall back to fixtures
        raise NotImplementedError("Live GitHub API calls not yet implemented")

    def list_user_prs(self, user: str) -> list[dict[str, Any]]:
        """List PRs where user is requested reviewer or assignee.

        Falls back to fixtures if live mode not available.
        """
        try:
            return self._make_request(f"/search/issues?q=user:{user}+type:pr+state:open")
        except (RuntimeError, NotImplementedError):
            logger.info("Falling back to fixture for list_user_prs")
            return self._fallback_provider.list_user_prs(user)

    def get_pr_details(self, repo: str, pr_number: int) -> dict[str, Any]:
        """Get PR details including title, description, labels, checks, and reviews.

        Falls back to fixtures if live mode not available.
        """
        try:
            return self._make_request(f"/repos/{repo}/pulls/{pr_number}")
        except (RuntimeError, NotImplementedError):
            logger.info("Falling back to fixture for get_pr_details")
            return self._fallback_provider.get_pr_details(repo, pr_number)

    def get_pr_checks(self, repo: str, pr_number: int) -> list[dict[str, Any]]:
        """Get check runs for a PR.

        Falls back to fixtures if live mode not available.
        """
        try:
            return self._make_request(f"/repos/{repo}/pulls/{pr_number}/checks")
        except (RuntimeError, NotImplementedError):
            logger.info("Falling back to fixture for get_pr_checks")
            return self._fallback_provider.get_pr_checks(repo, pr_number)

    def get_pr_reviews(self, repo: str, pr_number: int) -> list[dict[str, Any]]:
        """Get reviews for a PR.

        Falls back to fixtures if live mode not available.
        """
        try:
            return self._make_request(f"/repos/{repo}/pulls/{pr_number}/reviews")
        except (RuntimeError, NotImplementedError):
            logger.info("Falling back to fixture for get_pr_reviews")
            return self._fallback_provider.get_pr_reviews(repo, pr_number)
