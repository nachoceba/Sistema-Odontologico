"""Puerto de salida de emails (design D-1). La implementacion SMTP vive en infrastructure."""

from __future__ import annotations

from typing import Protocol

from app.domain.notifications.types import OutgoingEmail


class EmailSender(Protocol):
    """Entrega un email o lanza ``EmailSendError`` (temporal o permanente)."""

    def send(self, email: OutgoingEmail) -> None: ...
