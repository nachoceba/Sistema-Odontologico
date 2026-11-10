"""Puertos de la reserva online: limite de pedidos y aviso de verificacion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RateDecision:
    """Resultado de contar un pedido; ``retry_after`` en segundos cuando se rechaza."""

    allowed: bool
    retry_after: int = 0


class RateLimiter(Protocol):
    def hit(self, group: str, client: str, *, limit: int, window_seconds: int) -> RateDecision:
        """Cuenta un pedido del cliente en el grupo; rechaza al superar ``limit`` en la ventana."""
        ...


class VerificationDispatcher(Protocol):
    """Pide, despues del commit, el email de verificacion con el token en claro."""

    def dispatch(self, appointment_id: str, token: str) -> None: ...
