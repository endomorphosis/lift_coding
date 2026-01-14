"""GitHub provider interface and fixture-backed implementation."""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from handsfree.github.auth import GitHubAuthProvider, get_default_auth_provider


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
