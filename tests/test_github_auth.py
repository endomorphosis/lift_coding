"""Tests for GitHub authentication and token providers."""

import os
from unittest.mock import patch

import pytest

from handsfree.github.auth import (
    EnvTokenProvider,
    FixtureTokenProvider,
    get_token_provider,
)


class TestFixtureTokenProvider:
    """Test fixture token provider."""

    def test_returns_none(self):
        """Test that fixture provider returns None."""
        provider = FixtureTokenProvider()
        assert provider.get_token() is None


class TestEnvTokenProvider:
    """Test environment-based token provider."""

    def test_no_credentials(self):
        """Test when no environment variables are set."""
        with patch.dict(os.environ, {}, clear=True):
            provider = EnvTokenProvider()
            token = provider.get_token()
            assert token is None

    def test_github_token(self):
        """Test with GITHUB_TOKEN environment variable."""
        test_token = "ghp_test1234567890"
        with patch.dict(os.environ, {"GITHUB_TOKEN": test_token}):
            provider = EnvTokenProvider()
            token = provider.get_token()
            assert token == test_token

    def test_github_app_credentials_not_implemented(self):
        """Test with GitHub App credentials (not yet implemented)."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_APP_PRIVATE_KEY": "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
                "GITHUB_APP_ID": "12345",
                "GITHUB_APP_INSTALLATION_ID": "67890",
            },
        ):
            provider = EnvTokenProvider()
            token = provider.get_token()
            # Should return None since GitHub App auth is not yet implemented
            assert token is None

    def test_github_token_priority_over_app(self):
        """Test that GITHUB_TOKEN takes priority over GitHub App credentials."""
        test_token = "ghp_test1234567890"
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": test_token,
                "GITHUB_APP_PRIVATE_KEY": "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
                "GITHUB_APP_ID": "12345",
                "GITHUB_APP_INSTALLATION_ID": "67890",
            },
        ):
            provider = EnvTokenProvider()
            token = provider.get_token()
            assert token == test_token


class TestGetTokenProvider:
    """Test token provider factory function."""

    def test_fixture_mode_default(self):
        """Test that fixture mode is default."""
        with patch.dict(os.environ, {}, clear=True):
            provider = get_token_provider()
            assert isinstance(provider, FixtureTokenProvider)

    def test_fixture_mode_explicit(self):
        """Test explicit fixture mode."""
        with patch.dict(os.environ, {"GITHUB_LIVE_MODE": "false"}):
            provider = get_token_provider()
            assert isinstance(provider, FixtureTokenProvider)

    def test_live_mode_enabled(self):
        """Test live mode enabled."""
        with patch.dict(os.environ, {"GITHUB_LIVE_MODE": "true"}):
            provider = get_token_provider()
            assert isinstance(provider, EnvTokenProvider)

    def test_live_mode_case_insensitive(self):
        """Test that live mode flag is case insensitive."""
        with patch.dict(os.environ, {"GITHUB_LIVE_MODE": "TRUE"}):
            provider = get_token_provider()
            assert isinstance(provider, EnvTokenProvider)

        with patch.dict(os.environ, {"GITHUB_LIVE_MODE": "True"}):
            provider = get_token_provider()
            assert isinstance(provider, EnvTokenProvider)
