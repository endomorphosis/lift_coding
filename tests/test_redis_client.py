"""Tests for the Redis client factory."""

import logging

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


def test_get_redis_client_returns_none_for_redis_library_errors(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _set_fake_redis_ping_error(monkeypatch, FakeRedisError("redis backend unavailable"))
    caplog.set_level(logging.WARNING, logger="handsfree.redis_client")

    client = redis_client.get_redis_client(host="redis.local", port=6380)

    assert client is None
    assert "Redis error connecting to Redis at redis.local:6380 (db=0)" in caplog.text


def test_get_redis_client_does_not_swallow_unexpected_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_fake_redis_ping_error(monkeypatch, RuntimeError("unexpected redis client bug"))

    with pytest.raises(RuntimeError, match="unexpected redis client bug"):
        redis_client.get_redis_client(host="redis.local", port=6380)
