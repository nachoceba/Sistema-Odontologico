"""Limite de pedidos en memoria (doble de prueba del de Redis): ventanas fijas, reloj inyectado."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import datetime

from app.domain.public_booking.ports import RateDecision


class InMemoryRateLimiter:
    def __init__(self, clock: Callable[[], datetime]) -> None:
        self._clock = clock
        self._counts: dict[tuple[str, str, int], int] = defaultdict(int)

    def hit(self, group: str, client: str, *, limit: int, window_seconds: int) -> RateDecision:
        seconds = int(self._clock().timestamp())
        window = seconds // window_seconds
        self._counts[(group, client, window)] += 1
        if self._counts[(group, client, window)] <= limit:
            return RateDecision(allowed=True)
        return RateDecision(allowed=False, retry_after=(window + 1) * window_seconds - seconds)
