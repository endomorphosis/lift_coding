"""Tests for commands persistence (with privacy toggle)."""

from src.handsfree.persistence import (
    create_command,
    get_commands,
)
from tests.persistence.conftest import create_test_user


def test_create_command_basic(db_conn, test_user_id):
    """Test creating a basic command."""
    command_id = create_command(
        db_conn,
        user_id=test_user_id,
        input_type="text",
        status="ok",
    )

    assert command_id is not None


def test_privacy_toggle_stores_transcript(db_conn, test_user_id):
    """Test that transcript is stored when privacy toggle is True."""
    create_command(
        db_conn,
        user_id=test_user_id,
        input_type="text",
        status="ok",
        transcript="Merge the pull request",
        store_transcript=True,  # Explicitly allow storage
    )

    commands = get_commands(db_conn, user_id=test_user_id)
    assert len(commands) >= 1

    command = commands[0]
    assert command["transcript"] == "Merge the pull request"


def test_privacy_toggle_does_not_store_transcript(db_conn, test_user_id):
    """Test that transcript is NOT stored when privacy toggle is False (default)."""
    create_command(
        db_conn,
        user_id=test_user_id,
        input_type="text",
        status="ok",
        transcript="Sensitive information here",
        store_transcript=False,  # Default: don't store
    )

    commands = get_commands(db_conn, user_id=test_user_id)
    assert len(commands) >= 1

    command = commands[0]
    assert command["transcript"] is None  # Should NOT be stored


def test_default_privacy_behavior(db_conn, test_user_id):
    """Test that default behavior is to NOT store transcript."""
    create_command(
        db_conn,
        user_id=test_user_id,
        input_type="text",
        status="ok",
        transcript="This should not be stored by default",
        # store_transcript not specified - should default to False
    )

    commands = get_commands(db_conn, user_id=test_user_id)
    command = commands[0]
    assert command["transcript"] is None


def test_command_with_intent_and_entities(db_conn, test_user_id):
    """Test storing command with intent and entities."""
    create_command(
        db_conn,
        user_id=test_user_id,
        input_type="text",
        status="ok",
        intent_name="merge_pr",
        intent_confidence=0.95,
        entities={"pr_number": 123, "repo": "owner/repo"},
    )

    commands = get_commands(db_conn, user_id=test_user_id)
    command = commands[0]

    assert command["intent_name"] == "merge_pr"
    assert abs(command["intent_confidence"] - 0.95) < 0.001  # Float comparison with tolerance
    assert command["entities"]["pr_number"] == 123


def test_get_commands_by_user(db_conn):
    """Test filtering commands by user."""
    user_1 = create_test_user(db_conn)
    user_2 = create_test_user(db_conn)

    create_command(db_conn, user_id=user_1, input_type="text", status="ok")
    create_command(db_conn, user_id=user_1, input_type="text", status="ok")
    create_command(db_conn, user_id=user_2, input_type="text", status="ok")

    user_1_commands = get_commands(db_conn, user_id=user_1)
    assert len(user_1_commands) == 2


def test_get_commands_by_profile(db_conn, test_user_id):
    """Test filtering commands by profile."""
    create_command(db_conn, user_id=test_user_id, input_type="text", status="ok", profile="work")
    create_command(db_conn, user_id=test_user_id, input_type="text", status="ok", profile="work")
    create_command(
        db_conn, user_id=test_user_id, input_type="text", status="ok", profile="personal"
    )

    work_commands = get_commands(db_conn, profile="work")
    assert len(work_commands) == 2
    assert all(cmd["profile"] == "work" for cmd in work_commands)


def test_get_commands_by_status(db_conn, test_user_id):
    """Test filtering commands by status."""
    create_command(db_conn, user_id=test_user_id, input_type="text", status="ok")
    create_command(db_conn, user_id=test_user_id, input_type="text", status="needs_confirmation")
    create_command(db_conn, user_id=test_user_id, input_type="text", status="error")

    ok_commands = get_commands(db_conn, status="ok")
    assert len(ok_commands) >= 1

    needs_conf_commands = get_commands(db_conn, status="needs_confirmation")
    assert len(needs_conf_commands) >= 1


def test_commands_ordering(db_conn, test_user_id):
    """Test that commands are returned in reverse chronological order."""
    create_command(
        db_conn, user_id=test_user_id, input_type="text", status="ok", intent_name="first"
    )
    create_command(
        db_conn, user_id=test_user_id, input_type="text", status="ok", intent_name="second"
    )
    create_command(
        db_conn, user_id=test_user_id, input_type="text", status="ok", intent_name="third"
    )

    commands = get_commands(db_conn, user_id=test_user_id)

    # Most recent should be first
    assert commands[0]["intent_name"] == "third"
    assert commands[1]["intent_name"] == "second"
    assert commands[2]["intent_name"] == "first"


def test_audio_input_type(db_conn, test_user_id):
    """Test storing commands with audio input type."""
    create_command(
        db_conn,
        user_id=test_user_id,
        input_type="audio",
        status="ok",
        transcript="Voice command transcript",
        store_transcript=True,
    )

    commands = get_commands(db_conn, user_id=test_user_id)
    command = commands[0]

    assert command["input_type"] == "audio"
    assert command["transcript"] == "Voice command transcript"
