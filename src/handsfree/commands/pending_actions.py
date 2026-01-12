"""Pending action management for confirmation flow."""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass
class PendingAction:
    """A pending action awaiting confirmation."""

    token: str
    intent_name: str
    entities: dict[str, Any]
    summary: str
    expires_at: datetime
    user_id: str | None = None

    def is_expired(self) -> bool:
        """Check if this action has expired."""
        return datetime.now(UTC) >= self.expires_at

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "token": self.token,
            "expires_at": self.expires_at.isoformat(),
            "summary": self.summary,
        }


class PendingActionManager:
    """Manage pending actions requiring confirmation."""

    def __init__(self, default_expiry_seconds: int = 60) -> None:
        """Initialize the manager.

        Args:
            default_expiry_seconds: Default time until actions expire (default: 60s)
        """
        self.default_expiry_seconds = default_expiry_seconds
        # In-memory storage: token -> PendingAction
        # In production, this should use Redis or similar
        self._pending: dict[str, PendingAction] = {}

    def create(
        self,
        intent_name: str,
        entities: dict[str, Any],
        summary: str,
        user_id: str | None = None,
        expiry_seconds: int | None = None,
    ) -> PendingAction:
        """Create a new pending action.

        Args:
            intent_name: The intent to execute on confirmation
            entities: The entities extracted from the command
            summary: Human-readable description for confirmation
            user_id: Optional user identifier
            expiry_seconds: Custom expiry time, or use default

        Returns:
            PendingAction with a unique token
        """
        # Generate secure random token
        token = secrets.token_urlsafe(32)

        # Calculate expiry time
        expiry = expiry_seconds or self.default_expiry_seconds
        expires_at = datetime.now(UTC) + timedelta(seconds=expiry)

        action = PendingAction(
            token=token,
            intent_name=intent_name,
            entities=entities,
            summary=summary,
            expires_at=expires_at,
            user_id=user_id,
        )

        self._pending[token] = action
        return action

    def get(self, token: str) -> PendingAction | None:
        """Retrieve a pending action by token.

        Args:
            token: The action token

        Returns:
            PendingAction if found and not expired, None otherwise
        """
        action = self._pending.get(token)
        if action is None:
            return None

        if action.is_expired():
            # Clean up expired action
            del self._pending[token]
            return None

        return action

    def confirm(self, token: str) -> PendingAction | None:
        """Confirm and consume a pending action.

        Args:
            token: The action token

        Returns:
            PendingAction if found and confirmed, None if not found or expired
        """
        action = self.get(token)
        if action is None:
            return None

        # Remove from pending after confirmation
        del self._pending[token]
        return action

    def cancel(self, token: str) -> bool:
        """Cancel a pending action.

        Args:
            token: The action token

        Returns:
            True if action was cancelled, False if not found or expired
        """
        action = self.get(token)
        if action is None:
            return False

        del self._pending[token]
        return True

    def cleanup_expired(self) -> int:
        """Remove all expired actions.

        Returns:
            Number of expired actions removed
        """
        now = datetime.now(UTC)
        expired_tokens = [
            token for token, action in self._pending.items() if action.expires_at <= now
        ]

        for token in expired_tokens:
            del self._pending[token]

        return len(expired_tokens)
