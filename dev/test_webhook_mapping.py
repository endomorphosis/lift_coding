#!/usr/bin/env python3
"""Manual test script demonstrating webhook user mapping.

This script shows how to:
1. Set up user subscriptions
2. Send webhooks with dev signature
3. Verify notifications are routed correctly

Run from repository root:
    python3 dev/test_webhook_mapping.py
"""

import json
import uuid
from datetime import UTC, datetime

from handsfree.api import get_db
from handsfree.db.github_connections import create_github_connection
from handsfree.db.notifications import list_notifications
from handsfree.db.repo_subscriptions import create_repo_subscription


def main():
    """Run manual webhook mapping test."""
    print("=" * 70)
    print("Manual Test: Webhook User Mapping")
    print("=" * 70)

    # Initialize database
    db = get_db()
    print("\n✓ Database initialized")

    # Create test users
    user1_id = str(uuid.uuid4())
    user2_id = str(uuid.uuid4())
    print(f"\n✓ Created test users:")
    print(f"  User 1: {user1_id}")
    print(f"  User 2: {user2_id}")

    # Set up subscriptions
    print("\n📝 Setting up subscriptions...")

    # User 1 subscribes to testorg/testrepo by repo name
    create_repo_subscription(db, user1_id, "testorg/testrepo")
    print(f"  ✓ User 1 subscribed to testorg/testrepo")

    # User 2 connects via GitHub App installation
    installation_id = 12345
    create_github_connection(db, user2_id, installation_id=installation_id)
    print(f"  ✓ User 2 connected via installation {installation_id}")

    # Clear any existing notifications
    db.execute("DELETE FROM notifications")
    print("\n✓ Cleared existing notifications")

    # Test 1: Webhook with repo subscription
    print("\n" + "=" * 70)
    print("Test 1: Webhook routed by repository subscription")
    print("=" * 70)

    from handsfree.webhooks import normalize_github_event
    from handsfree.api import _emit_webhook_notification

    payload1 = {
        "action": "opened",
        "pull_request": {
            "number": 123,
            "title": "Test PR",
            "state": "open",
            "merged": False,
            "html_url": "https://github.com/testorg/testrepo/pull/123",
            "user": {"login": "testuser"},
            "base": {"ref": "main"},
            "head": {"ref": "feature", "sha": "abc123"},
        },
        "repository": {"full_name": "testorg/testrepo"},
    }

    normalized1 = normalize_github_event("pull_request", payload1)
    _emit_webhook_notification(normalized1, payload1)

    # Check User 1's notifications
    user1_notifs = list_notifications(db, user1_id)
    print(f"\nUser 1 notifications: {len(user1_notifs)}")
    if user1_notifs:
        for notif in user1_notifs:
            print(f"  • {notif.event_type}: {notif.message}")

    # Check User 2's notifications (should be empty)
    user2_notifs = list_notifications(db, user2_id)
    print(f"\nUser 2 notifications: {len(user2_notifs)}")
    if user2_notifs:
        for notif in user2_notifs:
            print(f"  • {notif.event_type}: {notif.message}")

    assert len(user1_notifs) == 1, "User 1 should have 1 notification"
    assert len(user2_notifs) == 0, "User 2 should have 0 notifications"
    print("\n✓ Test 1 passed: Webhook correctly routed to User 1")

    # Clear notifications
    db.execute("DELETE FROM notifications")

    # Test 2: Webhook with installation_id
    print("\n" + "=" * 70)
    print("Test 2: Webhook routed by installation_id")
    print("=" * 70)

    payload2 = {
        "action": "opened",
        "pull_request": {
            "number": 456,
            "title": "Another PR",
            "state": "open",
            "merged": False,
            "html_url": "https://github.com/testorg/testrepo/pull/456",
            "user": {"login": "testuser"},
            "base": {"ref": "main"},
            "head": {"ref": "another-feature", "sha": "def456"},
        },
        "repository": {"full_name": "testorg/testrepo"},
        "installation": {"id": installation_id},
    }

    normalized2 = normalize_github_event("pull_request", payload2)
    _emit_webhook_notification(normalized2, payload2)

    # Check notifications
    user1_notifs = list_notifications(db, user1_id)
    user2_notifs = list_notifications(db, user2_id)

    print(f"\nUser 1 notifications: {len(user1_notifs)}")
    for notif in user1_notifs:
        print(f"  • {notif.event_type}: {notif.message}")

    print(f"\nUser 2 notifications: {len(user2_notifs)}")
    for notif in user2_notifs:
        print(f"  • {notif.event_type}: {notif.message}")

    # Both users should get it (User 1 by repo, User 2 by installation)
    assert len(user1_notifs) == 1, "User 1 should have 1 notification"
    assert len(user2_notifs) == 1, "User 2 should have 1 notification"
    print("\n✓ Test 2 passed: Webhook routed to both users correctly")

    # Clear notifications
    db.execute("DELETE FROM notifications")

    # Test 3: Webhook with no subscription
    print("\n" + "=" * 70)
    print("Test 3: Webhook with no subscription (should be no-op)")
    print("=" * 70)

    payload3 = {
        "action": "opened",
        "pull_request": {
            "number": 789,
            "title": "Unsubscribed PR",
            "state": "open",
            "merged": False,
            "html_url": "https://github.com/unknown/repo/pull/789",
            "user": {"login": "testuser"},
            "base": {"ref": "main"},
            "head": {"ref": "feature", "sha": "xyz789"},
        },
        "repository": {"full_name": "unknown/repo"},
    }

    normalized3 = normalize_github_event("pull_request", payload3)
    _emit_webhook_notification(normalized3, payload3)

    # Check notifications (should be zero for both users)
    user1_notifs = list_notifications(db, user1_id)
    user2_notifs = list_notifications(db, user2_id)

    print(f"\nUser 1 notifications: {len(user1_notifs)}")
    print(f"User 2 notifications: {len(user2_notifs)}")

    assert len(user1_notifs) == 0, "User 1 should have 0 notifications"
    assert len(user2_notifs) == 0, "User 2 should have 0 notifications"
    print("\n✓ Test 3 passed: No notifications created for unsubscribed repo")

    # Summary
    print("\n" + "=" * 70)
    print("All tests passed! ✓")
    print("=" * 70)
    print("\nWebhook user mapping is working correctly:")
    print("  ✓ Webhooks routed by repository subscription")
    print("  ✓ Webhooks routed by installation_id")
    print("  ✓ Multiple users can receive the same webhook")
    print("  ✓ Unsubscribed repos result in no-op (no notifications)")


if __name__ == "__main__":
    main()
