"""Tests for commands persistence."""

import uuid

import pytest

from handsfree.db import init_db
from handsfree.db.commands import get_command_by_id, get_commands, store_command


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


def test_store_command(db_conn):
    """Test storing a command."""
    user_id = str(uuid.uuid4())
    command = store_command(
        db_conn,
        user_id=user_id,
        input_type="text",
        status="ok",
        transcript="merge the PR",
        intent_name="merge_pr",
        intent_confidence=0.95,
        entities={"pr_number": 123},
        store_transcript=True,
    )

    assert command.id is not None
    assert command.user_id == user_id
    assert command.input_type == "text"
    assert command.status == "ok"
    assert command.transcript == "merge the PR"
    assert command.intent_name == "merge_pr"
    assert command.intent_confidence == 0.95
    assert command.entities == {"pr_number": 123}


def test_store_command_without_transcript(db_conn):
    """Test that transcript is not stored when store_transcript=False."""
    user_id = str(uuid.uuid4())
    command = store_command(
        db_conn,
        user_id=user_id,
        input_type="text",
        status="ok",
        transcript="sensitive data here",
        intent_name="test",
        store_transcript=False,  # Privacy: don't store transcript
    )

    # Transcript should be None even though it was provided
    assert command.transcript is None


def test_store_command_defaults(db_conn):
    """Test storing a command with default values."""
    user_id = str(uuid.uuid4())
    command = store_command(
        db_conn,
        user_id=user_id,
        input_type="audio",
        status="needs_confirmation",
    )

    assert command.profile == "default"
    assert command.transcript is None
    assert command.intent_name is None
    assert command.intent_confidence is None
    assert command.entities is None


def test_get_commands(db_conn):
    """Test querying commands."""
    user_id = str(uuid.uuid4())

    # Create multiple commands
    store_command(db_conn, user_id=user_id, input_type="text", status="ok")
    store_command(db_conn, user_id=user_id, input_type="audio", status="ok")
    store_command(db_conn, user_id=user_id, input_type="text", status="error")

    # Get all commands for user
    commands = get_commands(db_conn, user_id=user_id)
    assert len(commands) == 3

    # Filter by status
    ok_commands = get_commands(db_conn, user_id=user_id, status="ok")
    assert len(ok_commands) == 2


def test_get_commands_with_profile_filter(db_conn):
    """Test filtering commands by profile."""
    user_id = str(uuid.uuid4())

    store_command(db_conn, user_id=user_id, input_type="text", status="ok", profile="default")
    store_command(db_conn, user_id=user_id, input_type="text", status="ok", profile="work")

    default_commands = get_commands(db_conn, user_id=user_id, profile="default")
    assert len(default_commands) == 1

    work_commands = get_commands(db_conn, user_id=user_id, profile="work")
    assert len(work_commands) == 1


def test_get_commands_with_limit(db_conn):
    """Test limiting the number of returned commands."""
    user_id = str(uuid.uuid4())

    # Create 5 commands
    for _i in range(5):
        store_command(db_conn, user_id=user_id, input_type="text", status="ok")

    # Request only 3
    commands = get_commands(db_conn, user_id=user_id, limit=3)
    assert len(commands) == 3


def test_get_command_by_id(db_conn):
    """Test retrieving a specific command."""
    user_id = str(uuid.uuid4())
    created = store_command(
        db_conn,
        user_id=user_id,
        input_type="text",
        status="ok",
        intent_name="test_intent",
        store_transcript=True,
        transcript="test command",
    )

    retrieved = get_command_by_id(db_conn, created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.user_id == user_id
    assert retrieved.intent_name == "test_intent"
    assert retrieved.transcript == "test command"


def test_get_nonexistent_command(db_conn):
    """Test retrieving a non-existent command."""
    result = get_command_by_id(db_conn, str(uuid.uuid4()))
    assert result is None


def test_command_ordering(db_conn):
    """Test that commands are returned in descending order by creation time."""
    user_id = str(uuid.uuid4())

    # Create commands
    cmd1 = store_command(db_conn, user_id=user_id, input_type="text", status="ok")
    cmd2 = store_command(db_conn, user_id=user_id, input_type="text", status="ok")
    cmd3 = store_command(db_conn, user_id=user_id, input_type="text", status="ok")

    # Retrieve commands
    commands = get_commands(db_conn, user_id=user_id)

    # Should be in reverse order (newest first)
    assert commands[0].id == cmd3.id
    assert commands[1].id == cmd2.id
    assert commands[2].id == cmd1.id


def test_command_with_complex_entities(db_conn):
    """Test storing and retrieving complex entity JSON."""
    user_id = str(uuid.uuid4())
    complex_entities = {
        "repo": "owner/repo",
        "pr_number": 456,
        "merge_options": {
            "method": "squash",
            "delete_branch": True,
        },
        "reviewers": ["user1", "user2"],
    }

    command = store_command(
        db_conn,
        user_id=user_id,
        input_type="text",
        status="ok",
        entities=complex_entities,
    )

    retrieved = get_command_by_id(db_conn, command.id)
    assert retrieved is not None
    assert retrieved.entities == complex_entities
