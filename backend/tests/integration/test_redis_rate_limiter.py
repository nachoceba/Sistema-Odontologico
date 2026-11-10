"""RedisRateLimiter contra el Redis de Compose (C-15, D-8)."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import redis

from app.infrastructure.rate_limiter import RedisRateLimiter

START = datetime(2026, 11, 9, 12, 0, 0, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def client() -> Iterator[redis.Redis]:
    connection = redis.Redis.from_url(os.environ["REDIS_URL"], socket_connect_timeout=2)
    yield connection
    for key in connection.scan_iter("rl:itest-*"):
        connection.delete(key)
    connection.close()


def test_the_limit_the_retry_after_and_the_new_window(client: redis.Redis) -> None:
    clock = Clock()
    limiter = RedisRateLimiter(client, clock)
    group = f"itest-{uuid.uuid4().hex[:8]}"

    first = [limiter.hit(group, "9.9.9.9", limit=2, window_seconds=3600) for _ in range(3)]
    assert [d.allowed for d in first] == [True, True, False]
    assert first[2].retry_after == 3600

    clock.now = START + timedelta(hours=1)
    assert limiter.hit(group, "9.9.9.9", limit=2, window_seconds=3600).allowed is True


def test_the_key_has_no_document_or_token_and_expires(client: redis.Redis) -> None:
    group = f"itest-{uuid.uuid4().hex[:8]}"
    RedisRateLimiter(client, Clock()).hit(group, "9.9.9.9", limit=5, window_seconds=3600)

    keys = [key.decode() for key in client.scan_iter(f"rl:{group}:*")]

    assert len(keys) == 1
    assert keys[0].startswith(f"rl:{group}:9.9.9.9:")
    assert 0 < client.ttl(keys[0]) <= 3600


def test_groups_are_independent(client: redis.Redis) -> None:
    limiter = RedisRateLimiter(client, Clock())
    book, confirm = (f"itest-{uuid.uuid4().hex[:8]}" for _ in range(2))
    limiter.hit(book, "9.9.9.9", limit=1, window_seconds=3600)

    assert limiter.hit(book, "9.9.9.9", limit=1, window_seconds=3600).allowed is False
    assert limiter.hit(confirm, "9.9.9.9", limit=1, window_seconds=3600).allowed is True
