"""Doble del puerto EmailSender: guarda los mensajes y falla a pedido."""

from __future__ import annotations

from app.domain.notifications import EmailSendError, OutgoingEmail


class FakeEmailSender:
    def __init__(self) -> None:
        self.sent: list[OutgoingEmail] = []
        self.attempts = 0
        self._failures: list[EmailSendError] = []

    def fail_next(self, times: int, *, temporary: bool, code: str = "") -> None:
        self._failures.extend(EmailSendError(temporary=temporary, code=code) for _ in range(times))

    def send(self, email: OutgoingEmail) -> None:
        self.attempts += 1
        if self._failures:
            raise self._failures.pop(0)
        self.sent.append(email)
