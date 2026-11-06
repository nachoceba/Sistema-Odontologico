"""Tipos de la entrega de emails (design D-1). Solo libreria estandar."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class OutgoingEmail:
    """Email ya armado: un destinatario, asunto y cuerpo en texto plano."""

    recipient: str
    subject: str
    body: str


class DeliveryDecision(Enum):
    """Que hacer con una notificacion al procesarla (design D-2)."""

    SEND = "SEND"
    SKIP = "SKIP"
    EXPIRE = "EXPIRE"


class DeliveryOutcome(Enum):
    """Resultado de procesar una notificacion (design D-1, D-12)."""

    SENT = "SENT"
    SKIPPED = "SKIPPED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"
    RETRY = "RETRY"
