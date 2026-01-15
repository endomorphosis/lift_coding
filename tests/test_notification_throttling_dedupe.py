"""Tests for notification throttling and deduplication."""

import pytest

from handsfree.db import init_db
from handsfree.db.notifications import (
    create_notification,
    generate_dedupe_key,
    get_event_priority,
    list_notifications,
    should_throttle_notification,
)


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def test_user_id():
    """Generate a consistent test user ID."""
    return "00000000-0000-0000-0000-000000000001"


class TestDedupeKeyGeneration:
    """Test dedupe key generation logic."""

    def test_dedupe_key_same_for_identical_events(self):
        """Test that identical events generate the same dedupe key."""
        metadata1 = {"repo": "owner/repo", "pr_number": 123}
        metadata2 = {"repo": "owner/repo", "pr_number": 123}

        key1 = generate_dedupe_key("webhook.pr_opened", metadata1)
        key2 = generate_dedupe_key("webhook.pr_opened", metadata2)

        assert key1 == key2

    def test_dedupe_key_different_for_different_repos(self):
        """Test that different repos generate different dedupe keys."""
        metadata1 = {"repo": "owner/repo1", "pr_number": 123}
        metadata2 = {"repo": "owner/repo2", "pr_number": 123}

        key1 = generate_dedupe_key("webhook.pr_opened", metadata1)
        key2 = generate_dedupe_key("webhook.pr_opened", metadata2)

        assert key1 != key2

    def test_dedupe_key_different_for_different_pr_numbers(self):
        """Test that different PR numbers generate different dedupe keys."""
        metadata1 = {"repo": "owner/repo", "pr_number": 123}
        metadata2 = {"repo": "owner/repo", "pr_number": 456}

        key1 = generate_dedupe_key("webhook.pr_opened", metadata1)
        key2 = generate_dedupe_key("webhook.pr_opened", metadata2)

        assert key1 != key2

    def test_dedupe_key_different_for_different_event_types(self):
        """Test that different event types generate different dedupe keys."""
        metadata = {"repo": "owner/repo", "pr_number": 123}

        key1 = generate_dedupe_key("webhook.pr_opened", metadata)
        key2 = generate_dedupe_key("webhook.pr_closed", metadata)

        assert key1 != key2

    def test_dedupe_key_handles_no_metadata(self):
        """Test that dedupe key can be generated without metadata."""
        key = generate_dedupe_key("webhook.simple_event", None)
        assert key is not None
        assert len(key) > 0


class TestEventPriority:
    """Test event priority assignment."""

    def test_high_priority_events(self):
        """Test that critical events get priority 5."""
        assert get_event_priority("webhook.pr_merged") == 5
        assert get_event_priority("webhook.deployment_failure") == 5
        assert get_event_priority("webhook.security_alert") == 5
        assert get_event_priority("webhook.check_suite_failure") == 5

    def test_important_priority_events(self):
        """Test that important events get priority 4."""
        assert get_event_priority("webhook.pr_opened") == 4
        assert get_event_priority("webhook.pr_closed") == 4
        assert get_event_priority("webhook.review_requested") == 4

    def test_medium_priority_events(self):
        """Test that medium priority events get priority 3."""
        assert get_event_priority("webhook.pr_synchronize") == 3
        assert get_event_priority("webhook.check_suite_completed") == 3

    def test_low_priority_events(self):
        """Test that low priority events get priority 2."""
        assert get_event_priority("webhook.pr_labeled") == 2
        assert get_event_priority("webhook.issue_comment") == 2

    def test_unknown_events_default_to_medium(self):
        """Test that unknown events default to priority 3."""
        assert get_event_priority("webhook.unknown_event") == 3


