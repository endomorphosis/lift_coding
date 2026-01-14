"""Tests for the GET /v1/status endpoint."""

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app

client = TestClient(app)


@pytest.fixture
def reset_db():
    """Reset the database connection before each test."""
    import handsfree.api as api_module

    api_module._db_conn = None
    api_module._command_router = None
    yield
    api_module._db_conn = None
    api_module._command_router = None


def test_get_status_returns_200(reset_db) -> None:
    """Test GET /v1/status returns 200 OK."""
    response = client.get("/v1/status")
    assert response.status_code == 200


def test_get_status_response_structure(reset_db) -> None:
    """Test GET /v1/status returns expected response structure."""
    response = client.get("/v1/status")
    assert response.status_code == 200

    data = response.json()

    # Validate required fields
    assert "status" in data
    assert "timestamp" in data

    # Validate status is one of the expected values
    assert data["status"] in ["ok", "degraded", "unavailable"]

    # Validate optional fields
    if "version" in data:
        assert isinstance(data["version"], str)

    if "dependencies" in data:
        assert isinstance(data["dependencies"], list)
        for dep in data["dependencies"]:
            assert "name" in dep
            assert "status" in dep
            assert dep["status"] in ["ok", "degraded", "unavailable"]


def test_get_status_has_timestamp(reset_db) -> None:
    """Test GET /v1/status includes a timestamp."""
    response = client.get("/v1/status")
    data = response.json()

    assert "timestamp" in data
    # Timestamp should be ISO 8601 format
    timestamp = data["timestamp"]
    assert isinstance(timestamp, str)
    # Basic check: should contain 'T' and end with timezone info
    assert "T" in timestamp


def test_get_status_includes_duckdb_dependency(reset_db) -> None:
    """Test GET /v1/status includes DuckDB dependency status."""
    response = client.get("/v1/status")
    data = response.json()

    assert "dependencies" in data
    dependencies = data["dependencies"]

    # Should have at least DuckDB dependency
    assert len(dependencies) > 0

    # Find DuckDB dependency
    duckdb_dep = next((dep for dep in dependencies if dep["name"] == "duckdb"), None)
    assert duckdb_dep is not None
    assert "status" in duckdb_dep
    assert duckdb_dep["status"] in ["ok", "degraded", "unavailable"]


def test_get_status_no_sensitive_config(reset_db) -> None:
    """Test GET /v1/status does not expose sensitive configuration."""
    response = client.get("/v1/status")
    data = response.json()

    # Convert to JSON string to check for sensitive keywords
    response_str = response.text.lower()

    # Should not contain sensitive information
    sensitive_keywords = [
        "password",
        "secret",
        "token",
        "key",
        "api_key",
        "private",
        "credential",
    ]

    for keyword in sensitive_keywords:
        assert keyword not in response_str, f"Response contains sensitive keyword: {keyword}"


def test_get_status_version_present(reset_db) -> None:
    """Test GET /v1/status includes version information."""
    response = client.get("/v1/status")
    data = response.json()

    # Version should be present
    assert "version" in data
    if data["version"] is not None:
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0


def test_get_status_idempotent(reset_db) -> None:
    """Test GET /v1/status is idempotent."""
    response1 = client.get("/v1/status")
    response2 = client.get("/v1/status")

    assert response1.status_code == 200
    assert response2.status_code == 200

    # Status should be consistent
    assert response1.json()["status"] == response2.json()["status"]


def test_get_status_no_auth_required(reset_db) -> None:
    """Test GET /v1/status does not require authentication."""
    # This endpoint should be accessible without authentication
    response = client.get("/v1/status")
    # Should return 200, not 401 (unauthorized)
    assert response.status_code == 200
