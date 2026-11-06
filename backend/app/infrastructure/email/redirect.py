"""Envoltorio de redireccion para la demo (spec email-sending, P-2).

Con ``EMAIL_REDIRECT_TO`` todos los emails van a esa casilla con una linea de demostracion y sin
la direccion original; vacia, pasan al destinatario del paciente sin cambios.
"""

from __future__ import annotations

from dataclasses import replace

from app.domain.notifications import EmailSender, OutgoingEmail

DEMO_LINE = "Email de demostración: en producción se enviaría al paciente del turno."


class RedirectingEmailSender:
    def __init__(self, inner: EmailSender, redirect_to: str) -> None:
        self._inner = inner
        self._redirect_to = redirect_to

    def send(self, email: OutgoingEmail) -> None:
        if not self._redirect_to:
            self._inner.send(email)
            return
        self._inner.send(
            replace(email, recipient=self._redirect_to, body=f"{DEMO_LINE}\n\n{email.body}")
        )