class TestThrottling:
    """Test throttling logic."""

    def test_workout_profile_throttles_low_priority(self):
        """Test that workout profile throttles events below priority 4."""
        assert should_throttle_notification(3, "workout") is True
        assert should_throttle_notification(2, "workout") is True
        assert should_throttle_notification(1, "workout") is True
        assert should_throttle_notification(4, "workout") is False
        assert should_throttle_notification(5, "workout") is False

    def test_commute_profile_throttles_low_priority(self):
        """Test that commute profile throttles events below priority 3."""
        assert should_throttle_notification(2, "commute") is True
        assert should_throttle_notification(1, "commute") is True
        assert should_throttle_notification(3, "commute") is False
        assert should_throttle_notification(4, "commute") is False
        assert should_throttle_notification(5, "commute") is False

    def test_kitchen_profile_throttles_very_low_priority(self):
        """Test that kitchen profile throttles events below priority 2."""
        assert should_throttle_notification(1, "kitchen") is True
        assert should_throttle_notification(2, "kitchen") is False
        assert should_throttle_notification(3, "kitchen") is False
        assert should_throttle_notification(4, "kitchen") is False
        assert should_throttle_notification(5, "kitchen") is False

    def test_default_profile_allows_all(self):
        """Test that default profile allows all priority levels."""
        assert should_throttle_notification(1, "default") is False
        assert should_throttle_notification(2, "default") is False
        assert should_throttle_notification(3, "default") is False
        assert should_throttle_notification(4, "default") is False
        assert should_throttle_notification(5, "default") is False


class TestNotificationDeduplication:
    """Test notification deduplication."""

    def test_duplicate_notification_within_window_is_blocked(self, db_conn, test_user_id):
        """Test that duplicate notifications within the dedupe window are blocked."""
        metadata = {"repo": "owner/repo", "pr_number": 123}

        # Create first notification
        notif1 = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_opened",
            message="PR #123 opened",
            metadata=metadata,
        )
        assert notif1 is not None

        # Try to create duplicate immediately
        notif2 = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_opened",
            message="PR #123 opened again",
            metadata=metadata,
        )
        # Should be blocked (None returned)
        assert notif2 is None

        # Verify only one notification exists
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        assert len(notifications) == 1
        assert notifications[0].id == notif1.id

    def test_different_event_types_not_deduplicated(self, db_conn, test_user_id):
        """Test that different event types are not deduplicated."""
        metadata = {"repo": "owner/repo", "pr_number": 123}

        # Create notification for PR opened
        notif1 = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_opened",
            message="PR #123 opened",
            metadata=metadata,
        )
        assert notif1 is not None

        # Create notification for PR closed (different event type)
        notif2 = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_closed",
            message="PR #123 closed",
            metadata=metadata,
        )
        assert notif2 is not None

        # Verify both notifications exist
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        assert len(notifications) == 2

    def test_different_repos_not_deduplicated(self, db_conn, test_user_id):
        """Test that notifications for different repos are not deduplicated."""
        # Create notification for repo1
        notif1 = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_opened",
            message="PR #123 opened in repo1",
            metadata={"repo": "owner/repo1", "pr_number": 123},
        )
        assert notif1 is not None

        # Create notification for repo2
        notif2 = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_opened",
            message="PR #123 opened in repo2",
            metadata={"repo": "owner/repo2", "pr_number": 123},
        )
        assert notif2 is not None

        # Verify both notifications exist
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        assert len(notifications) == 2

    def test_different_pr_numbers_not_deduplicated(self, db_conn, test_user_id):
        """Test that notifications for different PRs are not deduplicated."""
        # Create notification for PR #123
        notif1 = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_opened",
            message="PR #123 opened",
            metadata={"repo": "owner/repo", "pr_number": 123},
        )
        assert notif1 is not None

        # Create notification for PR #456
        notif2 = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_opened",
            message="PR #456 opened",
            metadata={"repo": "owner/repo", "pr_number": 456},
        )
        assert notif2 is not None

        # Verify both notifications exist
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        assert len(notifications) == 2

    def test_dedupe_window_custom_duration(self, db_conn, test_user_id):
        """Test that custom dedupe window works correctly."""
        metadata = {"repo": "owner/repo", "pr_number": 123}

        # Create first notification with short dedupe window (1 second)
        notif1 = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_opened",
            message="PR #123 opened",
            metadata=metadata,
            dedupe_window_seconds=1,
        )
        assert notif1 is not None

        # Immediate duplicate should be blocked
        notif2 = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_opened",
            message="PR #123 opened again",
            metadata=metadata,
            dedupe_window_seconds=1,
        )
        assert notif2 is None


