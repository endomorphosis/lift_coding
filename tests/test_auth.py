"""Tests for authentication module."""

import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException

from handsfree.auth import (
    FIXTURE_USER_ID,
    get_auth_mode,
    get_current_user,
    validate_jwt_token,
)


class TestAuthMode:
    """Test authentication mode detection."""

    def test_default_auth_mode_is_dev(self):
        """Test that default auth mode is dev."""
        with patch.dict(os.environ, {}, clear=False):
            # Remove HANDSFREE_AUTH_MODE if it exists
            os.environ.pop("HANDSFREE_AUTH_MODE", None)
            assert get_auth_mode() == "dev"

    def test_auth_mode_from_env(self):
        """Test that auth mode is read from environment."""
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "jwt"}):
            assert get_auth_mode() == "jwt"

        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "api_key"}):
            assert get_auth_mode() == "api_key"

    def test_auth_mode_case_insensitive(self):
        """Test that auth mode is case insensitive."""
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "JWT"}):
            assert get_auth_mode() == "jwt"

        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "Dev"}):
            assert get_auth_mode() == "dev"


class TestJWTValidation:
    """Test JWT token validation."""

    @pytest.fixture
    def jwt_secret(self):
        """JWT secret for testing."""
        return "test-secret-key-for-jwt-validation"

    @pytest.fixture
    def test_user_id(self):
        """Test user ID."""
        return str(uuid.uuid4())

    def create_token(self, user_id: str, secret: str, expired: bool = False) -> str:
        """Helper to create a test JWT token."""
        payload = {
            "user_id": user_id,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=-1 if expired else 1),  # Expired or valid
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    def test_valid_jwt_token(self, jwt_secret, test_user_id):
        """Test validation of a valid JWT token."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": jwt_secret}):
            token = self.create_token(test_user_id, jwt_secret)
            result = validate_jwt_token(token)
            assert result == test_user_id

    def test_jwt_token_with_sub_claim(self, jwt_secret, test_user_id):
        """Test JWT token using 'sub' claim for user_id."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": jwt_secret}):
            payload = {
                "sub": test_user_id,
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) + timedelta(hours=1),
            }
            token = jwt.encode(payload, jwt_secret, algorithm="HS256")
            result = validate_jwt_token(token)
            assert result == test_user_id

    def test_jwt_token_with_uid_claim(self, jwt_secret, test_user_id):
        """Test JWT token using 'uid' claim for user_id."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": jwt_secret}):
            payload = {
                "uid": test_user_id,
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) + timedelta(hours=1),
            }
            token = jwt.encode(payload, jwt_secret, algorithm="HS256")
            result = validate_jwt_token(token)
            assert result == test_user_id

    def test_expired_jwt_token(self, jwt_secret, test_user_id):
        """Test that expired JWT tokens are rejected."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": jwt_secret}):
            token = self.create_token(test_user_id, jwt_secret, expired=True)
            with pytest.raises(HTTPException) as exc_info:
                validate_jwt_token(token)
            assert exc_info.value.status_code == 401
            assert "expired" in exc_info.value.detail.lower()

    def test_invalid_jwt_signature(self, jwt_secret, test_user_id):
        """Test that tokens with invalid signatures are rejected."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": jwt_secret}):
            token = self.create_token(test_user_id, "wrong-secret")
            with pytest.raises(HTTPException) as exc_info:
                validate_jwt_token(token)
            assert exc_info.value.status_code == 401

    def test_jwt_token_missing_user_id(self, jwt_secret):
        """Test that tokens without user_id claim are rejected."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": jwt_secret}):
            payload = {
                "some_other_claim": "value",
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) + timedelta(hours=1),
            }
            token = jwt.encode(payload, jwt_secret, algorithm="HS256")
            with pytest.raises(HTTPException) as exc_info:
                validate_jwt_token(token)
            assert exc_info.value.status_code == 401
            assert "missing user identifier" in exc_info.value.detail.lower()

    def test_jwt_token_invalid_user_id_format(self, jwt_secret):
        """Test that tokens with non-UUID user_id are rejected."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": jwt_secret}):
            payload = {
                "user_id": "not-a-uuid",
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) + timedelta(hours=1),
            }
            token = jwt.encode(payload, jwt_secret, algorithm="HS256")
            with pytest.raises(HTTPException) as exc_info:
                validate_jwt_token(token)
            assert exc_info.value.status_code == 401
            assert "must be a valid uuid" in exc_info.value.detail.lower()

    def test_jwt_missing_secret_key(self, test_user_id):
        """Test that missing JWT_SECRET_KEY is handled."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("JWT_SECRET_KEY", None)
            with pytest.raises(HTTPException) as exc_info:
                validate_jwt_token("any-token")
            assert exc_info.value.status_code == 500

    def test_jwt_custom_algorithm(self, test_user_id):
        """Test JWT validation with custom algorithm."""
        secret = "test-secret"
        with patch.dict(os.environ, {"JWT_SECRET_KEY": secret, "JWT_ALGORITHM": "HS256"}):
            payload = {
                "user_id": test_user_id,
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) + timedelta(hours=1),
            }
            token = jwt.encode(payload, secret, algorithm="HS256")
            result = validate_jwt_token(token)
            assert result == test_user_id


