"""Limite de pedidos sobre Redis: ventanas fijas con ``INCR`` + ``EXPIRE`` (C-15, design D-8).

La clave es ``rl:{grupo}:{ip}:{ventana}``: nunca lleva el documento, el token ni otros datos del
cuerpo. Si Redis no responde el pedido sigue (falla abierta) y queda un aviso sin la IP.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

import redis

from app.domain.public_booking.ports import RateDecision

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    def __init__(self, client: redis.Redis, clock: Callable[[], datetime]) -> None:
        self._client = client
        self._clock = clock

    def hit(self, group: str, client: str, *, limit: int, window_seconds: int) -> RateDecision:
        seconds = int(self._clock().timestamp())
        window = seconds // window_seconds
        key = f"rl:{group}:{client}:{window}"
        try:
            with self._client.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, window_seconds)
                count = int(pipe.execute()[0])
        except redis.RedisError as error:
            logger.warning(
                "limite de pedidos: Redis no responde (%s); el pedido sigue sin limite",
                type(error).__name__,
            )
            return RateDecision(allowed=True)
        if count <= limit:
            return RateDecision(allowed=True)
        return RateDecision(allowed=False, retry_after=(window + 1) * window_seconds - seconds)


def build_redis_rate_limiter(url: str, clock: Callable[[], datetime]) -> RedisRateLimiter:
    """Cliente con tiempos cortos: con Redis caido el pedido falla abierto en pocos segundos."""
    client = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
    return RedisRateLimiter(client, clock)
