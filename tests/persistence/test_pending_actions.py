"""Tests for pending actions persistence."""

from src.handsfree.persistence import (
    cleanup_expired_actions,
    create_pending_action,
    delete_pending_action,
    get_pending_action,
)


def test_create_and_get_pending_action(db_conn, test_user_id):
    """Test creating and retrieving a pending action."""
    token = create_pending_action(
        db_conn,
        user_id=test_user_id,
        summary="Merge PR #123",
        action_type="merge_pr",
        action_payload={"pr_number": 123, "repo": "owner/repo"},
        expires_in_seconds=3600,
    )

    assert token is not None
    assert len(token) > 0

    # Retrieve the action
    action = get_pending_action(db_conn, token)

    assert action is not None
    assert action["token"] == token
    assert str(action["user_id"]) == str(test_user_id)
    assert action["summary"] == "Merge PR #123"
    assert action["action_type"] == "merge_pr"
    assert action["action_payload"]["pr_number"] == 123
    assert action["action_payload"]["repo"] == "owner/repo"


def test_get_nonexistent_action(db_conn):
    """Test retrieving a nonexistent action returns None."""
    action = get_pending_action(db_conn, "nonexistent_token")
    assert action is None


def test_expired_action_not_returned(db_conn, test_user_id):
    """Test that expired actions are not returned."""
    # Create an action that expires immediately
    token = create_pending_action(
        db_conn,
        user_id=test_user_id,
        summary="Expired action",
        action_type="test",
        action_payload={},
        expires_in_seconds=-1,  # Already expired
    )

    # Try to retrieve it
    action = get_pending_action(db_conn, token)
    assert action is None


def test_delete_pending_action(db_conn, test_user_id):
    """Test deleting a pending action."""
    token = create_pending_action(
        db_conn,
        user_id=test_user_id,
        summary="Test action",
        action_type="test",
        action_payload={},
    )

    # Delete it
    result = delete_pending_action(db_conn, token)
    assert result is True

    # Verify it's gone
    action = get_pending_action(db_conn, token)
    assert action is None

    # Deleting again should return False
    result = delete_pending_action(db_conn, token)
    assert result is False


def test_cleanup_expired_actions(db_conn, test_user_id):
    """Test cleaning up expired actions."""
    # Create some expired actions
    for i in range(3):
        create_pending_action(
            db_conn,
            user_id=test_user_id,
            summary=f"Expired action {i}",
            action_type="test",
            action_payload={},
            expires_in_seconds=-1,
        )

    # Create a valid action
    valid_token = create_pending_action(
        db_conn,
        user_id=test_user_id,
        summary="Valid action",
        action_type="test",
        action_payload={},
        expires_in_seconds=3600,
    )

    # Cleanup expired
    deleted_count = cleanup_expired_actions(db_conn)
    assert deleted_count == 3

    # Valid action should still exist
    action = get_pending_action(db_conn, valid_token)
    assert action is not None


def test_custom_token(db_conn, test_user_id):
    """Test creating an action with a custom token."""
    custom_token = "my-custom-token-123"

    token = create_pending_action(
        db_conn,
        user_id=test_user_id,
        summary="Test",
        action_type="test",
        action_payload={},
        token=custom_token,
    )

    assert token == custom_token

    action = get_pending_action(db_conn, custom_token)
    assert action is not None
