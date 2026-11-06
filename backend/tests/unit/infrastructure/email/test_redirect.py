"""Redireccion de destinatarios para la demo (spec email-sending, P-2)."""

from __future__ import annotations

from app.domain.notifications import OutgoingEmail
from app.infrastructure.email.redirect import RedirectingEmailSender
from tests.email_fakes import FakeEmailSender

ORIGINAL = OutgoingEmail("juan.perez@example.com", "Turno confirmado", "Hola, Juan Perez:\nTexto")
DEMO_LINE = "Email de demostración: en producción se enviaría al paciente del turno."


def test_with_a_redirect_everything_goes_there_with_the_demo_line_first() -> None:
    inner = FakeEmailSender()

    RedirectingEmailSender(inner, "equipo.demo@example.org").send(ORIGINAL)

    [sent] = inner.sent
    assert sent.recipient == "equipo.demo@example.org"
    assert sent.body.startswith(DEMO_LINE)
    assert sent.body.endswith(ORIGINAL.body)
    assert sent.subject == ORIGINAL.subject


def test_the_original_address_never_appears_in_the_redirected_email() -> None:
    inner = FakeEmailSender()

    RedirectingEmailSender(inner, "otra.casilla@example.org").send(
        OutgoingEmail("ana.gomez@example.com", "Asunto", "Cuerpo")
    )

    [sent] = inner.sent
    assert sent.recipient == "otra.casilla@example.org"
    assert "ana.gomez@example.com" not in sent.subject + sent.body


def test_without_a_redirect_it_goes_to_the_patient_unchanged() -> None:
    inner = FakeEmailSender()

    RedirectingEmailSender(inner, "").send(ORIGINAL)

    assert inner.sent == [ORIGINAL]
    assert DEMO_LINE not in inner.sent[0].body
