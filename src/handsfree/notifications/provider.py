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


class WebPushProvider(NotificationDeliveryProvider):
    """WebPush provider for sending real push notifications using VAPID authentication.

    This provider uses the pywebpush library to send Web Push notifications
    to browser endpoints. It requires VAPID keys for authentication.
    """

    def __init__(
        self,
        vapid_public_key: str,
        vapid_private_key: str,
        vapid_subject: str,
    ):
        """Initialize WebPush provider with VAPID credentials.

        Args:
            vapid_public_key: VAPID public key for authentication.
            vapid_private_key: VAPID private key for authentication.
            vapid_subject: VAPID subject (typically mailto: URL).
        """
        self.vapid_public_key = vapid_public_key
        self.vapid_private_key = vapid_private_key
        self.vapid_subject = vapid_subject

        # Check if pywebpush is available
        try:
            import pywebpush  # noqa: F401

            self._pywebpush_available = True
        except ImportError:
            logger.warning(
                "pywebpush library not available. WebPush notifications will fail. "
                "Install with: pip install pywebpush"
            )
            self._pywebpush_available = False

    def send(
        self,
        subscription_endpoint: str,
        notification_data: dict[str, Any],
        subscription_keys: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send a Web Push notification.

        Args:
            subscription_endpoint: The push service endpoint URL.
            notification_data: The notification payload to send.
            subscription_keys: Required keys for WebPush (p256dh, auth).

        Returns:
            Dictionary with delivery result:
            - ok: bool - Whether the send was successful
            - message: str - Status message
            - delivery_id: str - Optional delivery tracking ID
        """
        if not self._pywebpush_available:
            return {
                "ok": False,
                "message": "pywebpush library not installed",
                "delivery_id": None,
            }

        if not subscription_keys:
            return {
                "ok": False,
                "message": "Missing subscription keys (p256dh, auth required)",
                "delivery_id": None,
            }

        # Validate required keys
        if "p256dh" not in subscription_keys or "auth" not in subscription_keys:
            return {
                "ok": False,
                "message": "Missing required subscription keys: p256dh and auth are required",
                "delivery_id": None,
            }

        try:
            import json

            from pywebpush import WebPushException, webpush

            # Prepare subscription info for pywebpush
            subscription_info = {
                "endpoint": subscription_endpoint,
                "keys": {
                    "p256dh": subscription_keys["p256dh"],
                    "auth": subscription_keys["auth"],
                },
            }

            # Send the notification
            response = webpush(
                subscription_info=subscription_info,
                data=json.dumps(notification_data),
                vapid_private_key=self.vapid_private_key,
                vapid_claims={
                    "sub": self.vapid_subject,
                },
            )

            # Success
            logger.info(
                "WebPush notification sent successfully to %s (status: %s)",
                subscription_endpoint,
                response.status_code if hasattr(response, "status_code") else "unknown",
            )

            status_code = response.status_code if hasattr(response, "status_code") else "sent"
            return {
                "ok": True,
                "message": f"Notification sent (status: {status_code})",
                "delivery_id": f"webpush-{hash((subscription_endpoint, str(notification_data)))}",
            }

        except WebPushException as e:
            # WebPush-specific errors (e.g., expired subscription, invalid keys)
            logger.warning(
                "WebPush error sending to %s: %s",
                subscription_endpoint,
                str(e),
            )
            return {
                "ok": False,
                "message": f"WebPush error: {str(e)}",
                "delivery_id": None,
            }

        except Exception as e:
            # Unexpected errors
            logger.error(
                "Unexpected error sending WebPush to %s: %s",
                subscription_endpoint,
                str(e),
                exc_info=True,
            )
            return {
                "ok": False,
                "message": f"Unexpected error: {str(e)}",
                "delivery_id": None,
            }


def get_notification_provider() -> NotificationDeliveryProvider | None:
    """Get the configured notification delivery provider.

    Reads the HANDSFREE_NOTIFICATION_PROVIDER environment variable:
    - "logger" or "dev": Returns DevLoggerProvider
    - "webpush": Returns WebPushProvider with VAPID configuration
    - None or empty: Returns None (push notifications disabled)

    Returns:
        NotificationDeliveryProvider instance or None if disabled.
    """
    provider_name = os.getenv("HANDSFREE_NOTIFICATION_PROVIDER", "").lower()

    if provider_name in ("logger", "dev"):
        return DevLoggerProvider()

    if provider_name == "webpush":
        # Get VAPID configuration from environment
        vapid_public_key = os.getenv("HANDSFREE_WEBPUSH_VAPID_PUBLIC_KEY", "")
        vapid_private_key = os.getenv("HANDSFREE_WEBPUSH_VAPID_PRIVATE_KEY", "")
        vapid_subject = os.getenv("HANDSFREE_WEBPUSH_VAPID_SUBJECT", "")

        if not vapid_public_key or not vapid_private_key or not vapid_subject:
            logger.error(
                "WebPush provider requested but VAPID credentials not configured. "
                "Required: HANDSFREE_WEBPUSH_VAPID_PUBLIC_KEY, "
                "HANDSFREE_WEBPUSH_VAPID_PRIVATE_KEY, "
                "HANDSFREE_WEBPUSH_VAPID_SUBJECT"
            )
            return None

        return WebPushProvider(
            vapid_public_key=vapid_public_key,
            vapid_private_key=vapid_private_key,
            vapid_subject=vapid_subject,
        )

    # Default: push notifications disabled
    return None