class TestGetCurrentUser:
    """Test the get_current_user dependency."""

    @pytest.fixture
    def test_user_id(self):
        """Test user ID."""
        return str(uuid.uuid4())

    @pytest.fixture
    def jwt_secret(self):
        """JWT secret for testing."""
        return "test-secret-key"

    def create_credentials(self, token: str):
        """Helper to create mock HTTPAuthorizationCredentials."""
        from fastapi.security import HTTPAuthorizationCredentials

        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    @pytest.mark.asyncio
    async def test_dev_mode_with_valid_header(self, test_user_id):
        """Test dev mode with valid X-User-Id header."""
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
            user_id = await get_current_user(x_user_id=test_user_id, credentials=None)
            assert user_id == test_user_id

    @pytest.mark.asyncio
    async def test_dev_mode_without_header(self):
        """Test dev mode without X-User-Id header uses fixture."""
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
            user_id = await get_current_user(x_user_id=None, credentials=None)
            assert user_id == FIXTURE_USER_ID

    @pytest.mark.asyncio
    async def test_dev_mode_with_invalid_header(self):
        """Test dev mode with invalid X-User-Id header falls back to fixture."""
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
            user_id = await get_current_user(x_user_id="not-a-uuid", credentials=None)
            assert user_id == FIXTURE_USER_ID

    @pytest.mark.asyncio
    async def test_jwt_mode_with_valid_token(self, test_user_id, jwt_secret):
        """Test JWT mode with valid token."""
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "jwt", "JWT_SECRET_KEY": jwt_secret}):
            payload = {
                "user_id": test_user_id,
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) + timedelta(hours=1),
            }
            token = jwt.encode(payload, jwt_secret, algorithm="HS256")
            credentials = self.create_credentials(token)

            user_id = await get_current_user(x_user_id=None, credentials=credentials)
            assert user_id == test_user_id

    @pytest.mark.asyncio
    async def test_jwt_mode_without_token(self):
        """Test JWT mode without token raises 401."""
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "jwt", "JWT_SECRET_KEY": "secret"}):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(x_user_id=None, credentials=None)
            assert exc_info.value.status_code == 401
            assert "authentication required" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_jwt_mode_with_invalid_token(self, jwt_secret):
        """Test JWT mode with invalid token raises 401."""
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "jwt", "JWT_SECRET_KEY": jwt_secret}):
            credentials = self.create_credentials("invalid-token")
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(x_user_id=None, credentials=credentials)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_jwt_mode_ignores_x_user_id_header(self, test_user_id, jwt_secret):
        """Test that JWT mode ignores X-User-Id header."""
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "jwt", "JWT_SECRET_KEY": jwt_secret}):
            # Even with X-User-Id header, JWT mode requires token
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(x_user_id=test_user_id, credentials=None)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_mode_with_valid_key(self, test_user_id):
        """Test API key mode with valid key."""
        from unittest.mock import patch

        from handsfree.db.api_keys import create_api_key

        # Create an in-memory database and API key
        with patch("handsfree.api.get_db") as mock_get_db:
            from handsfree.db.connection import init_db

            db = init_db(":memory:")
            mock_get_db.return_value = db

            # Create API key
            plaintext_key, _ = create_api_key(db, test_user_id, label="Test")

            # Test validation
            with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "api_key"}):
                credentials = self.create_credentials(plaintext_key)
                user_id = await get_current_user(x_user_id=None, credentials=credentials)
                assert user_id == test_user_id

    @pytest.mark.asyncio
    async def test_api_key_mode_with_invalid_key(self):
        """Test API key mode with invalid key."""
        from unittest.mock import patch

        with patch("handsfree.api.get_db") as mock_get_db:
            from handsfree.db.connection import init_db

            db = init_db(":memory:")
            mock_get_db.return_value = db

            with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "api_key"}):
                credentials = self.create_credentials("invalid-key")
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(x_user_id=None, credentials=credentials)
                assert exc_info.value.status_code == 401
                assert "invalid or revoked" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_api_key_mode_with_revoked_key(self, test_user_id):
        """Test API key mode with revoked key."""
        from unittest.mock import patch

        from handsfree.db.api_keys import create_api_key, revoke_api_key

        with patch("handsfree.api.get_db") as mock_get_db:
            from handsfree.db.connection import init_db

            db = init_db(":memory:")
            mock_get_db.return_value = db

            # Create and revoke API key
            plaintext_key, api_key = create_api_key(db, test_user_id, label="Test")
            revoke_api_key(db, api_key.id)

            # Test validation fails
            with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "api_key"}):
                credentials = self.create_credentials(plaintext_key)
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(x_user_id=None, credentials=credentials)
                assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_mode_without_key(self):
        """Test API key mode without providing a key."""
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "api_key"}):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(x_user_id=None, credentials=None)
            assert exc_info.value.status_code == 401
            assert "api key required" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_unknown_auth_mode(self):
        """Test that unknown auth mode raises 500."""
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "unknown"}):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(x_user_id=None, credentials=None)
            assert exc_info.value.status_code == 500
