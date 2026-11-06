"""Adaptador SMTP con un ``smtplib.SMTP`` reemplazado por un doble (spec email-sending)."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Any

import pytest

from app.domain.notifications import EmailSendError, OutgoingEmail, sanitize_error
from app.infrastructure.email.smtp import SmtpEmailSender

EMAIL = OutgoingEmail(
    "juan.perez@example.com", "Turno confirmado", "Hola, Juan Peña Gómez: miércoles 10:00 h"
)
PASSWORD = "clave-super-secreta"
USER = "usuario-smtp"


class FakeSmtp:
    """Registra las llamadas en el orden en que ocurren; puede fallar en un paso."""

    instances: list[FakeSmtp] = []
    fail_at: dict[str, BaseException] = {}

    def __init__(self, host: str, port: int, timeout: float | None = None) -> None:
        self.host, self.port, self.timeout = host, port, timeout
        self.calls: list[str] = []
        self.message: EmailMessage | None = None
        self.login_args: tuple[str, str] | None = None
        self._maybe_fail("connect")
        FakeSmtp.instances.append(self)

    def _maybe_fail(self, step: str) -> None:
        self.calls.append(step)
        if step in FakeSmtp.fail_at:
            raise FakeSmtp.fail_at[step]

    def __enter__(self) -> FakeSmtp:
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def starttls(self) -> None:
        self._maybe_fail("starttls")

    def login(self, user: str, password: str) -> None:
        self.login_args = (user, password)
        self._maybe_fail("login")

    def send_message(self, message: EmailMessage) -> None:
        self.message = message
        self._maybe_fail("send")


@pytest.fixture(autouse=True)
def reset_fake() -> None:
    FakeSmtp.instances = []
    FakeSmtp.fail_at = {}


def make_sender(*, user: str = "", use_tls: bool = False) -> SmtpEmailSender:
    return SmtpEmailSender(
        host="mailpit",
        port=1025,
        user=user,
        password=PASSWORD if user else "",
        use_tls=use_tls,
        sender="turnos@consultorio.test",
        smtp_factory=FakeSmtp,
    )


def test_without_a_user_it_never_logs_in_and_never_uses_starttls() -> None:
    make_sender().send(EMAIL)

    [smtp] = FakeSmtp.instances
    assert smtp.calls == ["connect", "send"]
    assert (smtp.host, smtp.port) == ("mailpit", 1025)


def test_the_connection_has_a_timeout_of_at_most_ten_seconds() -> None:
    make_sender().send(EMAIL)
    [smtp] = FakeSmtp.instances
    assert smtp.timeout is not None
    assert smtp.timeout <= 10


def test_with_tls_and_user_it_negotiates_starttls_then_logs_in_then_sends() -> None:
    make_sender(user=USER, use_tls=True).send(EMAIL)

    [smtp] = FakeSmtp.instances
    assert smtp.calls == ["connect", "starttls", "login", "send"]
    assert smtp.login_args == (USER, PASSWORD)


def test_with_a_user_and_no_tls_it_logs_in_without_starttls() -> None:
    make_sender(user=USER, use_tls=False).send(EMAIL)
    [smtp] = FakeSmtp.instances
    assert smtp.calls == ["connect", "login", "send"]


def test_the_message_has_sender_recipient_subject_and_utf8_body() -> None:
    make_sender().send(EMAIL)

    message = FakeSmtp.instances[0].message
    assert message is not None
    assert message["From"] == "turnos@consultorio.test"
    assert message["To"] == "juan.perez@example.com"
    assert message["Subject"] == "Turno confirmado"
    assert message.get_content().strip() == EMAIL.body
    assert message.get_content_charset() == "utf-8"


@pytest.mark.parametrize(
    ("step", "raised", "temporary", "text"),
    [
        (
            "send",
            smtplib.SMTPRecipientsRefused({"juan.perez@example.com": (550, b"5.1.1 rechazado")}),
            False,
            "SMTP_PERMANENT 550",
        ),
        ("login", smtplib.SMTPAuthenticationError(535, b"mal"), False, "SMTP_PERMANENT 535"),
        ("send", smtplib.SMTPDataError(451, b"ocupado"), True, "SMTP_TEMPORARY 451"),
        ("send", smtplib.SMTPSenderRefused(553, b"no", "a@b.c"), False, "SMTP_PERMANENT 553"),
        ("connect", ConnectionRefusedError(), True, "SMTP_TEMPORARY CONNECTION"),
        ("connect", TimeoutError(), True, "SMTP_TEMPORARY TIMEOUT"),
        ("send", smtplib.SMTPServerDisconnected("cortada"), True, "SMTP_TEMPORARY CONNECTION"),
        ("send", OSError("red caida"), True, "SMTP_TEMPORARY CONNECTION"),
    ],
)
def test_smtp_failures_are_translated_to_temporary_or_permanent(
    step: str, raised: BaseException, temporary: bool, text: str
) -> None:
    FakeSmtp.fail_at[step] = raised

    with pytest.raises(EmailSendError) as caught:
        make_sender(user=USER, use_tls=True).send(EMAIL)

    assert caught.value.temporary is temporary
    assert sanitize_error(caught.value) == text


def test_errors_and_logs_never_contain_the_password_nor_the_user(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    FakeSmtp.fail_at["login"] = smtplib.SMTPAuthenticationError(
        535, f"clave {PASSWORD} usuario {USER}".encode()
    )

    with pytest.raises(EmailSendError) as caught:
        make_sender(user=USER, use_tls=True).send(EMAIL)

    visible = f"{caught.value!s} {sanitize_error(caught.value)} {caplog.text}"
    assert PASSWORD not in visible
    assert USER not in visible
    assert "juan.perez@example.com" not in visible
