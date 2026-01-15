"""GitHub authentication and token management.

This module provides GitHub authentication including:
- Simple environment-based token access (dev/testing)
- GitHub App installation token minting with JWT authentication
- Token caching with automatic refresh

Security notes:
- Private keys and tokens are never logged
- Tokens are cached in memory only, never persisted to disk
- Installation IDs may be stored in DB, but not tokens
"""

import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Lazy imports for JWT functionality to avoid dependencies when not needed
_jwt = None
_httpx = None


def _import_jwt():
    """Lazily import JWT library."""
    global _jwt
    if _jwt is None:
        import jwt as jwt_module

        _jwt = jwt_module
    return _jwt


def _import_httpx():
    """Lazily import httpx library."""
    global _httpx
    if _httpx is None:
        import httpx as httpx_module

        _httpx = httpx_module
    return _httpx


class TokenProvider(ABC):
    """Abstract interface for GitHub token providers.

    This is the base interface that all token providers implement.
    It provides a simple get_token() method that returns tokens for GitHub API access.
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

    Legacy interface that includes user_id parameter.
    Kept for backward compatibility with existing code.

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


class FixtureTokenProvider(TokenProvider):
    """Token provider that always returns None (fixture-only mode).

    This is the default provider when no live mode configuration is present.
    All GitHub API calls will fall back to fixture data.
    """

    def get_token(self) -> str | None:
        """Always returns None to force fixture mode.

        Returns:
            None to indicate fixture-only mode.
        """
        return None


class EnvTokenProvider(TokenProvider):
    """Token provider that reads from GITHUB_TOKEN environment variable.

    This is a simple provider for development and testing that uses a
    personal access token from the environment.

    Usage:
        export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
        export GITHUB_LIVE_MODE=true
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


