"""Factory for creating secret manager instances.

This module provides a factory function that returns the appropriate
secret manager based on environment configuration.
"""

import logging
import os

from .env_secrets import EnvSecretManager
from .interface import SecretManager

logger = logging.getLogger(__name__)


def get_secret_manager() -> SecretManager:
    """Get a secret manager instance based on environment configuration.

    The secret manager type is determined by the SECRET_MANAGER_TYPE environment variable:
    - "env": EnvSecretManager (default, for development)
    - "aws": AWS Secrets Manager (future implementation)
    - "vault": HashiCorp Vault (future implementation)
    - "gcp": Google Secret Manager (future implementation)

    Environment Variables:
        SECRET_MANAGER_TYPE: Type of secret manager to use (default: "env")

    Returns:
        A SecretManager instance

    Raises:
        ValueError: If an unsupported secret manager type is specified
    """
    manager_type = os.getenv("SECRET_MANAGER_TYPE", "env").lower()

    if manager_type == "env":
        logger.info("Using EnvSecretManager (development mode)")
        return EnvSecretManager()
    elif manager_type == "aws":
        from .aws_secrets import AWSSecretManager

        logger.info("Using AWSSecretManager (production mode)")
        return AWSSecretManager()
    elif manager_type == "vault":
        from .vault_secrets import VaultSecretManager

        logger.info("Using VaultSecretManager (production mode)")
        return VaultSecretManager()
    elif manager_type == "gcp":
        # Future implementation
        # from .gcp_secrets import GCPSecretManager
        # return GCPSecretManager()
        raise NotImplementedError("Google Secret Manager support coming soon")
    else:
        raise ValueError(f"Unsupported secret manager type: {manager_type}")


# Singleton instance (lazy-loaded)
_secret_manager: SecretManager | None = None


def get_default_secret_manager() -> SecretManager:
    """Get the default secret manager singleton.

    This function returns a singleton instance of the secret manager,
    creating it on first access. Subsequent calls return the same instance.

    Returns:
        The default SecretManager instance
    """
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = get_secret_manager()
    return _secret_manager


def reset_secret_manager() -> None:
    """Reset the secret manager singleton.

    This is primarily useful for testing to force recreation of the manager.
    """
    global _secret_manager
    _secret_manager = None
