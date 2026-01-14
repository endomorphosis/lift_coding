"""GitHub authentication and token management.

This module provides a minimal auth provider that can mint/use tokens via environment variables
in dev mode. It is structured to be swapped for GitHub App installation tokens later.
"""

import os
from abc import ABC, abstractmethod


class TokenProvider(ABC):
    """Abstract interface for token providers (used by LiveGitHubProvider).
    
    This is a simplified interface that doesn't require user_id parameter.
    """

    @abstractmethod
    def get_token(self) -> str | None:
        """Get a GitHub token.

        Returns:
            GitHub token or None if not available.
        """
        pass


class GitHubAuthProvider(ABC):
    """Abstract interface for GitHub authentication providers.
    
    This is the legacy interface used by GitHubProvider.
    """

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


class FixtureTokenProvider(TokenProvider):
    """Token provider that always returns None (fixture-only mode)."""

    def get_token(self) -> str | None:
        """Always returns None to force fixture mode.

        Returns:
            None to indicate fixture-only mode.
        """
        return None


class EnvTokenProvider(TokenProvider):
    """Token provider that reads from GITHUB_TOKEN environment variable.
    
    This is a simplified provider for LiveGitHubProvider that doesn't
    require per-user tokens.
    """

    def __init__(self):
        """Initialize the environment token provider."""
        self.token = os.getenv("GITHUB_TOKEN")

    def get_token(self) -> str | None:
        """Get a GitHub token from environment variable.

        Returns:
            GitHub token from GITHUB_TOKEN env var, or None if not set.
        """
        return self.token


def get_default_auth_provider() -> GitHubAuthProvider:
    """Get the default GitHub auth provider based on environment.

    Returns:
        EnvironmentTokenProvider if GITHUB_LIVE_MODE is enabled,
        otherwise FixtureOnlyProvider.
    """
    if os.getenv("GITHUB_LIVE_MODE", "").lower() in ("true", "1", "yes"):
        return EnvironmentTokenProvider()
    return FixtureOnlyProvider()


def get_token_provider() -> TokenProvider:
    """Get a token provider for LiveGitHubProvider based on environment.
    
    Checks HANDS_FREE_GITHUB_MODE or GITHUB_LIVE_MODE environment variables.

    Returns:
        EnvTokenProvider if live mode is enabled, otherwise FixtureTokenProvider.
    """
    # Check both environment variable names as per problem statement
    live_mode = (
        os.getenv("HANDS_FREE_GITHUB_MODE", "").lower() == "live"
        or os.getenv("GITHUB_LIVE_MODE", "").lower() in ("true", "1", "yes")
    )
    
    if live_mode and os.getenv("GITHUB_TOKEN"):
        return EnvTokenProvider()
    return FixtureTokenProvider()
