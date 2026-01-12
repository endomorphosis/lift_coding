"""
Persistence layer for handsfree dev companion.

Provides database connection and minimal persistence APIs for:
- Pending actions (with token and expiry)
- Action logs (with idempotency_key)
- Webhook events (with signature_ok flag)
- Commands history (with privacy toggle for transcript)
"""

from .action_logs import create_action_log, get_action_logs
from .commands import create_command, get_commands
from .connection import get_connection
from .pending_actions import (
    cleanup_expired_actions,
    create_pending_action,
    delete_pending_action,
    get_pending_action,
)
from .webhook_events import create_webhook_event, get_webhook_events

__all__ = [
    "get_connection",
    "create_pending_action",
    "get_pending_action",
    "delete_pending_action",
    "cleanup_expired_actions",
    "create_action_log",
    "get_action_logs",
    "create_webhook_event",
    "get_webhook_events",
    "create_command",
    "get_commands",
]
