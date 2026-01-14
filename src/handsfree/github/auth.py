"""GitHub authentication and token provider interface.

This module provides abstractions for GitHub authentication without storing tokens directly.
Token providers can be fixture-based (for testing) or environment-based (for dev/local).
"""

import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class TokenProvider(ABC):
    """Abstract interface for GitHub token providers."""

    @abstractmethod
    def get_token(self) -> str | None:
        """Get a GitHub token for API access.
        
        Returns:
            GitHub token string, or None if not available.
        """
        pass


class FixtureTokenProvider(TokenProvider):
    """Fixture-based token provider that returns None (fixture mode)."""

    def get_token(self) -> str | None:
        """Return None to indicate fixture mode.
        
        In fixture mode, the GitHub provider uses local fixture data
        instead of making real API calls.
        """
        return None


class EnvTokenProvider(TokenProvider):
    """Environment-based token provider for dev/local testing.
    
    Supports:
    - GITHUB_TOKEN: Personal access token
    - GITHUB_APP_PRIVATE_KEY + GITHUB_APP_ID + GITHUB_APP_INSTALLATION_ID:
      GitHub App authentication (stubbed with TODO for now)
    """

    def __init__(self):
        """Initialize provider and check for available credentials."""
        self._token = os.environ.get("GITHUB_TOKEN")
        self._app_private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY")
        self._app_id = os.environ.get("GITHUB_APP_ID")
        self._installation_id = os.environ.get("GITHUB_APP_INSTALLATION_ID")

    def get_token(self) -> str | None:
        """Get token from environment variables.
        
        Priority:
        1. GITHUB_TOKEN (personal access token)
        2. GitHub App credentials (TODO: implement JWT/installation token minting)
        
        Returns:
            GitHub token string, or None if no credentials available.
            
        Security:
            - Tokens are never logged
            - Only token presence is logged, not the value
        """
        # Personal access token (simplest approach for dev)
        if self._token:
            logger.info("Using GitHub personal access token from GITHUB_TOKEN")
            # SECURITY: Never log the actual token value
            return self._token

        # GitHub App authentication (stubbed for now)
        if self._app_private_key and self._app_id and self._installation_id:
            logger.warning(
                "GitHub App authentication detected but not yet implemented. "
                "TODO: Implement JWT signing and installation token minting. "
                "For now, set GITHUB_TOKEN to use a personal access token."
            )
            # TODO: Implement GitHub App JWT/installation token flow
            # 1. Parse private key
            # 2. Create and sign JWT with app_id
            # 3. Exchange JWT for installation access token
            # 4. Return installation token
            return None

        logger.info("No GitHub credentials found in environment (fixture mode)")
        return None


def get_token_provider() -> TokenProvider:
    """Get the appropriate token provider based on configuration.
    
    Uses GITHUB_LIVE_MODE environment variable to determine provider:
    - GITHUB_LIVE_MODE=true: Use EnvTokenProvider (live mode)
    - GITHUB_LIVE_MODE=false or unset: Use FixtureTokenProvider (default)
    
    Returns:
        TokenProvider instance
    """
    live_mode = os.environ.get("GITHUB_LIVE_MODE", "false").lower() == "true"
    
    if live_mode:
        logger.info("GitHub live mode enabled")
        return EnvTokenProvider()
    else:
        logger.info("GitHub fixture mode enabled (default)")
        return FixtureTokenProvider()