class GitHubAppTokenProvider(TokenProvider):
    """Token provider that mints GitHub App installation tokens.

    This provider implements the GitHub App authentication flow:
    1. Generate a JWT signed with the app's private key
    2. Use the JWT to request an installation access token
    3. Cache the token and refresh automatically when near expiry

    Configuration via environment variables:
    - GITHUB_APP_ID: The GitHub App ID
    - GITHUB_APP_PRIVATE_KEY_PEM: The private key in PEM format (supports \\n escaping)
    - GITHUB_INSTALLATION_ID: The installation ID for the app

    Security:
    - Private key is stored in memory only, never logged
    - Tokens are cached in memory only, never persisted
    - Token refresh happens automatically before expiry

    Thread-safety:
    - Token refresh is protected by a lock to prevent concurrent minting
    """

    # Token refresh window: refresh when less than 5 minutes remain
    TOKEN_REFRESH_WINDOW_SECONDS = 300

    # JWT expiration: 10 minutes (max allowed by GitHub)
    JWT_EXPIRATION_SECONDS = 600

    def __init__(
        self,
        app_id: str | None = None,
        private_key_pem: str | None = None,
        installation_id: str | None = None,
        http_client: Any | None = None,
    ):
        """Initialize the GitHub App token provider.

        Args:
            app_id: GitHub App ID (defaults to GITHUB_APP_ID env var)
            private_key_pem: Private key in PEM format (defaults to GITHUB_APP_PRIVATE_KEY_PEM)
            installation_id: Installation ID (defaults to GITHUB_INSTALLATION_ID)
            http_client: Optional HTTP client for testing (uses httpx by default)
        """
        self.app_id = app_id or os.getenv("GITHUB_APP_ID")
        self.installation_id = installation_id or os.getenv("GITHUB_INSTALLATION_ID")

        # Get private key and unescape newlines if needed
        raw_key = private_key_pem or os.getenv("GITHUB_APP_PRIVATE_KEY_PEM", "")
        self.private_key_pem = raw_key.replace("\\n", "\n") if raw_key else None

        self.http_client = http_client

        # Token cache
        self._cached_token: str | None = None
        self._token_expires_at: datetime | None = None

        # Thread lock for token refresh
        self._refresh_lock = threading.Lock()

        # Validate configuration
        if not self.app_id or not self.private_key_pem or not self.installation_id:
            logger.debug(
                "GitHub App not configured (missing app_id, private_key, or installation_id)"
            )

    def _is_configured(self) -> bool:
        """Check if GitHub App is properly configured.

        Returns:
            True if all required configuration is present.
        """
        return bool(self.app_id and self.private_key_pem and self.installation_id)

    def _generate_jwt(self) -> str:
        """Generate a JWT for GitHub App authentication.

        Returns:
            JWT token string.

        Raises:
            RuntimeError: If JWT generation fails.
        """
        if not self._is_configured():
            raise RuntimeError("GitHub App not configured")

        try:
            jwt_lib = _import_jwt()

            now = int(time.time())
            payload = {
                "iat": now,  # Issued at time
                "exp": now + self.JWT_EXPIRATION_SECONDS,  # Expiration (10 minutes)
                "iss": self.app_id,  # Issuer (GitHub App ID)
            }

            # Sign with RS256 algorithm
            token = jwt_lib.encode(payload, self.private_key_pem, algorithm="RS256")

            logger.debug(
                "Generated GitHub App JWT (expires in %d seconds)", self.JWT_EXPIRATION_SECONDS
            )
            return token

        except Exception as e:
            logger.error("Failed to generate GitHub App JWT: %s", str(e))
            raise RuntimeError(f"JWT generation failed: {e}") from e

    def _mint_installation_token(self) -> tuple[str, datetime]:
        """Mint a new installation access token using JWT.

        Returns:
            Tuple of (access_token, expires_at).

        Raises:
            RuntimeError: If token minting fails.
        """
        jwt_token = self._generate_jwt()

        # Use provided HTTP client or create a new httpx client
        if self.http_client:
            response = self.http_client.post(
                f"https://api.github.com/app/installations/{self.installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "HandsFree-Dev-Companion/1.0",
                },
            )
        else:
            httpx = _import_httpx()
            response = httpx.post(
                f"https://api.github.com/app/installations/{self.installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "HandsFree-Dev-Companion/1.0",
                },
                timeout=10.0,
            )

        if response.status_code != 201:
            logger.error(
                "Failed to mint installation token: HTTP %d - %s",
                response.status_code,
                response.text[:200],  # Log first 200 chars of error
            )
            raise RuntimeError(f"Failed to mint installation token: HTTP {response.status_code}")

        data = response.json()
        token = data["token"]
        expires_at_str = data["expires_at"]

        # Parse expiration time (ISO 8601 format)
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))

        logger.info("Minted GitHub App installation token (expires at %s)", expires_at.isoformat())

        return token, expires_at

    def _should_refresh_token(self) -> bool:
        """Check if the cached token should be refreshed.

        Returns:
            True if token should be refreshed (expired or near expiry).
        """
        if self._cached_token is None or self._token_expires_at is None:
            return True

        now = datetime.now(UTC)
        refresh_threshold = self._token_expires_at - timedelta(
            seconds=self.TOKEN_REFRESH_WINDOW_SECONDS
        )

        return now >= refresh_threshold

    def get_token(self) -> str | None:
        """Get a GitHub App installation access token.

        This method handles token caching and automatic refresh.
        Tokens are refreshed when they are within 5 minutes of expiry.

        Thread-safe: Uses a lock to prevent concurrent token refresh.

        Returns:
            GitHub installation access token, or None if not configured.
        """
        if not self._is_configured():
            return None

        try:
            # Fast path: check if we can use cached token without lock
            if not self._should_refresh_token():
                logger.debug("Using cached GitHub App installation token")
                return self._cached_token

            # Slow path: acquire lock and refresh token
            with self._refresh_lock:
                # Double-check after acquiring lock (another thread may have refreshed)
                if not self._should_refresh_token():
                    logger.debug("Using cached GitHub App installation token (after lock)")
                    return self._cached_token

                logger.debug("Refreshing GitHub App installation token")
                self._cached_token, self._token_expires_at = self._mint_installation_token()
                return self._cached_token

        except Exception as e:
            logger.error("Failed to get GitHub App token: %s", str(e))
            return None


