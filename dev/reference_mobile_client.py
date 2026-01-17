#!/usr/bin/env python3
"""
Reference Mobile Client for HandsFree Dev Companion

This script demonstrates the complete mobile client integration flow:
1. Register APNS/FCM push notification subscription
2. Submit a text command
3. Handle confirmation flow
4. Poll for notifications
5. Fetch TTS audio

Usage:
    python dev/reference_mobile_client.py

Environment variables:
    HANDSFREE_API_URL: Backend API URL (default: http://localhost:8080)
    HANDSFREE_USER_ID: User ID for authentication (default: test user)
"""

import json
import os
import sys
import time
import uuid
from typing import Any

# Try to import requests, provide helpful error if missing
try:
    import requests
except ImportError:
    print("Error: requests library not installed")
    print("Install it with: pip install requests")
    sys.exit(1)


class HandsFreeClient:
    """Reference client for HandsFree Dev Companion API."""

    def __init__(self, base_url: str, user_id: str):
        self.base_url = base_url.rstrip("/")
        self.user_id = user_id
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-User-ID": user_id,
                "Content-Type": "application/json",
            }
        )

    def _print_section(self, title: str) -> None:
        """Print a formatted section header."""
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}\n")

    def _print_response(self, response: requests.Response) -> None:
        """Print response details."""
        print(f"Status: {response.status_code}")
        try:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        except Exception:
            print(f"Response: {response.text[:500]}")

    def check_status(self) -> dict[str, Any]:
        """Check if the backend is running."""
        self._print_section("1. Checking Backend Status")
        try:
            response = self.session.get(f"{self.base_url}/v1/status")
            self._print_response(response)
            return response.json() if response.ok else {}
        except requests.exceptions.RequestException as e:
            print(f"Error: Cannot connect to backend at {self.base_url}")
            print(f"Details: {e}")
            print("\nMake sure the backend is running:")
            print("  cd /path/to/lift_coding")
            print("  make run")
            return {}

    def register_push_subscription(self, platform: str = "fcm") -> dict[str, Any] | None:
        """Register a push notification subscription."""
        self._print_section(f"2. Registering {platform.upper()} Push Subscription")

        # Generate a fake device token (in real app, this comes from APNS/FCM)
        if platform == "apns":
            # APNS tokens are hex strings
            device_token = "a1b2c3d4e5f6" + uuid.uuid4().hex[:52]
        else:
            # FCM tokens are longer
            device_token = "fcm-token-" + uuid.uuid4().hex

        payload = {
            "endpoint": device_token,
            "platform": platform,
        }

        # WebPush requires subscription_keys, but mobile platforms don't
        if platform == "webpush":
            payload["subscription_keys"] = {
                "auth": "auth-secret-" + uuid.uuid4().hex[:16],
                "p256dh": "public-key-" + uuid.uuid4().hex[:16],
            }

        print(f"Request payload:\n{json.dumps(payload, indent=2)}\n")

        try:
            response = self.session.post(
                f"{self.base_url}/v1/notifications/subscriptions",
                json=payload,
            )
            self._print_response(response)

            if response.ok:
                return response.json()
            else:
                print(f"Failed to register subscription: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error registering subscription: {e}")
            return None

    def send_command(self, text: str, profile: str = "terse") -> dict[str, Any] | None:
        """Send a text command to the backend."""
        self._print_section(f"3. Sending Command: '{text}'")

        payload = {
            "input": {
                "type": "text",
                "text": text,
            },
            "profile": profile,
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
            "idempotency_key": f"cmd-{uuid.uuid4().hex}",
        }

        print(f"Request payload:\n{json.dumps(payload, indent=2)}\n")

        try:
            response = self.session.post(
                f"{self.base_url}/v1/command",
                json=payload,
            )
            self._print_response(response)

            if response.ok:
                return response.json()
            else:
                print(f"Failed to send command: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error sending command: {e}")
            return None

    def confirm_action(self, token: str) -> dict[str, Any] | None:
        """Confirm a pending action."""
        self._print_section(f"4. Confirming Action (token: {token})")

        payload = {
            "token": token,
            "idempotency_key": f"confirm-{uuid.uuid4().hex}",
        }

        print(f"Request payload:\n{json.dumps(payload, indent=2)}\n")

        try:
            response = self.session.post(
                f"{self.base_url}/v1/commands/confirm",
                json=payload,
            )
            self._print_response(response)

            if response.ok:
                return response.json()
            else:
                print(f"Failed to confirm action: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error confirming action: {e}")
            return None

    def poll_notifications(
        self, since: str | None = None, limit: int = 10
    ) -> dict[str, Any] | None:
        """Poll for notifications."""
        self._print_section("5. Polling Notifications")

        params = {"limit": limit}
        if since:
            params["since"] = since

        print(f"Request params: {params}\n")

        try:
            response = self.session.get(
                f"{self.base_url}/v1/notifications",
                params=params,
            )
            self._print_response(response)

            if response.ok:
                return response.json()
            else:
                print(f"Failed to poll notifications: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error polling notifications: {e}")
            return None

    def fetch_tts(self, text: str, format: str = "mp3") -> bytes | None:
        """Fetch TTS audio for text."""
        self._print_section(f"6. Fetching TTS Audio: '{text}'")

        payload = {
            "text": text,
            "format": format,
        }

        print(f"Request payload:\n{json.dumps(payload, indent=2)}\n")

        try:
            response = self.session.post(
                f"{self.base_url}/v1/tts",
                json=payload,
            )

            print(f"Status: {response.status_code}")

            if response.ok:
                audio_data = response.content
                print(f"Received {len(audio_data)} bytes of audio data")
                print(f"Content-Type: {response.headers.get('Content-Type')}")

                # Save to file for inspection
                output_file = f"tts_output_{int(time.time())}.{format}"
                with open(output_file, "wb") as f:
                    f.write(audio_data)
                print(f"Saved audio to: {output_file}")

                return audio_data
            else:
                print(f"Failed to fetch TTS: {response.status_code}")
                self._print_response(response)
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching TTS: {e}")
            return None

    def list_subscriptions(self) -> dict[str, Any] | None:
        """List all push notification subscriptions."""
        self._print_section("7. Listing Push Subscriptions")

        try:
            response = self.session.get(
                f"{self.base_url}/v1/notifications/subscriptions"
            )
            self._print_response(response)

            if response.ok:
                return response.json()
            else:
                print(f"Failed to list subscriptions: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error listing subscriptions: {e}")
            return None

    def delete_subscription(self, subscription_id: str) -> bool:
        """Delete a push notification subscription."""
        self._print_section(f"8. Deleting Subscription: {subscription_id}")

        try:
            response = self.session.delete(
                f"{self.base_url}/v1/notifications/subscriptions/{subscription_id}"
            )

            print(f"Status: {response.status_code}")

            if response.status_code == 204:
                print("Subscription deleted successfully")
                return True
            else:
                print(f"Failed to delete subscription: {response.status_code}")
                self._print_response(response)
                return False
        except requests.exceptions.RequestException as e:
            print(f"Error deleting subscription: {e}")
            return False


