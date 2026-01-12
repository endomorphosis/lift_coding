"""Command system for hands-free dev companion.

This module implements:
- Intent parsing from text transcripts
- Profile-based response tuning
- Pending action confirmation flow
- Command routing
"""

from .intent_parser import IntentParser, ParsedIntent
from .pending_actions import PendingAction, PendingActionManager
from .profiles import Profile, ProfileConfig
from .router import CommandRouter

__all__ = [
    "IntentParser",
    "ParsedIntent",
    "PendingActionManager",
    "PendingAction",
    "Profile",
    "ProfileConfig",
    "CommandRouter",
]
