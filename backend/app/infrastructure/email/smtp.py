"""Adaptador SMTP con la libreria estandar (spec email-sending, design D-6).

Configurable solo por variables de entorno (``SMTP_*``): apuntar a otro servidor no toca el
dominio. Los fallos se traducen a ``EmailSendError`` con un codigo corto; nunca se copia el texto
del servidor ni se registra el usuario, la clave o el destinatario.
"""

from __future__ import annotations

import smtplib
import socket
from collections.abc import Callable
from email.message import EmailMessage
from typing import Any

from app.domain.notifications import EmailSendError, OutgoingEmail

TIMEOUT_SECONDS = 10.0
_FIRST_PERMANENT = 500


def _translate(error: BaseException) -> EmailSendError:
    if isinstance(error, smtplib.SMTPRecipientsRefused):
        codes = [code for code, _ in error.recipients.values()]
        return EmailSendError(temporary=False, code=str(codes[0]) if codes else "")
    if isinstance(error, smtplib.SMTPResponseException):
        return EmailSendError(
            temporary=error.smtp_code < _FIRST_PERMANENT, code=str(error.smtp_code)
        )
    if isinstance(error, TimeoutError | socket.timeout):
        return EmailSendError(temporary=True, code="TIMEOUT")
    if isinstance(error, smtplib.SMTPServerDisconnected | OSError):
        return EmailSendError(temporary=True, code="CONNECTION")
    return EmailSendError(temporary=True)


class SmtpEmailSender:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        use_tls: bool,
        sender: str,
        timeout: float = TIMEOUT_SECONDS,
        smtp_factory: Callable[..., Any] = smtplib.SMTP,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._use_tls = use_tls
        self._sender = sender
        self._timeout = min(timeout, TIMEOUT_SECONDS)
        self._factory = smtp_factory

    def send(self, email: OutgoingEmail) -> None:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = email.recipient
        message["Subject"] = email.subject
        message.set_content(email.body, charset="utf-8")
        try:
            with self._factory(self._host, self._port, timeout=self._timeout) as smtp:
                if self._use_tls:
                    smtp.starttls()
                if self._user:
                    smtp.login(self._user, self._password)
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as error:
            raise _translate(error) from None