def demo_basic_flow(client: HandsFreeClient) -> None:
    """Demonstrate the basic command flow."""
    print("\n" + "=" * 60)
    print("  DEMO: Basic Command Flow")
    print("=" * 60)

    # 1. Check status
    status = client.check_status()
    if not status:
        print("\n❌ Backend is not running. Exiting.")
        return

    # 2. Register push subscription (FCM)
    subscription = client.register_push_subscription(platform="fcm")

    # 3. Send a simple command
    response = client.send_command("show my inbox")

    # 4. Check if there's a pending action requiring confirmation
    if response and response.get("pending_action"):
        pending = response["pending_action"]
        print(f"\n⚠️  Action requires confirmation: {pending.get('summary')}")
        print(f"Token: {pending.get('token')}")
        print(f"Expires at: {pending.get('expires_at')}")

        # Auto-confirm for demo purposes
        time.sleep(1)
        confirm_response = client.confirm_action(pending["token"])
        if confirm_response:
            print("\n✅ Action confirmed and executed")

    # 5. Poll for notifications
    notifications = client.poll_notifications(limit=5)
    if notifications:
        count = notifications.get("count", 0)
        print(f"\n📬 Found {count} notification(s)")

    # 6. Fetch TTS audio
    if response and response.get("response"):
        response_text = response["response"].get("text", "Hello, developer!")
        client.fetch_tts(response_text[:100])  # Limit text length

    # 7. List subscriptions
    subscriptions = client.list_subscriptions()
    if subscriptions and subscriptions.get("subscriptions"):
        print(f"\n📱 Active subscriptions: {len(subscriptions['subscriptions'])}")

    # 8. Clean up: delete subscription
    if subscription and subscription.get("id"):
        time.sleep(1)
        client.delete_subscription(subscription["id"])


