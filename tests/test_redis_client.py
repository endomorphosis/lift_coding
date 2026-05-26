"""Unit tests for Redis client factory fallback behavior."""

from types import SimpleNamespace

import pytest

from handsfree import redis_client


def test_get_redis_client_returns_none_for_invalid_env_port(monkeypatch, caplog) -> None:
    """Invalid Redis configuration should use the documented None fallback."""
    monkeypatch.setattr(redis_client, "REDIS_AVAILABLE", True)
    monkeypatch.setenv("REDIS_ENABLED", "true")
    monkeypatch.setenv("REDIS_PORT", "not-a-port")

    assert redis_client.get_redis_client() is None
    assert "Invalid REDIS_PORT value" in caplog.text


def test_get_redis_client_does_not_swallow_unexpected_init_errors(monkeypatch) -> None:
    """Only Redis errors are fallback-safe; unrelated runtime defects should surface."""

    class FakeRedisError(Exception):
        pass

    class FakeConnectionError(FakeRedisError):
        pass

    def raise_runtime_error(**_kwargs):
        raise RuntimeError("unexpected init failure")

    monkeypatch.setattr(redis_client, "REDIS_AVAILABLE", True)
    monkeypatch.setenv("REDIS_ENABLED", "true")
    monkeypatch.setattr(
        redis_client,
        "redis",
        SimpleNamespace(
            Redis=raise_runtime_error,
            RedisError=FakeRedisError,
            ConnectionError=FakeConnectionError,
        ),
    )

    with pytest.raises(RuntimeError, match="unexpected init failure"):
        redis_client.get_redis_client(port=6379)
