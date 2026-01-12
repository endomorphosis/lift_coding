"""GitHub provider interface and fixture-backed implementation."""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class GitHubProviderInterface(ABC):
    """Abstract interface for GitHub data providers."""

    @abstractmethod
    def list_user_prs(self, user: str) -> list[dict[str, Any]]:
        """List PRs where user is requested reviewer or assignee."""
        pass

    @abstractmethod
    def get_pr_details(self, repo: str, pr_number: int) -> dict[str, Any]:
        """Get PR details including title, description, labels, checks, and reviews."""
        pass

    @abstractmethod
    def get_pr_checks(self, repo: str, pr_number: int) -> list[dict[str, Any]]:
        """Get check runs for a PR."""
        pass

    @abstractmethod
    def get_pr_reviews(self, repo: str, pr_number: int) -> list[dict[str, Any]]:
        """Get reviews for a PR."""
        pass


class GitHubProvider(GitHubProviderInterface):
    """Fixture-backed GitHub provider for testing and development."""

    def __init__(self, fixtures_dir: Path | None = None):
        """Initialize with optional fixtures directory path."""
        if fixtures_dir is None:
            # Default to tests/fixtures/github/api relative to repo root
            fixtures_dir = Path(__file__).parent.parent.parent.parent / "tests/fixtures/github/api"
        self.fixtures_dir = Path(fixtures_dir)

    def _load_fixture(self, fixture_name: str) -> Any:
        """Load a fixture file by name."""
        fixture_path = self.fixtures_dir / fixture_name
        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture not found: {fixture_path}")
        with open(fixture_path) as f:
            return json.load(f)

    def list_user_prs(self, user: str) -> list[dict[str, Any]]:
        """List PRs where user is requested reviewer or assignee."""
        return self._load_fixture("user_prs.json")

    def get_pr_details(self, repo: str, pr_number: int) -> dict[str, Any]:
        """Get PR details including title, description, labels, checks, and reviews."""
        return self._load_fixture(f"pr_{pr_number}_details.json")

    def get_pr_checks(self, repo: str, pr_number: int) -> list[dict[str, Any]]:
        """Get check runs for a PR."""
        return self._load_fixture(f"pr_{pr_number}_checks.json")

    def get_pr_reviews(self, repo: str, pr_number: int) -> list[dict[str, Any]]:
        """Get reviews for a PR."""
        return self._load_fixture(f"pr_{pr_number}_reviews.json")
