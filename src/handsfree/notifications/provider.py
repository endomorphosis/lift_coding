"""Notification delivery provider abstraction.

This module defines the interface for push notification providers and includes
a development logger provider for testing.
"""

import logging
import os
import time
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
    """Apple Push Notification Service (APNS) provider.

    By default this provider runs in "stub" mode to keep local development and
    tests deterministic.

    Enable real sends by constructing with mode="real" (or setting
    HANDSFREE_APNS_MODE=real when using get_provider_for_platform()).
    """

    def __init__(
        self,
        team_id: str,
        key_id: str,
        key_path: str,
        bundle_id: str,
        use_sandbox: bool = False,
        mode: str = "stub",
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
        self.mode = mode

        self._cached_jwt: str | None = None
        self._cached_jwt_issued_at: int | None = None

        logger.info(
            "APNSProvider initialized (mode=%s) - team_id=%s, bundle_id=%s, sandbox=%s",
            mode,
            team_id,
            bundle_id,
            use_sandbox,
        )

    def _apns_host(self) -> str:
        return "api.sandbox.push.apple.com" if self.use_sandbox else "api.push.apple.com"

    def _load_private_key_pem(self) -> str:
        with open(self.key_path, encoding="utf-8") as f:
            return f.read()

    def _get_bearer_token(self) -> str:
        """Get (and cache) the APNS JWT used for Authorization.

        APNS provider tokens are valid for up to 60 minutes; we rotate them
        proactively after ~50 minutes.
        """
        now = int(time.time())
        if self._cached_jwt and self._cached_jwt_issued_at:
            if now - self._cached_jwt_issued_at < 50 * 60:
                return self._cached_jwt

        try:
            import jwt  # PyJWT
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("PyJWT is required for APNS real mode") from e

        private_key_pem = self._load_private_key_pem()
        token = jwt.encode(
            {"iss": self.team_id, "iat": now},
            private_key_pem,
            algorithm="ES256",
            headers={"kid": self.key_id},
        )

        self._cached_jwt = token
        self._cached_jwt_issued_at = now
        return token

    def send(
        self,
        subscription_endpoint: str,
        notification_data: dict[str, Any],
        subscription_keys: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send an APNS notification.

        In "stub" mode this logs and returns success without sending.
        In "real" mode this calls the APNS HTTP/2 API.

        Args:
            subscription_endpoint: The device token.
            notification_data: The notification payload to send.
            subscription_keys: Optional APNS-specific keys (unused in stub).

        Returns:
            Dictionary with delivery result (stub returns success).
        """
        token_preview = subscription_endpoint[:10] + "..." if subscription_endpoint else "<empty>"

        if self.mode != "real":
            logger.info(
                "APNSProvider (stub): Would send notification to device token %s: %s",
                token_preview,
                notification_data,
            )
            return {
                "ok": True,
                "message": "APNS notification logged (stub mode)",
                "delivery_id": f"apns-stub-{hash((subscription_endpoint, str(notification_data)))}",
            }

        try:
            import httpx

            bearer = self._get_bearer_token()

            title = str(
                notification_data.get("title") or notification_data.get("event_type") or "Handsfree"
            )
            body = str(notification_data.get("message") or "")

            payload: dict[str, Any] = {
                "aps": {
                    "alert": {"title": title, "body": body},
                    "sound": "default",
                },
                "data": notification_data,
            }

            url = f"https://{self._apns_host()}/3/device/{subscription_endpoint}"
            headers = {
                "authorization": f"bearer {bearer}",
                "apns-topic": self.bundle_id,
                "apns-push-type": "alert",
                "apns-priority": "10",
            }

            try:
                with httpx.Client(http2=True, timeout=10.0) as client:
                    resp = client.post(url, json=payload, headers=headers)
            except ImportError as e:
                # httpx HTTP/2 requires the optional 'h2' dependency.
                logger.error("APNS real mode requires httpx[http2] (h2). %s", e)
                return {
                    "ok": False,
                    "message": "APNS requires HTTP/2 support (install 'h2')",
                    "delivery_id": None,
                }

            if 200 <= resp.status_code < 300:
                apns_id = resp.headers.get("apns-id")
                return {
                    "ok": True,
                    "message": f"APNS sent (status: {resp.status_code})",
                    "delivery_id": apns_id
                    or f"apns-{hash((subscription_endpoint, str(notification_data)))}",
                }

            reason = None
            try:
                reason = resp.json().get("reason")
            except Exception:
                reason = resp.text

            logger.warning(
                "APNS send failed (status=%s, reason=%s) for token %s",
                resp.status_code,
                reason,
                token_preview,
            )
            return {
                "ok": False,
                "message": f"APNS error ({resp.status_code}): {reason}",
                "delivery_id": None,
            }

        except Exception as e:
            logger.error(
                "Unexpected error sending APNS to %s: %s", token_preview, str(e), exc_info=True
            )
            return {"ok": False, "message": f"Unexpected error: {str(e)}", "delivery_id": None}


class FCMProvider(NotificationDeliveryProvider):
    """Firebase Cloud Messaging (FCM) provider.

    By default this provider runs in "stub" mode.
    Enable real sends with mode="real" (or HANDSFREE_FCM_MODE=real).

    Real mode uses a service account JSON and performs the OAuth2 JWT Bearer
    flow to obtain an access token, then sends via FCM HTTP v1.
    """

    def __init__(
        self,
        project_id: str,
        credentials_path: str,
        mode: str = "stub",
    ):
        """Initialize FCM provider with credentials.

        Args:
            project_id: Firebase project ID.
            credentials_path: Path to the service account JSON credentials file.
        """
        self.project_id = project_id
        self.credentials_path = credentials_path
        self.mode = mode

        self._cached_access_token: str | None = None
        self._cached_access_token_exp: int | None = None

        logger.info(
            "FCMProvider initialized (mode=%s) - project_id=%s",
            mode,
            project_id,
        )

    def _load_service_account(self) -> dict[str, Any]:
        import json

        with open(self.credentials_path, encoding="utf-8") as f:
            return json.load(f)

    def _get_access_token(self) -> tuple[str, int]:
        """Get (and cache) an OAuth2 access token for FCM."""
        now = int(time.time())
        if self._cached_access_token and self._cached_access_token_exp:
            # Refresh ~2 minutes before expiry.
            if now < self._cached_access_token_exp - 120:
                return self._cached_access_token, self._cached_access_token_exp

        try:
            import jwt  # PyJWT
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("PyJWT is required for FCM real mode") from e

        import httpx

        service_account = self._load_service_account()
        token_uri = str(service_account.get("token_uri") or "https://oauth2.googleapis.com/token")
        client_email = str(service_account["client_email"])
        private_key = str(service_account["private_key"])
        scope = "https://www.googleapis.com/auth/firebase.messaging"

        assertion = jwt.encode(
            {
                "iss": client_email,
                "scope": scope,
                "aud": token_uri,
                "iat": now,
                "exp": now + 3600,
            },
            private_key,
            algorithm="RS256",
        )

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                token_uri,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": assertion,
                },
                headers={"content-type": "application/x-www-form-urlencoded"},
            )

        if resp.status_code != 200:
            raise RuntimeError(f"Failed to obtain OAuth token: {resp.status_code} {resp.text}")

        payload = resp.json()
        access_token = str(payload["access_token"])
        expires_in = int(payload.get("expires_in", 3600))
        exp = now + expires_in

        self._cached_access_token = access_token
        self._cached_access_token_exp = exp
        return access_token, exp

    def send(
        self,
        subscription_endpoint: str,
        notification_data: dict[str, Any],
        subscription_keys: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send an FCM notification.

        In "stub" mode this logs and returns success without sending.
        In "real" mode this calls FCM HTTP v1.

        Args:
            subscription_endpoint: The FCM registration token.
            notification_data: The notification payload to send.
            subscription_keys: Optional FCM-specific keys (unused in stub).

        Returns:
            Dictionary with delivery result (stub returns success).
        """
        token_preview = subscription_endpoint[:10] + "..." if subscription_endpoint else "<empty>"
        if self.mode != "real":
            logger.info(
                "FCMProvider (stub): Would send notification to FCM token %s: %s",
                token_preview,
                notification_data,
            )
            return {
                "ok": True,
                "message": "FCM notification logged (stub mode)",
                "delivery_id": f"fcm-stub-{hash((subscription_endpoint, str(notification_data)))}",
            }

        try:
            import httpx

            access_token, _exp = self._get_access_token()

            title = str(
                notification_data.get("title") or notification_data.get("event_type") or "Handsfree"
            )
            body = str(notification_data.get("message") or "")

            url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
            payload = {
                "message": {
                    "token": subscription_endpoint,
                    "notification": {"title": title, "body": body},
                    "data": {k: str(v) for k, v in notification_data.items()},
                }
            }

            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    url,
                    json=payload,
                    headers={"authorization": f"Bearer {access_token}"},
                )

            if 200 <= resp.status_code < 300:
                name = None
                try:
                    name = resp.json().get("name")
                except Exception:
                    name = None
                return {
                    "ok": True,
                    "message": f"FCM sent (status: {resp.status_code})",
                    "delivery_id": name
                    or f"fcm-{hash((subscription_endpoint, str(notification_data)))}",
                }

            logger.warning(
                "FCM send failed (status=%s) for token %s: %s",
                resp.status_code,
                token_preview,
                resp.text,
            )
            return {
                "ok": False,
                "message": f"FCM error ({resp.status_code}): {resp.text}",
                "delivery_id": None,
            }

        except Exception as e:
            logger.error(
                "Unexpected error sending FCM to %s: %s", token_preview, str(e), exc_info=True
            )
            return {"ok": False, "message": f"Unexpected error: {str(e)}", "delivery_id": None}


class ExpoPushProvider(NotificationDeliveryProvider):
    """Expo Push Notification Service provider.

    By default this provider runs in "stub" mode for local development.
    Enable real sends with mode="real" (or HANDSFREE_EXPO_MODE=real).

    Real mode sends notifications via Expo's Push API.
    Expo push tokens look like: ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]
    """

    def __init__(
        self,
        access_token: str | None = None,
        mode: str = "stub",
    ):
        """Initialize Expo Push provider.

        Args:
            access_token: Optional Expo access token for higher rate limits.
            mode: "stub" or "real" mode.
        """
        self.access_token = access_token
        self.mode = mode

        logger.info(
            "ExpoPushProvider initialized (mode=%s) - access_token=%s",
            mode,
            "configured" if access_token else "not configured",
        )

    def send(
        self,
        subscription_endpoint: str,
        notification_data: dict[str, Any],
        subscription_keys: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send an Expo Push notification.

        In "stub" mode this logs and returns success without sending.
        In "real" mode this calls the Expo Push API.

        Args:
            subscription_endpoint: The Expo push token (ExponentPushToken[...]).
            notification_data: The notification payload to send.
            subscription_keys: Optional keys (unused for Expo).

        Returns:
            Dictionary with delivery result (stub returns success).
        """
        token_preview = subscription_endpoint[:20] + "..." if len(subscription_endpoint) > 20 else subscription_endpoint

        if self.mode != "real":
            logger.info(
                "ExpoPushProvider (stub): Would send notification to Expo token %s: %s",
                token_preview,
                notification_data,
            )
            return {
                "ok": True,
                "message": "Expo notification logged (stub mode)",
                "delivery_id": f"expo-stub-{hash((subscription_endpoint, str(notification_data)))}",
            }

        try:
            import httpx

            title = str(
                notification_data.get("title") or notification_data.get("event_type") or "Handsfree"
            )
            body = str(notification_data.get("message") or "")

            # Prepare Expo push message
            # https://docs.expo.dev/push-notifications/sending-notifications/
            message = {
                "to": subscription_endpoint,
                "title": title,
                "body": body,
                "data": notification_data,
                "sound": "default",
                "priority": "high",
            }

            # Expo Push API endpoint
            url = "https://exp.host/--/api/v2/push/send"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            # Add access token if configured (for higher rate limits)
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"

            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, json=message, headers=headers)

            if 200 <= resp.status_code < 300:
                # Parse response
                try:
                    result = resp.json()
                    data = result.get("data", {})
                    
                    # Check if the push ticket indicates success
                    status = data.get("status")
                    if status == "ok":
                        ticket_id = data.get("id", "")
                        return {
                            "ok": True,
                            "message": f"Expo notification sent (status: {resp.status_code})",
                            "delivery_id": ticket_id or f"expo-{hash((subscription_endpoint, str(notification_data)))}",
                        }
                    else:
                        # Expo returned an error in the ticket
                        error_message = data.get("message", "Unknown error")
                        error_details = data.get("details", {})
                        logger.warning(
                            "Expo push ticket error for token %s: %s (details: %s)",
                            token_preview,
                            error_message,
                            error_details,
                        )
                        return {
                            "ok": False,
                            "message": f"Expo error: {error_message}",
                            "delivery_id": None,
                        }
                except Exception as e:
                    logger.warning("Failed to parse Expo response for token %s: %s", token_preview, e)
                    return {
                        "ok": True,  # HTTP success, assume sent
                        "message": f"Expo notification sent (status: {resp.status_code})",
                        "delivery_id": f"expo-{hash((subscription_endpoint, str(notification_data)))}",
                    }

            # HTTP error
            logger.warning(
                "Expo send failed (status=%s) for token %s: %s",
                resp.status_code,
                token_preview,
                resp.text,
            )
            return {
                "ok": False,
                "message": f"Expo error ({resp.status_code}): {resp.text}",
                "delivery_id": None,
            }

        except Exception as e:
            logger.error(
                "Unexpected error sending Expo notification to %s: %s",
                token_preview,
                str(e),
                exc_info=True,
            )
            return {"ok": False, "message": f"Unexpected error: {str(e)}", "delivery_id": None}


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

        apns_mode = os.getenv("HANDSFREE_APNS_MODE", "stub").lower()
        return APNSProvider(
            team_id=team_id,
            key_id=key_id,
            key_path=key_path,
            bundle_id=bundle_id,
            use_sandbox=use_sandbox,
            mode=apns_mode,
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

        fcm_mode = os.getenv("HANDSFREE_FCM_MODE", "stub").lower()
        return FCMProvider(
            project_id=project_id,
            credentials_path=credentials_path,
            mode=fcm_mode,
        )

    # Default: push notifications disabled
    return None


def get_provider_for_platform(platform: str) -> NotificationDeliveryProvider | None:
    """Get the appropriate notification provider for a specific platform.

    This function selects the correct provider based on the subscription platform,
    allowing multi-platform push notification support (WebPush, APNS, FCM, Expo).

    Args:
        platform: Platform type ('webpush', 'apns', 'fcm', or 'expo').

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

        apns_mode = os.getenv("HANDSFREE_APNS_MODE", "stub").lower()
        return APNSProvider(
            team_id=team_id,
            key_id=key_id,
            key_path=key_path,
            bundle_id=bundle_id,
            use_sandbox=use_sandbox,
            mode=apns_mode,
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

        fcm_mode = os.getenv("HANDSFREE_FCM_MODE", "stub").lower()
        return FCMProvider(
            project_id=project_id,
            credentials_path=credentials_path,
            mode=fcm_mode,
        )

    if platform == "expo":
        access_token = os.getenv("HANDSFREE_EXPO_ACCESS_TOKEN", "")
        expo_mode = os.getenv("HANDSFREE_EXPO_MODE", "stub").lower()
        
        # Expo access token is optional (used for higher rate limits)
        return ExpoPushProvider(
            access_token=access_token if access_token else None,
            mode=expo_mode,
        )

    logger.warning("Unknown platform: %s", platform)
    return None
