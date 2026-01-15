"""Tests for observability metrics."""

import os

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app
from handsfree.metrics import get_metrics_collector, is_metrics_enabled


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def reset_metrics():
    """Reset metrics before and after each test."""
    collector = get_metrics_collector()
    collector.reset()
    yield
    collector.reset()


def test_metrics_collector_record_command(reset_metrics):
    """Test that MetricsCollector records command metrics correctly."""
    collector = get_metrics_collector()

    # Record some commands
    collector.record_command("inbox.list", "ok", 150.5)
    collector.record_command("pr.summarize", "ok", 200.3)
    collector.record_command("inbox.list", "ok", 175.2)
    collector.record_command("pr.merge", "needs_confirmation", 120.0)
    collector.record_command("unknown", "error", 50.0)

    # Get snapshot
    snapshot = collector.get_snapshot()

    # Check intent counts
    assert snapshot["intent_counts"]["inbox.list"] == 2
    assert snapshot["intent_counts"]["pr.summarize"] == 1
    assert snapshot["intent_counts"]["pr.merge"] == 1
    assert snapshot["intent_counts"]["unknown"] == 1

    # Check status counts
    assert snapshot["status_counts"]["ok"] == 3
    assert snapshot["status_counts"]["needs_confirmation"] == 1
    assert snapshot["status_counts"]["error"] == 1

    # Check latency
    assert snapshot["command_latency_ms"]["count"] == 5
    assert snapshot["command_latency_ms"]["p50"] is not None
    assert snapshot["command_latency_ms"]["p95"] is not None


def test_metrics_collector_record_confirmation(reset_metrics):
    """Test that MetricsCollector records confirmation metrics correctly."""
    collector = get_metrics_collector()

    # Record some confirmations
    collector.record_confirmation("ok")
    collector.record_confirmation("ok")
    collector.record_confirmation("not_found")
    collector.record_confirmation("error")

    # Get snapshot
    snapshot = collector.get_snapshot()

    # Check confirmation outcomes
    assert snapshot["confirm_outcomes"]["ok"] == 2
    assert snapshot["confirm_outcomes"]["not_found"] == 1
    assert snapshot["confirm_outcomes"]["error"] == 1


def test_metrics_collector_percentiles(reset_metrics):
    """Test latency percentile calculation."""
    collector = get_metrics_collector()

    # Record latencies in known order
    latencies = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    for lat in latencies:
        collector.record_command("test.intent", "ok", lat)

    snapshot = collector.get_snapshot()

    # p50 should be around 50-60 (median)
    assert 40 <= snapshot["command_latency_ms"]["p50"] <= 60

    # p95 should be around 90-100
    assert 85 <= snapshot["command_latency_ms"]["p95"] <= 100


def test_metrics_endpoint_disabled_by_default(client, reset_metrics):
    """Test that /v1/metrics is disabled by default."""
    # Ensure HANDSFREE_ENABLE_METRICS is not set
    old_value = os.environ.pop("HANDSFREE_ENABLE_METRICS", None)

    try:
        response = client.get("/v1/metrics")
        assert response.status_code == 404
        assert response.json()["error"] == "not_found"
    finally:
        # Restore old value if it existed
        if old_value is not None:
            os.environ["HANDSFREE_ENABLE_METRICS"] = old_value


def test_metrics_endpoint_enabled(client, reset_metrics):
    """Test that /v1/metrics works when enabled."""
    # Enable metrics
    os.environ["HANDSFREE_ENABLE_METRICS"] = "true"

    try:
        # Record some metrics via commands
        collector = get_metrics_collector()
        collector.record_command("inbox.list", "ok", 100.0)
        collector.record_command("pr.summarize", "ok", 200.0)
        collector.record_confirmation("ok")

        # Get metrics via endpoint
        response = client.get("/v1/metrics")
        assert response.status_code == 200

        data = response.json()
        assert "intent_counts" in data
        assert "status_counts" in data
        assert "confirm_outcomes" in data
        assert "command_latency_ms" in data

        # Check some values
        assert data["intent_counts"]["inbox.list"] == 1
        assert data["intent_counts"]["pr.summarize"] == 1
        assert data["status_counts"]["ok"] == 2
        assert data["confirm_outcomes"]["ok"] == 1
        assert data["command_latency_ms"]["count"] == 2
    finally:
        # Clean up
        os.environ.pop("HANDSFREE_ENABLE_METRICS", None)


def test_command_endpoint_records_metrics(client, reset_metrics):
    """Test that /v1/command records metrics."""
    # Enable metrics
    os.environ["HANDSFREE_ENABLE_METRICS"] = "true"

    try:
        # Make a command request
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "show my inbox"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "1.0.0",
                },
            },
            headers={"X-User-ID": "test-user-123"},
        )
        assert response.status_code == 200

        # Check that metrics were recorded
        metrics_response = client.get("/v1/metrics")
        assert metrics_response.status_code == 200

        data = metrics_response.json()
        assert data["command_latency_ms"]["count"] >= 1
        assert "inbox.list" in data["intent_counts"]
        assert data["status_counts"]["ok"] >= 1
    finally:
        # Clean up
        os.environ.pop("HANDSFREE_ENABLE_METRICS", None)


def test_confirm_endpoint_records_metrics(client, reset_metrics):
    """Test that /v1/commands/confirm records metrics."""
    # Enable metrics
    os.environ["HANDSFREE_ENABLE_METRICS"] = "true"

    try:
        # Try to confirm a non-existent action (should record not_found)
        response = client.post(
            "/v1/commands/confirm",
            json={"token": "non-existent-token"},
            headers={"X-User-ID": "test-user-123"},
        )
        assert response.status_code == 404

        # Check that metrics were recorded
        metrics_response = client.get("/v1/metrics")
        assert metrics_response.status_code == 200

        data = metrics_response.json()
        assert "not_found" in data["confirm_outcomes"]
        assert data["confirm_outcomes"]["not_found"] >= 1
    finally:
        # Clean up
        os.environ.pop("HANDSFREE_ENABLE_METRICS", None)


def test_is_metrics_enabled():
    """Test is_metrics_enabled function."""
    # Test default (should be false)
    old_value = os.environ.pop("HANDSFREE_ENABLE_METRICS", None)
    try:
        assert is_metrics_enabled() is False

        # Test true values
        for value in ["true", "True", "TRUE", "1", "yes"]:
            os.environ["HANDSFREE_ENABLE_METRICS"] = value
            assert is_metrics_enabled() is True

        # Test false values
        for value in ["false", "False", "FALSE", "0", "no"]:
            os.environ["HANDSFREE_ENABLE_METRICS"] = value
            assert is_metrics_enabled() is False
    finally:
        # Restore old value if it existed
        if old_value is not None:
            os.environ["HANDSFREE_ENABLE_METRICS"] = old_value
        else:
            os.environ.pop("HANDSFREE_ENABLE_METRICS", None)


def test_metrics_collector_thread_safety(reset_metrics):
    """Test that MetricsCollector is thread-safe."""
    import threading

    collector = get_metrics_collector()

    def record_many():
        for i in range(100):
            collector.record_command(f"intent_{i % 5}", "ok", float(i))
            collector.record_confirmation("ok")

    # Create multiple threads
    threads = [threading.Thread(target=record_many) for _ in range(10)]

    # Start all threads
    for t in threads:
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Check that all metrics were recorded
    snapshot = collector.get_snapshot()
    assert snapshot["command_latency_ms"]["count"] == 1000  # 10 threads * 100 iterations
    assert sum(snapshot["confirm_outcomes"].values()) == 1000
