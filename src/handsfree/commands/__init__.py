"""Command system for hands-free dev companion.

This module implements:
- Intent parsing from text transcripts
- Profile-based response tuning
- Pending action confirmation flow
- Command routing
"""

from .intent_parser import IntentParser, ParsedIntent
from .pending_actions import PendingAction, PendingActionManager, RedisPendingActionManager
from .profiles import Profile, ProfileConfig
from .session_context import RedisSessionContext, SessionContext

__all__ = [
    "IntentParser",
    "ParsedIntent",
    "PendingActionManager",
    "RedisPendingActionManager",
    "PendingAction",
    "Profile",
    "ProfileConfig",
    "CommandRouter",
    "SessionContext",
    "RedisSessionContext",
]


def __getattr__(name: str):
    """Lazily import router types to avoid package-level cycles."""
    if name == "CommandRouter":
        from .router import CommandRouter

        return CommandRouter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
