"""Tests for pending actions manager."""

import time
from datetime import UTC, datetime, timedelta

import pytest

from handsfree.commands.pending_actions import PendingAction, PendingActionManager


@pytest.fixture
def manager() -> PendingActionManager:
    """Create a pending actions manager."""
    return PendingActionManager(default_expiry_seconds=60)


class TestPendingActionCreation:
    """Test creating pending actions."""

    def test_create_action(self, manager: PendingActionManager) -> None:
        """Test creating a new pending action."""
        action = manager.create(
            intent_name="pr.request_review",
            entities={"reviewers": ["alice"], "pr_number": 123},
            summary="Request review from alice on PR 123",
        )

        assert action.token is not None
        assert len(action.token) > 20  # Should be a long random token
        assert action.intent_name == "pr.request_review"
        assert action.entities["reviewers"] == ["alice"]
        assert action.summary == "Request review from alice on PR 123"
        assert action.expires_at > datetime.now(UTC)

    def test_create_with_custom_expiry(self, manager: PendingActionManager) -> None:
        """Test creating action with custom expiry time."""
        action = manager.create(
            intent_name="pr.merge",
            entities={"pr_number": 456},
            summary="Merge PR 456",
            expiry_seconds=120,
        )

        # Should expire in ~120 seconds
        time_until_expiry = (action.expires_at - datetime.now(UTC)).total_seconds()
        assert 115 < time_until_expiry < 125

    def test_create_with_user_id(self, manager: PendingActionManager) -> None:
        """Test creating action with user ID."""
        action = manager.create(
            intent_name="pr.merge",
            entities={},
            summary="Test",
            user_id="user123",
        )

        assert action.user_id == "user123"

    def test_unique_tokens(self, manager: PendingActionManager) -> None:
        """Test that each action gets a unique token."""
        action1 = manager.create("intent1", {}, "summary1")
        action2 = manager.create("intent2", {}, "summary2")

        assert action1.token != action2.token


class TestPendingActionRetrieval:
    """Test retrieving pending actions."""

    def test_get_existing_action(self, manager: PendingActionManager) -> None:
        """Test retrieving an existing action."""
        created = manager.create("test.intent", {"key": "value"}, "Test action")
        retrieved = manager.get(created.token)

        assert retrieved is not None
        assert retrieved.token == created.token
        assert retrieved.intent_name == "test.intent"
        assert retrieved.entities["key"] == "value"

    def test_get_nonexistent_action(self, manager: PendingActionManager) -> None:
        """Test retrieving a non-existent action."""
        result = manager.get("nonexistent-token")
        assert result is None

    def test_get_expired_action(self, manager: PendingActionManager) -> None:
        """Test that expired actions are cleaned up on get."""
        # Create action that expires immediately
        action = manager.create(
            "test.intent",
            {},
            "Test",
            expiry_seconds=1,
        )

        # Wait for expiry
        time.sleep(1.5)

        # Should return None and clean up
        result = manager.get(action.token)
        assert result is None

        # Should no longer be in storage
        result = manager.get(action.token)
        assert result is None


class TestPendingActionConfirmation:
    """Test confirming pending actions."""

    def test_confirm_action(self, manager: PendingActionManager) -> None:
        """Test confirming a pending action."""
        created = manager.create("test.intent", {"data": "value"}, "Test action")
        confirmed = manager.confirm(created.token)

        assert confirmed is not None
        assert confirmed.token == created.token
        assert confirmed.intent_name == "test.intent"

        # Action should be removed after confirmation
        result = manager.get(created.token)
        assert result is None

    def test_confirm_nonexistent(self, manager: PendingActionManager) -> None:
        """Test confirming a non-existent action."""
        result = manager.confirm("nonexistent-token")
        assert result is None

    def test_confirm_expired(self, manager: PendingActionManager) -> None:
        """Test confirming an expired action."""
        action = manager.create("test.intent", {}, "Test", expiry_seconds=1)
        time.sleep(1.5)

        result = manager.confirm(action.token)
        assert result is None


class TestPendingActionCancellation:
    """Test cancelling pending actions."""

    def test_cancel_action(self, manager: PendingActionManager) -> None:
        """Test cancelling a pending action."""
        created = manager.create("test.intent", {}, "Test action")
        result = manager.cancel(created.token)

        assert result is True

        # Action should be removed
        retrieved = manager.get(created.token)
        assert retrieved is None

    def test_cancel_nonexistent(self, manager: PendingActionManager) -> None:
        """Test cancelling a non-existent action."""
        result = manager.cancel("nonexistent-token")
        assert result is False

    def test_cancel_expired(self, manager: PendingActionManager) -> None:
        """Test cancelling an expired action."""
        action = manager.create("test.intent", {}, "Test", expiry_seconds=1)
        time.sleep(1.5)

        result = manager.cancel(action.token)
        assert result is False


class TestPendingActionCleanup:
    """Test cleanup of expired actions."""

    def test_cleanup_expired(self, manager: PendingActionManager) -> None:
        """Test manual cleanup of expired actions."""
        # Create some actions with different expiry times
        action1 = manager.create("test1", {}, "Test1", expiry_seconds=1)
        action2 = manager.create("test2", {}, "Test2", expiry_seconds=5)
        action3 = manager.create("test3", {}, "Test3", expiry_seconds=1)

        # Wait for some to expire
        time.sleep(1.5)

        # Run cleanup
        removed_count = manager.cleanup_expired()
        assert removed_count == 2

        # Non-expired should still exist
        assert manager.get(action2.token) is not None

        # Expired should be gone
        assert manager.get(action1.token) is None
        assert manager.get(action3.token) is None

    def test_cleanup_none_expired(self, manager: PendingActionManager) -> None:
        """Test cleanup when no actions are expired."""
        manager.create("test1", {}, "Test1", expiry_seconds=10)
        manager.create("test2", {}, "Test2", expiry_seconds=10)

        removed_count = manager.cleanup_expired()
        assert removed_count == 0


class TestPendingActionIsExpired:
    """Test the is_expired method on PendingAction."""

    def test_not_expired(self) -> None:
        """Test action that is not expired."""
        action = PendingAction(
            token="test-token",
            intent_name="test",
            entities={},
            summary="Test",
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
        )

        assert not action.is_expired()

    def test_is_expired(self) -> None:
        """Test action that is expired."""
        action = PendingAction(
            token="test-token",
            intent_name="test",
            entities={},
            summary="Test",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )

        assert action.is_expired()


class TestPendingActionToDict:
    """Test conversion of PendingAction to dict."""

    def test_to_dict(self) -> None:
        """Test converting action to dictionary."""
        expires_at = datetime.now(UTC) + timedelta(seconds=60)
        action = PendingAction(
            token="test-token-123",
            intent_name="test.intent",
            entities={"key": "value"},
            summary="Test summary",
            expires_at=expires_at,
        )

        result = action.to_dict()

        assert result["token"] == "test-token-123"
        assert result["summary"] == "Test summary"
        assert result["expires_at"] == expires_at.isoformat()
