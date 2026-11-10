"""RedisRateLimiter con un cliente falso: clave sin datos personales y falla abierta (C-15, D-8)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.infrastructure.rate_limiter import RedisRateLimiter

NOW = datetime(2026, 11, 9, 12, 30, 0, tzinfo=UTC)  # 1.7 mil millones de segundos: ventana fija


class FakePipeline:
    def __init__(self, store: dict[str, int], log: list[tuple[str, str, int | None]]) -> None:
        self._store = store
        self._log = log
        self._keys: list[str] = []

    def incr(self, key: str) -> FakePipeline:
        self._store[key] = self._store.get(key, 0) + 1
        self._keys.append(key)
        self._log.append(("incr", key, None))
        return self

    def expire(self, key: str, seconds: int) -> FakePipeline:
        self._log.append(("expire", key, seconds))
        return self

    def execute(self) -> list[Any]:
        return [self._store[self._keys[0]], True]

    def __enter__(self) -> FakePipeline:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, int] = {}
        self.log: list[tuple[str, str, int | None]] = []

    def pipeline(self, transaction: bool = True) -> FakePipeline:
        assert transaction is True
        return FakePipeline(self.store, self.log)


class BrokenRedis:
    def pipeline(self, transaction: bool = True) -> Any:
        raise RedisConnectionError("redis caido en 10.0.0.5")


def test_it_counts_with_incr_and_expire_on_a_key_without_personal_data() -> None:
    client = FakeRedis()
    limiter = RedisRateLimiter(client, lambda: NOW)  # type: ignore[arg-type]

    limiter.hit("book", "203.0.113.9", limit=5, window_seconds=3600)

    window = int(NOW.timestamp()) // 3600
    assert client.log == [
        ("incr", f"rl:book:203.0.113.9:{window}", None),
        ("expire", f"rl:book:203.0.113.9:{window}", 3600),
    ]


def test_it_denies_over_the_limit_with_the_seconds_to_the_next_window() -> None:
    limiter = RedisRateLimiter(FakeRedis(), lambda: NOW)  # type: ignore[arg-type]

    decisions = [limiter.hit("book", "1.1.1.1", limit=2, window_seconds=3600) for _ in range(3)]

    assert [d.allowed for d in decisions] == [True, True, False]
    assert decisions[2].retry_after == 3600 - int(NOW.timestamp()) % 3600


def test_with_redis_down_it_allows_and_logs_a_warning_without_the_address(
    caplog: pytest.LogCaptureFixture,
) -> None:
    limiter = RedisRateLimiter(BrokenRedis(), lambda: NOW)  # type: ignore[arg-type]
    caplog.set_level(logging.WARNING)

    decision = limiter.hit("book", "203.0.113.9", limit=1, window_seconds=3600)

    assert decision.allowed is True
    assert "ConnectionError" in caplog.text
    assert "203.0.113.9" not in caplog.text
    assert "10.0.0.5" not in caplog.text
