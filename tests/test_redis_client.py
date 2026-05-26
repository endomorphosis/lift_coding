"""Tests for the Redis client factory."""

import logging
from types import SimpleNamespace

import pytest

from handsfree import redis_client


class FakeRedisError(Exception):
    pass


class FakeRedisConnectionError(FakeRedisError):
    pass


def _set_fake_redis_ping_error(monkeypatch: pytest.MonkeyPatch, ping_error: Exception) -> None:
    class FakeRedis:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def ping(self) -> None:
            raise ping_error

    monkeypatch.setattr(redis_client, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(redis_client.redis, "RedisError", FakeRedisError)
    monkeypatch.setattr(redis_client.redis, "ConnectionError", FakeRedisConnectionError)
    monkeypatch.setattr(redis_client.redis, "Redis", FakeRedis)
    monkeypatch.setenv("REDIS_ENABLED", "true")


def test_get_redis_client_returns_none_for_invalid_env_port(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Invalid Redis configuration should use the documented None fallback."""
    monkeypatch.setattr(redis_client, "REDIS_AVAILABLE", True)
    monkeypatch.setenv("REDIS_ENABLED", "true")
    monkeypatch.setenv("REDIS_PORT", "not-a-port")
    caplog.set_level(logging.WARNING, logger="handsfree.redis_client")

    assert redis_client.get_redis_client() is None
    assert "Invalid REDIS_PORT value" in caplog.text


def test_get_redis_client_returns_none_for_redis_library_errors(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _set_fake_redis_ping_error(monkeypatch, FakeRedisError("redis backend unavailable"))
    caplog.set_level(logging.WARNING, logger="handsfree.redis_client")

    client = redis_client.get_redis_client(host="redis.local", port=6380)

    assert client is None
    assert "Redis error connecting to Redis at redis.local:6380 (db=0)" in caplog.text


def test_get_redis_client_does_not_swallow_unexpected_init_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only Redis errors are fallback-safe; unrelated runtime defects should surface."""

    class InitRedisError(Exception):
        pass

    class InitConnectionError(InitRedisError):
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
            RedisError=InitRedisError,
            ConnectionError=InitConnectionError,
        ),
    )

    with pytest.raises(RuntimeError, match="unexpected init failure"):
        redis_client.get_redis_client(port=6379)


def test_get_redis_client_does_not_swallow_unexpected_ping_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_fake_redis_ping_error(monkeypatch, RuntimeError("unexpected redis client bug"))

    with pytest.raises(RuntimeError, match="unexpected redis client bug"):
        redis_client.get_redis_client(host="redis.local", port=6380)
