"""Secret management interfaces and implementations.

This module provides production-ready abstractions for storing and retrieving
secrets (like GitHub tokens) from various secret management backends.
"""

from .env_secrets import EnvSecretManager
from .factory import get_default_secret_manager, get_secret_manager, reset_secret_manager
from .interface import SecretManager
from .vault_secrets import VaultSecretManager

# Lazy import for AWSSecretManager (requires optional boto3 dependency)
try:
    from .aws_secrets import AWSSecretManager
except ImportError:
    AWSSecretManager = None  # type: ignore

__all__ = [
    "SecretManager",
    "EnvSecretManager",
    "VaultSecretManager",
    "AWSSecretManager",
    "get_secret_manager",
    "get_default_secret_manager",
    "reset_secret_manager",
]
