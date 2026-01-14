"""Logging utilities with security and observability features.

Provides:
- Secret redaction for GitHub tokens and authorization headers
- Structured logging helpers
- Request ID context management
"""

import logging
import re
import uuid
from contextvars import ContextVar
from typing import Any

# Context variable for request ID (thread-safe and async-safe)
_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Patterns for secret redaction
GITHUB_TOKEN_PATTERNS = [
    (re.compile(r"ghp_[A-Za-z0-9_]+"), "ghp_***REDACTED***"),  # Personal access tokens
    (re.compile(r"ghs_[A-Za-z0-9_]+"), "ghs_***REDACTED***"),  # GitHub App tokens
    (re.compile(r"gho_[A-Za-z0-9_]+"), "gho_***REDACTED***"),  # OAuth tokens
    (re.compile(r"github_pat_[A-Za-z0-9_]+"), "github_pat_***REDACTED***"),  # Fine-grained PATs
]

# Pattern for Authorization header values
AUTH_HEADER_PATTERN = re.compile(
    r"(Authorization[:\s]+)([^\s,;]+)",
    re.IGNORECASE,
)


def redact_secrets(text: str | None) -> str:
    """Redact secrets from text (GitHub tokens, auth headers, etc.).

    Args:
        text: Text that may contain secrets

    Returns:
        Text with secrets redacted
    """
    if text is None:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # Redact GitHub tokens
    for pattern, replacement in GITHUB_TOKEN_PATTERNS:
        text = pattern.sub(replacement, text)

    # Redact Authorization header values
    text = AUTH_HEADER_PATTERN.sub(r"\1***REDACTED***", text)

    return text


def set_request_id(request_id: str | None = None) -> str:
    """Set the request ID for the current context.

    Args:
        request_id: Optional request ID (generates one if not provided)

    Returns:
        The request ID that was set
    """
    if request_id is None:
        request_id = str(uuid.uuid4())

    _request_id_var.set(request_id)
    return request_id


def get_request_id() -> str | None:
    """Get the request ID for the current context.

    Returns:
        The request ID or None if not set
    """
    return _request_id_var.get()


def clear_request_id() -> None:
    """Clear the request ID from the current context."""
    _request_id_var.set(None)


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **kwargs: Any,
) -> None:
    """Log a message with structured context (request_id, user_id, etc.).

    Args:
        logger: Logger instance
        level: Log level (logging.INFO, logging.ERROR, etc.)
        message: Log message
        **kwargs: Additional structured fields to include
    """
    # Get request ID from context
    request_id = get_request_id()

    # Build structured log message
    parts = [message]

    # Add request_id if available
    if request_id:
        parts.append(f"request_id={request_id}")

    # Add other structured fields
    for key, value in kwargs.items():
        # Redact any secrets in values
        safe_value = redact_secrets(str(value))
        parts.append(f"{key}={safe_value}")

    # Join all parts
    structured_message = " | ".join(parts)

    # Log with appropriate level
    logger.log(level, structured_message)


def log_info(logger: logging.Logger, message: str, **kwargs: Any) -> None:
    """Log an info message with structured context.

    Args:
        logger: Logger instance
        message: Log message
        **kwargs: Additional structured fields
    """
    log_with_context(logger, logging.INFO, message, **kwargs)


def log_warning(logger: logging.Logger, message: str, **kwargs: Any) -> None:
    """Log a warning message with structured context.

    Args:
        logger: Logger instance
        message: Log message
        **kwargs: Additional structured fields
    """
    log_with_context(logger, logging.WARNING, message, **kwargs)


def log_error(logger: logging.Logger, message: str, **kwargs: Any) -> None:
    """Log an error message with structured context.

    Args:
        logger: Logger instance
        message: Log message
        **kwargs: Additional structured fields
    """
    log_with_context(logger, logging.ERROR, message, **kwargs)


def log_debug(logger: logging.Logger, message: str, **kwargs: Any) -> None:
    """Log a debug message with structured context.

    Args:
        logger: Logger instance
        message: Log message
        **kwargs: Additional structured fields
    """
    log_with_context(logger, logging.DEBUG, message, **kwargs)
