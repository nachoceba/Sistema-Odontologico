"""InMemoryRateLimiter: ventanas fijas por grupo e IP, reloj inyectado (C-15, D-8)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.infrastructure.in_memory.rate_limiter import InMemoryRateLimiter

START = datetime(2026, 11, 9, 12, 0, 0, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> datetime:
        return self.now


def test_allows_up_to_the_limit_and_then_denies() -> None:
    limiter = InMemoryRateLimiter(Clock())
    results = [limiter.hit("book", "1.1.1.1", limit=2, window_seconds=3600) for _ in range(3)]
    assert [r.allowed for r in results] == [True, True, False]


def test_denial_reports_seconds_until_the_window_ends() -> None:
    clock = Clock()
    clock.now = START + timedelta(minutes=10)
    limiter = InMemoryRateLimiter(clock)
    limiter.hit("book", "1.1.1.1", limit=1, window_seconds=3600)
    denied = limiter.hit("book", "1.1.1.1", limit=1, window_seconds=3600)
    assert denied.allowed is False
    assert denied.retry_after == 50 * 60


def test_a_new_window_resets_the_counter() -> None:
    clock = Clock()
    limiter = InMemoryRateLimiter(clock)
    limiter.hit("book", "1.1.1.1", limit=1, window_seconds=3600)
    assert limiter.hit("book", "1.1.1.1", limit=1, window_seconds=3600).allowed is False
    clock.now = START + timedelta(hours=1)
    assert limiter.hit("book", "1.1.1.1", limit=1, window_seconds=3600).allowed is True


def test_groups_and_clients_are_independent() -> None:
    limiter = InMemoryRateLimiter(Clock())
    limiter.hit("book", "1.1.1.1", limit=1, window_seconds=3600)
    assert limiter.hit("confirm", "1.1.1.1", limit=1, window_seconds=3600).allowed is True
    assert limiter.hit("book", "2.2.2.2", limit=1, window_seconds=3600).allowed is True