class TestProfileAwareThrottling:
    """Test profile-aware throttling in notification creation."""

    def test_workout_profile_blocks_low_priority(self, db_conn, test_user_id):
        """Test that workout profile blocks low priority notifications."""
        # Low priority event (priority 2)
        notif = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_labeled",
            message="PR labeled",
            metadata={"repo": "owner/repo", "pr_number": 123},
            profile="workout",
        )
        # Should be throttled
        assert notif is None

        # Verify no notification was created
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        assert len(notifications) == 0

    def test_workout_profile_allows_high_priority(self, db_conn, test_user_id):
        """Test that workout profile allows high priority notifications."""
        # High priority event (priority 5)
        notif = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_merged",
            message="PR merged",
            metadata={"repo": "owner/repo", "pr_number": 123},
            profile="workout",
        )
        # Should NOT be throttled
        assert notif is not None

        # Verify notification was created
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        assert len(notifications) == 1

    def test_default_profile_allows_all_priority(self, db_conn, test_user_id):
        """Test that default profile allows all priority levels."""
        # Create low priority notification
        notif1 = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_labeled",
            message="PR labeled",
            metadata={"repo": "owner/repo", "pr_number": 123},
            profile="default",
        )
        assert notif1 is not None

        # Create high priority notification
        notif2 = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_merged",
            message="PR merged",
            metadata={"repo": "owner/repo", "pr_number": 456},
            profile="default",
        )
        assert notif2 is not None

        # Verify both notifications were created
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        assert len(notifications) == 2


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_create_notification_without_profile_parameter(self, db_conn, test_user_id):
        """Test that create_notification works without profile parameter."""
        notif = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="test_event",
            message="Test message",
            metadata={"key": "value"},
        )
        # Should succeed with default profile
        assert notif is not None
        assert notif.profile == "default"
        assert notif.priority == 3  # Default priority for unknown event

    def test_list_notifications_returns_new_fields(self, db_conn, test_user_id):
        """Test that list_notifications includes priority and profile fields."""
        create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_merged",
            message="PR merged",
            metadata={"repo": "owner/repo", "pr_number": 123},
            profile="workout",
        )

        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        assert len(notifications) == 1
        assert notifications[0].priority == 5
        assert notifications[0].profile == "workout"

    def test_notification_to_dict_includes_new_fields(self, db_conn, test_user_id):
        """Test that Notification.to_dict includes priority and profile."""
        notif = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_merged",
            message="PR merged",
            profile="workout",
        )

        notif_dict = notif.to_dict()
        assert "priority" in notif_dict
        assert "profile" in notif_dict
        assert notif_dict["priority"] == 5
        assert notif_dict["profile"] == "workout"


class TestPriorityOverride:
    """Test priority override functionality."""

    def test_priority_override_works(self, db_conn, test_user_id):
        """Test that priority can be manually overridden."""
        # Create notification with manual priority override
        notif = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_labeled",  # Normally priority 2
            message="PR labeled",
            metadata={"repo": "owner/repo", "pr_number": 123},
            priority=5,  # Override to priority 5
        )
        assert notif is not None
        assert notif.priority == 5

    def test_priority_override_affects_throttling(self, db_conn, test_user_id):
        """Test that priority override affects throttling decisions."""
        # Create low priority event with high priority override
        notif = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_labeled",  # Normally priority 2
            message="PR labeled",
            metadata={"repo": "owner/repo", "pr_number": 123},
            profile="workout",  # Would normally block priority 2
            priority=5,  # Override to priority 5 to bypass throttling
        )
        # Should NOT be throttled due to override
        assert notif is not None
        assert notif.priority == 5
