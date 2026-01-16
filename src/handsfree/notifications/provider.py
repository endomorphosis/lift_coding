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


class APNSProvider(NotificationDeliveryProvider):
    """Apple Push Notification Service (APNS) provider stub.

    This provider is a placeholder for future APNS integration.
    It requires APNS credentials and will send notifications to iOS devices.
    """

    def __init__(
        self,
        team_id: str,
        key_id: str,
        key_path: str,
        bundle_id: str,
        use_sandbox: bool = False,
    ):
        """Initialize APNS provider with credentials.

        Args:
            team_id: Apple Developer Team ID.
            key_id: APNS Key ID.
            key_path: Path to the .p8 key file.
            bundle_id: iOS app bundle identifier.
            use_sandbox: Whether to use sandbox environment (default: False).
        """
        self.team_id = team_id
        self.key_id = key_id
        self.key_path = key_path
        self.bundle_id = bundle_id
        self.use_sandbox = use_sandbox

        logger.info(
            "APNSProvider initialized (stub mode) - team_id=%s, bundle_id=%s, sandbox=%s",
            team_id,
            bundle_id,
            use_sandbox,
        )

    def send(
        self,
        subscription_endpoint: str,
        notification_data: dict[str, Any],
        subscription_keys: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send an APNS notification (stub implementation).

        Args:
            subscription_endpoint: The device token.
            notification_data: The notification payload to send.
            subscription_keys: Optional APNS-specific keys (unused in stub).

        Returns:
            Dictionary with delivery result (stub returns success).
        """
        logger.info(
            "APNSProvider (stub): Would send notification to device token %s: %s",
            subscription_endpoint[:10] + "...",  # Log only first 10 chars for security
            notification_data,
        )

        # In production, this would use aioapns or similar library to send
        # the notification to Apple's APNS servers
        return {
            "ok": True,
            "message": "APNS notification logged (stub mode)",
            "delivery_id": f"apns-stub-{hash((subscription_endpoint, str(notification_data)))}",
        }


class FCMProvider(NotificationDeliveryProvider):
    """Firebase Cloud Messaging (FCM) provider stub.

    This provider is a placeholder for future FCM integration.
    It requires FCM credentials and will send notifications to Android devices.
    """

    def __init__(
        self,
        project_id: str,
        credentials_path: str,
    ):
        """Initialize FCM provider with credentials.

        Args:
            project_id: Firebase project ID.
            credentials_path: Path to the service account JSON credentials file.
        """
        self.project_id = project_id
        self.credentials_path = credentials_path

        logger.info(
            "FCMProvider initialized (stub mode) - project_id=%s",
            project_id,
        )

    def send(
        self,
        subscription_endpoint: str,
        notification_data: dict[str, Any],
        subscription_keys: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send an FCM notification (stub implementation).

        Args:
            subscription_endpoint: The FCM registration token.
            notification_data: The notification payload to send.
            subscription_keys: Optional FCM-specific keys (unused in stub).

        Returns:
            Dictionary with delivery result (stub returns success).
        """
        logger.info(
            "FCMProvider (stub): Would send notification to FCM token %s: %s",
            subscription_endpoint[:10] + "...",  # Log only first 10 chars for security
            notification_data,
        )

        # In production, this would use firebase-admin or similar library
        # to send the notification to Google's FCM servers
        return {
            "ok": True,
            "message": "FCM notification logged (stub mode)",
            "delivery_id": f"fcm-stub-{hash((subscription_endpoint, str(notification_data)))}",
        }


def get_notification_provider() -> NotificationDeliveryProvider | None:
    """Get the configured notification delivery provider.

    Reads the HANDSFREE_NOTIFICATION_PROVIDER environment variable:
    - "logger" or "dev": Returns DevLoggerProvider
    - "webpush": Returns WebPushProvider with VAPID configuration
    - "apns": Returns APNSProvider with APNS configuration
    - "fcm": Returns FCMProvider with FCM configuration
    - None or empty: Returns None (push notifications disabled)

    Note: This function is kept for backward compatibility.
    For platform-specific delivery, use get_provider_for_platform() instead.

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

    if provider_name == "apns":
        # Get APNS configuration from environment
        team_id = os.getenv("HANDSFREE_APNS_TEAM_ID", "")
        key_id = os.getenv("HANDSFREE_APNS_KEY_ID", "")
        key_path = os.getenv("HANDSFREE_APNS_KEY_PATH", "")
        bundle_id = os.getenv("HANDSFREE_APNS_BUNDLE_ID", "")
        use_sandbox = os.getenv("HANDSFREE_APNS_USE_SANDBOX", "false").lower() == "true"

        if not team_id or not key_id or not key_path or not bundle_id:
            logger.error(
                "APNS provider requested but credentials not configured. "
                "Required: HANDSFREE_APNS_TEAM_ID, HANDSFREE_APNS_KEY_ID, "
                "HANDSFREE_APNS_KEY_PATH, HANDSFREE_APNS_BUNDLE_ID"
            )
            return None

        return APNSProvider(
            team_id=team_id,
            key_id=key_id,
            key_path=key_path,
            bundle_id=bundle_id,
            use_sandbox=use_sandbox,
        )

    if provider_name == "fcm":
        # Get FCM configuration from environment
        project_id = os.getenv("HANDSFREE_FCM_PROJECT_ID", "")
        credentials_path = os.getenv("HANDSFREE_FCM_CREDENTIALS_PATH", "")

        if not project_id or not credentials_path:
            logger.error(
                "FCM provider requested but credentials not configured. "
                "Required: HANDSFREE_FCM_PROJECT_ID, HANDSFREE_FCM_CREDENTIALS_PATH"
            )
            return None

        return FCMProvider(
            project_id=project_id,
            credentials_path=credentials_path,
        )

    # Default: push notifications disabled
    return None


def get_provider_for_platform(platform: str) -> NotificationDeliveryProvider | None:
    """Get the appropriate notification provider for a specific platform.

    This function selects the correct provider based on the subscription platform,
    allowing multi-platform push notification support (WebPush, APNS, FCM).

    Args:
        platform: Platform type ('webpush', 'apns', or 'fcm').

    Returns:
        NotificationDeliveryProvider instance or None if platform not supported/configured.
    """
    # Use dev logger if explicitly configured
    default_provider = os.getenv("HANDSFREE_NOTIFICATION_PROVIDER", "").lower()
    if default_provider in ("logger", "dev"):
        return DevLoggerProvider()

    # Platform-specific providers
    if platform == "webpush":
        vapid_public_key = os.getenv("HANDSFREE_WEBPUSH_VAPID_PUBLIC_KEY", "")
        vapid_private_key = os.getenv("HANDSFREE_WEBPUSH_VAPID_PRIVATE_KEY", "")
        vapid_subject = os.getenv("HANDSFREE_WEBPUSH_VAPID_SUBJECT", "")

        if not vapid_public_key or not vapid_private_key or not vapid_subject:
            logger.warning(
                "WebPush credentials not configured. "
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

    if platform == "apns":
        team_id = os.getenv("HANDSFREE_APNS_TEAM_ID", "")
        key_id = os.getenv("HANDSFREE_APNS_KEY_ID", "")
        key_path = os.getenv("HANDSFREE_APNS_KEY_PATH", "")
        bundle_id = os.getenv("HANDSFREE_APNS_BUNDLE_ID", "")
        use_sandbox = os.getenv("HANDSFREE_APNS_USE_SANDBOX", "false").lower() == "true"

        if not team_id or not key_id or not key_path or not bundle_id:
            logger.warning(
                "APNS credentials not configured. "
                "Required: HANDSFREE_APNS_TEAM_ID, HANDSFREE_APNS_KEY_ID, "
                "HANDSFREE_APNS_KEY_PATH, HANDSFREE_APNS_BUNDLE_ID"
            )
            return None

        return APNSProvider(
            team_id=team_id,
            key_id=key_id,
            key_path=key_path,
            bundle_id=bundle_id,
            use_sandbox=use_sandbox,
        )

    if platform == "fcm":
        project_id = os.getenv("HANDSFREE_FCM_PROJECT_ID", "")
        credentials_path = os.getenv("HANDSFREE_FCM_CREDENTIALS_PATH", "")

        if not project_id or not credentials_path:
            logger.warning(
                "FCM credentials not configured. "
                "Required: HANDSFREE_FCM_PROJECT_ID, HANDSFREE_FCM_CREDENTIALS_PATH"
            )
            return None

        return FCMProvider(
            project_id=project_id,
            credentials_path=credentials_path,
        )

    logger.warning("Unknown platform: %s", platform)
    return None