def demo_confirmation_flow(client: HandsFreeClient) -> None:
    """Demonstrate the confirmation flow with a policy-gated command."""
    print("\n" + "=" * 60)
    print("  DEMO: Confirmation Flow")
    print("=" * 60)

    # Send a command that typically requires confirmation
    # (e.g., merging a PR, delegating to agent)
    response = client.send_command("merge PR 123")

    if response and response.get("pending_action"):
        pending = response["pending_action"]
        print("\n⚠️  Confirmation required:")
        print(f"  Summary: {pending.get('summary')}")
        print(f"  Token: {pending.get('token')}")
        print(f"  Expires: {pending.get('expires_at')}")

        # Simulate user thinking...
        print("\n  Waiting 2 seconds before confirming...")
        time.sleep(2)

        # Confirm the action
        confirm_response = client.confirm_action(pending["token"])
        if confirm_response:
            print("\n✅ Confirmation successful!")
            if confirm_response.get("response"):
                print(f"  Response: {confirm_response['response'].get('text')}")
    else:
        print("\n  This command did not require confirmation (or failed)")


def demo_push_platforms(client: HandsFreeClient) -> None:
    """Demonstrate registering different push notification platforms."""
    print("\n" + "=" * 60)
    print("  DEMO: Push Notification Platforms")
    print("=" * 60)

    platforms = ["apns", "fcm"]
    subscription_ids = []

    for platform in platforms:
        subscription = client.register_push_subscription(platform=platform)
        if subscription and subscription.get("id"):
            subscription_ids.append(subscription["id"])
            time.sleep(0.5)

    # List all subscriptions
    subscriptions = client.list_subscriptions()
    if subscriptions:
        print(f"\n📱 Total active subscriptions: {len(subscriptions.get('subscriptions', []))}")

    # Clean up
    for sub_id in subscription_ids:
        time.sleep(0.5)
        client.delete_subscription(sub_id)


def demo_notification_polling(client: HandsFreeClient) -> None:
    """Demonstrate notification polling with timestamp tracking."""
    print("\n" + "=" * 60)
    print("  DEMO: Notification Polling")
    print("=" * 60)

    # Initial poll (no timestamp)
    print("\nInitial poll (all notifications):")
    result = client.poll_notifications(limit=10)

    if result and result.get("notifications"):
        notifications = result["notifications"]
        if notifications:
            # Get the most recent notification timestamp
            latest = notifications[0]["created_at"]
            print(f"\nMost recent notification: {latest}")

            # Simulate waiting and polling again
            print("\nWaiting 2 seconds...")
            time.sleep(2)

            # Poll again with 'since' parameter
            print(f"\nPolling for notifications since {latest}:")
            client.poll_notifications(since=latest, limit=10)
        else:
            print("\n  No notifications found")
    else:
        print("\n  No notifications available")


def main():
    """Main entry point."""
    # Configuration
    base_url = os.environ.get("HANDSFREE_API_URL", "http://localhost:8080")
    user_id = os.environ.get(
        "HANDSFREE_USER_ID", "00000000-0000-0000-0000-000000000001"
    )

    print("=" * 60)
    print("  HandsFree Mobile Client Reference Implementation")
    print("=" * 60)
    print(f"API URL: {base_url}")
    print(f"User ID: {user_id}")
    print("=" * 60)

    # Create client
    client = HandsFreeClient(base_url, user_id)

    # Run demos
    try:
        # Demo 1: Basic flow (all steps)
        demo_basic_flow(client)

        # Demo 2: Confirmation flow
        print("\n\nPress Enter to continue with confirmation flow demo...")
        input()
        demo_confirmation_flow(client)

        # Demo 3: Push platforms
        print("\n\nPress Enter to continue with push platforms demo...")
        input()
        demo_push_platforms(client)

        # Demo 4: Notification polling
        print("\n\nPress Enter to continue with notification polling demo...")
        input()
        demo_notification_polling(client)

        print("\n" + "=" * 60)
        print("  ✅ All demos completed successfully!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
    except Exception as e:
        print(f"\n\n❌ Error during demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