class EnvironmentTokenProvider(GitHubAuthProvider):
    """Legacy token provider that reads from environment variables.

    This is kept for backward compatibility with existing code that uses
    the GitHubAuthProvider interface with user_id parameter.

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
    """Legacy auth provider that always uses fixtures (default behavior).

    Kept for backward compatibility.
    """

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


class UserTokenProvider(TokenProvider):
    """Token provider that gets tokens for specific users from connection metadata.

    This provider implements per-user token retrieval using the connection metadata
    stored in the database. It supports the token selection order:
    1. GitHub App installation token minting (if connection has installation_id)
    2. GITHUB_TOKEN env fallback (for users with connections but no installation_id)
    3. fixture-only mode (for users without any connections)

    Supports multi-installation scenarios by allowing repo-specific installation selection.

    Usage:
        db_conn = init_db()
        provider = UserTokenProvider(db_conn, user_id="user-123")
        token = provider.get_token()

        # For repo-specific installation:
        provider = UserTokenProvider(db_conn, user_id="user-123", repo_full_name="owner/repo")
        token = provider.get_token()
    """

    def __init__(
        self,
        db_conn: Any,
        user_id: str,
        repo_full_name: str | None = None,
        http_client: Any | None = None,
    ):
        """Initialize the user token provider.

        Args:
            db_conn: Database connection for looking up connection metadata.
            user_id: User ID to get token for.
            repo_full_name: Optional repository name for installation selection.
            http_client: Optional HTTP client for token minting (for testing).
        """
        self.db_conn = db_conn
        self.user_id = user_id
        self.repo_full_name = repo_full_name
        self.http_client = http_client
        self._cached_provider: TokenProvider | None = None

    def _get_provider(self) -> TokenProvider:
        """Get the appropriate token provider for this user.

        Returns:
            TokenProvider instance based on user's connection metadata.
        """
        if self._cached_provider is not None:
            return self._cached_provider

        # Import here to avoid circular dependency
        from handsfree.db.github_connections import (
            get_github_connections_by_user,
            get_installation_for_repo,
        )

        # Check if user has any connections
        connections = get_github_connections_by_user(conn=self.db_conn, user_id=self.user_id)
        has_connections = len(connections) > 0

        # If repo_full_name is provided, try to get repo-specific installation
        installation_id = None
        if self.repo_full_name:
            installation_id = get_installation_for_repo(
                conn=self.db_conn,
                user_id=self.user_id,
                repo_full_name=self.repo_full_name,
            )

        # If no repo-specific installation, fall back to user's most recent connection
        if installation_id is None and has_connections:
            connection = connections[0]
            installation_id = connection.installation_id

        # Priority 1: GitHub App installation token minting
        if installation_id is not None:
            app_id = os.getenv("GITHUB_APP_ID")
            private_key = os.getenv("GITHUB_APP_PRIVATE_KEY_PEM")
            if app_id and private_key:
                self._cached_provider = GitHubAppTokenProvider(
                    app_id=app_id,
                    private_key_pem=private_key,
                    installation_id=str(installation_id),
                    http_client=self.http_client,
                )
                return self._cached_provider

            logger.warning(
                "User %s has installation_id=%s but GitHub App is not configured",
                self.user_id,
                installation_id,
            )

        # Priority 2: Environment token fallback (only for users with connections)
        # Users with connections are real users, so they can use env token for dev
        if has_connections and os.getenv("GITHUB_TOKEN"):
            self._cached_provider = EnvTokenProvider()
            return self._cached_provider

        # Priority 3: Fixture-only mode (users without connections for isolation)
        self._cached_provider = FixtureTokenProvider()
        return self._cached_provider

    def get_token(self) -> str | None:
        """Get a GitHub token for this user."""
        return self._get_provider().get_token()


def get_default_auth_provider() -> GitHubAuthProvider:
    """Get the default GitHub auth provider based on environment.

    Legacy function kept for backward compatibility.

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

    Token selection order:
    1. GitHub App installation token minting (JWT -> installation access token)
       when app config present
    2. GITHUB_TOKEN env fallback for dev
    3. fixture-only mode otherwise

    Can be explicitly set to fixture mode with HANDS_FREE_GITHUB_MODE=fixtures

    Returns:
        TokenProvider instance based on available configuration.
    """
    # Explicit fixture mode overrides everything
    if os.getenv("HANDS_FREE_GITHUB_MODE", "").lower() == "fixtures":
        return FixtureTokenProvider()

    # Priority 1: GitHub App installation token minting
    app_id = os.getenv("GITHUB_APP_ID")
    private_key = os.getenv("GITHUB_APP_PRIVATE_KEY_PEM")
    installation_id = os.getenv("GITHUB_INSTALLATION_ID")
    if app_id and private_key and installation_id:
        return GitHubAppTokenProvider(
            app_id=app_id,
            private_key_pem=private_key,
            installation_id=installation_id,
        )

    # Priority 2: Environment token
    if os.getenv("GITHUB_TOKEN"):
        return EnvTokenProvider()

    # Priority 3: Fixture-only mode
    return FixtureTokenProvider()


def get_user_token_provider(
    db_conn: Any,
    user_id: str,
    repo_full_name: str | None = None,
    http_client: Any | None = None,
) -> TokenProvider:
    """Get a token provider for a specific user using their connection metadata.

    This function creates a UserTokenProvider that looks up the user's GitHub
    connection metadata and selects the appropriate token source.

    Supports multi-installation scenarios by allowing repo-specific installation selection.

    Args:
        db_conn: Database connection for looking up connection metadata.
        user_id: User ID to get token for.
        repo_full_name: Optional repository name for installation selection.
        http_client: Optional HTTP client for token minting (for testing).

    Returns:
        TokenProvider instance for the specified user.
    """
    return UserTokenProvider(
        db_conn=db_conn,
        user_id=user_id,
        repo_full_name=repo_full_name,
        http_client=http_client,
    )
