"""GitHub authentication and token management.

This module provides a minimal auth provider that can mint/use tokens via environment variables
in dev mode. It is structured to be swapped for GitHub App installation tokens later.
"""

import os
from abc import ABC, abstractmethod


class GitHubAuthProvider(ABC):
    """Abstract interface for GitHub authentication providers."""

    @abstractmethod
    def get_token(self, user_id: str) -> str | None:
        """Get a GitHub token for the specified user.

        Args:
            user_id: User ID to get token for.

        Returns:
            GitHub token or None if not available.
        """
        pass

    @abstractmethod
    def supports_live_mode(self) -> bool:
        """Check if this provider supports live GitHub API calls.

        Returns:
            True if live mode is supported, False for fixture-only mode.
        """
        pass


class EnvironmentTokenProvider(GitHubAuthProvider):
    """Token provider that reads from environment variables.

    This is a development/testing provider that reads tokens from the GITHUB_TOKEN
    environment variable. It does not support per-user tokens or token refresh.

    Usage:
        export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
        export GITHUB_LIVE_MODE=true
    """

    def __init__(self):
        """Initialize the environment token provider."""
        self.token = os.getenv("GITHUB_TOKEN")
        self.live_mode_enabled = os.getenv("GITHUB_LIVE_MODE", "").lower() in ("true", "1", "yes")

    def get_token(self, user_id: str) -> str | None:
        """Get a GitHub token from environment variable.

        Args:
            user_id: User ID (ignored in this implementation).

        Returns:
            GitHub token from GITHUB_TOKEN env var, or None if not set.
        """
        return self.token if self.live_mode_enabled else None

    def supports_live_mode(self) -> bool:
        """Check if live mode is enabled via environment variable.

        Returns:
            True if GITHUB_LIVE_MODE is set to true/1/yes and GITHUB_TOKEN is available.
        """
        return self.live_mode_enabled and self.token is not None


class FixtureOnlyProvider(GitHubAuthProvider):
    """Auth provider that always uses fixtures (default behavior)."""

    def get_token(self, user_id: str) -> str | None:
        """Always returns None to force fixture mode.

        Args:
            user_id: User ID (ignored).

        Returns:
            None to indicate fixture-only mode.
        """
        return None

    def supports_live_mode(self) -> bool:
        """Fixture-only provider never supports live mode.

        Returns:
            False.
        """
        return False


def get_default_auth_provider() -> GitHubAuthProvider:
    """Get the default GitHub auth provider based on environment.

    Returns:
        EnvironmentTokenProvider if GITHUB_LIVE_MODE is enabled,
        otherwise FixtureOnlyProvider.
    """
    if os.getenv("GITHUB_LIVE_MODE", "").lower() in ("true", "1", "yes"):
        return EnvironmentTokenProvider()
    return FixtureOnlyProvider()
