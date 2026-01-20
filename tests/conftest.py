"""pytest configuration for HandsFree tests."""

import os
import sys
import uuid
from pathlib import Path

import pytest

# Add src directory to path so tests can import handsfree
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Set DUCKDB_PATH to :memory: for all tests to ensure test isolation
os.environ["DUCKDB_PATH"] = ":memory:"

# Image fetching configuration for tests
# Enable local image URIs for testing (gated by env var for security)
os.environ["HANDSFREE_ALLOW_LOCAL_IMAGE_URIS"] = "1"
# Disable strict host checking for tests to avoid requiring allowlist configuration
os.environ["IMAGE_STRICT_HOST_CHECKING"] = "0"
# Limit maximum image size (in bytes) for tests (5 MiB)
os.environ["IMAGE_MAX_SIZE_BYTES"] = "5242880"
# Set a reasonable timeout (in seconds) for fetching images in tests
os.environ["IMAGE_FETCH_TIMEOUT_SECONDS"] = "10"


@pytest.fixture
def test_user_id():
    """Generate a consistent test user ID."""
    # Use a fixed UUID for consistent testing
    return str(uuid.UUID("12345678-1234-1234-1234-123456789012"))


@pytest.fixture
def test_user_id_2():
    """Generate a second test user ID."""
    return str(uuid.UUID("87654321-4321-4321-4321-210987654321"))
