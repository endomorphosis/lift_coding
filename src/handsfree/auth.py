"""Authentication module for HandsFree Dev Companion.

Provides production-ready authentication scaffolding with environment-based mode switching:
- dev mode: allows X-User-Id header fallback (for development/testing)
- jwt mode: requires JWT bearer token and extracts user_id from claims
- api_key mode: supports API key authentication (future extension)

Environment Variables:
    HANDSFREE_AUTH_MODE: Authentication mode (dev|jwt|api_key), defaults to "dev"
    JWT_SECRET_KEY: Secret key for JWT validation (required in jwt mode)
    JWT_ALGORITHM: JWT algorithm (default: HS256)
"""

import logging
import os
import uuid
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# Fixture user ID for development/testing
FIXTURE_USER_ID = "00000000-0000-0000-0000-000000000001"

# Security scheme for JWT bearer tokens
security = HTTPBearer(auto_error=False)


def get_auth_mode() -> str:
    """Get the configured authentication mode.

    Returns:
        Authentication mode: "dev", "jwt", or "api_key"
    """
    return os.getenv("HANDSFREE_AUTH_MODE", "dev").lower()


def validate_jwt_token(token: str) -> str:
    """Validate JWT token and extract user_id.

    Args:
        token: JWT token string

    Returns:
        User ID extracted from token claims

    Raises:
        HTTPException: If token is invalid or missing required claims
    """
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        logger.error("JWT_SECRET_KEY not configured for jwt mode")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not properly configured",
        )

    algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    try:
        # Decode and verify the token
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])

        # Extract user_id from claims
        # Try common claim names: user_id, sub (subject), uid
        user_id = payload.get("user_id") or payload.get("sub") or payload.get("uid")

        if not user_id:
            logger.warning("JWT token missing user_id claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user identifier",
            )

        # Validate user_id is a valid UUID format
        try:
            uuid.UUID(str(user_id))
        except (ValueError, AttributeError):
            logger.warning("JWT token contains invalid user_id format: %s", user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: user identifier must be a valid UUID",
            ) from None

        return str(user_id)

    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from None
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid JWT token: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from None


def validate_api_key(api_key: str) -> str:
    """Validate API key and return associated user_id.

    Args:
        api_key: API key string

    Returns:
        User ID associated with the API key

    Raises:
        HTTPException: If API key is invalid

    Note:
        This is a placeholder for future API key implementation.
        In production, this would look up the key in a database.
    """
    # TODO: Implement actual API key validation with database lookup
    # For now, reject all API keys as not implemented
    logger.warning("API key authentication not yet implemented")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="API key authentication not yet implemented",
    )


async def get_current_user(
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
) -> str:
    """Extract and validate user ID based on configured auth mode.

    This is the main authentication dependency used by all endpoints.

    Behavior by auth mode:
    - dev: Accepts X-User-Id header, falls back to fixture user ID
    - jwt: Requires valid JWT bearer token, extracts user_id from claims
    - api_key: Requires valid API key (not yet fully implemented)

    Args:
        x_user_id: Optional X-User-Id header (used in dev mode)
        credentials: Optional Bearer token credentials

    Returns:
        User ID string (UUID format)

    Raises:
        HTTPException: In jwt/api_key mode if authentication fails
    """
    auth_mode = get_auth_mode()

    if auth_mode == "dev":
        # Development mode: allow X-User-Id header fallback
        if x_user_id:
            # Validate it's a proper UUID format
            try:
                uuid.UUID(x_user_id)
                logger.debug("Dev mode: Using user_id from X-User-Id header: %s", x_user_id)
                return x_user_id
            except (ValueError, AttributeError):
                logger.warning("Dev mode: Invalid X-User-Id format: %s, using fixture", x_user_id)
                return FIXTURE_USER_ID

        logger.debug("Dev mode: Using fixture user ID")
        return FIXTURE_USER_ID

    elif auth_mode == "jwt":
        # JWT mode: require valid bearer token
        if not credentials or not credentials.credentials:
            logger.warning("JWT mode: Missing bearer token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = validate_jwt_token(credentials.credentials)
        logger.debug("JWT mode: Authenticated user_id: %s", user_id)
        return user_id

    elif auth_mode == "api_key":
        # API key mode: require valid API key
        # Check for API key in Authorization header (as Bearer token for now)
        # In the future, could support X-API-Key header
        if not credentials or not credentials.credentials:
            logger.warning("API key mode: Missing API key")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = validate_api_key(credentials.credentials)
        logger.debug("API key mode: Authenticated user_id: %s", user_id)
        return user_id

    else:
        logger.error("Unknown authentication mode: %s", auth_mode)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid authentication configuration",
        )


# Type alias for dependency injection
CurrentUser = Annotated[str, Depends(get_current_user)]
