"""Notification delivery provider abstraction.

This module defines the interface for push notification providers and includes
a development logger provider for testing.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class NotificationDeliveryProvider(ABC):
    """Abstract base class for notification delivery providers."""

    @abstractmethod
    def send(
        self,
        subscription_endpoint: str,
        notification_data: dict[str, Any],
        subscription_keys: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send a notification to a subscription endpoint.

        Args:
            subscription_endpoint: The endpoint URL or identifier to send to.
            notification_data: The notification payload to send.
            subscription_keys: Optional provider-specific keys (e.g., auth, p256dh for WebPush).

        Returns:
            Dictionary with delivery result:
            - ok: bool - Whether the send was successful
            - message: str - Status message
            - delivery_id: str - Optional delivery tracking ID
        """
        pass


class DevLoggerProvider(NotificationDeliveryProvider):
    """Development logger provider that logs notifications instead of sending them.

    This provider is used for development and testing. It simply logs the
    notification payload without sending real push notifications.
    """

    def send(
        self,
        subscription_endpoint: str,
        notification_data: dict[str, Any],
        subscription_keys: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Log notification instead of sending it.

        Args:
            subscription_endpoint: The endpoint URL or identifier.
            notification_data: The notification payload.
            subscription_keys: Optional subscription keys (ignored in logger).

        Returns:
            Dictionary with success status.
        """
        logger.info(
            "DevLoggerProvider: Would send notification to %s: %s",
            subscription_endpoint,
            notification_data,
        )

        return {
            "ok": True,
            "message": "Notification logged (dev mode)",
            "delivery_id": f"dev-{hash((subscription_endpoint, str(notification_data)))}",
        }


def get_notification_provider() -> NotificationDeliveryProvider | None:
    """Get the configured notification delivery provider.

    Reads the HANDSFREE_NOTIFICATION_PROVIDER environment variable:
    - "logger" or "dev": Returns DevLoggerProvider
    - None or empty: Returns None (push notifications disabled)

    Returns:
        NotificationDeliveryProvider instance or None if disabled.
    """
    provider_name = os.getenv("HANDSFREE_NOTIFICATION_PROVIDER", "").lower()

    if provider_name in ("logger", "dev"):
        return DevLoggerProvider()

    # Default: push notifications disabled
    return None
