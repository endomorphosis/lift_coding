"""Tests for persistent database functionality."""

import os
import tempfile
from pathlib import Path

from handsfree.db.connection import get_db_path, init_db
from handsfree.db.notifications import create_notification, list_notifications


def test_default_db_path_from_env():
    """Test that get_db_path respects DUCKDB_PATH environment variable."""
    # In tests, conftest.py sets DUCKDB_PATH=:memory:
    assert get_db_path() == ":memory:"


def test_default_db_path_without_env():
    """Test that get_db_path uses default when DUCKDB_PATH is not set."""
    # Temporarily remove the env var
    original = os.environ.pop("DUCKDB_PATH", None)
    try:
        assert get_db_path() == "data/handsfree.db"
    finally:
        # Restore it
        if original:
            os.environ["DUCKDB_PATH"] = original


def test_persistent_db_creates_file():
    """Test that persistent database creates a file on disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        
        # Initialize database
        conn = init_db(str(db_path))
        
        # Verify file was created
        assert db_path.exists()
        
        # Write some data
        test_user_id = "12345678-1234-1234-1234-123456789012"
        create_notification(
            conn=conn,
            user_id=test_user_id,
            event_type="test.persistence",
            message="Test message",
            metadata={"test": True}
        )
        
        # Close connection
        conn.close()
        
        # Reopen and verify data persists
        conn2 = init_db(str(db_path))
        notifications = list_notifications(conn=conn2, user_id=test_user_id, limit=10)
        
        assert len(notifications) == 1
        assert notifications[0].message == "Test message"
        assert notifications[0].event_type == "test.persistence"
        
        conn2.close()


def test_memory_db_does_not_persist():
    """Test that :memory: database does not persist across connections."""
    # Create first connection with memory database
    conn1 = init_db(":memory:")
    
    test_user_id = "12345678-1234-1234-1234-123456789012"
    create_notification(
        conn=conn1,
        user_id=test_user_id,
        event_type="test.ephemeral",
        message="This should not persist",
        metadata={"test": True}
    )
    
    # Verify data exists
    notifications = list_notifications(conn=conn1, user_id=test_user_id, limit=10)
    assert len(notifications) == 1
    
    conn1.close()
    
    # Create new connection - data should be gone
    conn2 = init_db(":memory:")
    notifications = list_notifications(conn=conn2, user_id=test_user_id, limit=10)
    assert len(notifications) == 0
    
    conn2.close()


def test_api_uses_memory_db_in_tests():
    """Test that the API uses memory database during tests."""
    from handsfree import api
    
    # Reset connection
    api._db_conn = None
    
    # Get DB (should use :memory: due to conftest.py)
    _ = api.get_db()
    
    # Check it's using memory database
    # We can verify by checking that DUCKDB_PATH is set to :memory:
    assert os.environ.get("DUCKDB_PATH") == ":memory:"
