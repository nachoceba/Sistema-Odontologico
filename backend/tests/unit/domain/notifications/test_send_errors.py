"""Fallos de envio sin datos personales (spec email-sending, design D-4)."""

from __future__ import annotations

import pytest

from app.domain.notifications import EmailSendError, sanitize_error


def test_a_permanent_550_keeps_only_the_code_not_the_address() -> None:
    raw = "550 5.1.1 <juan.perez@example.com>: Recipient address rejected"
    error = EmailSendError(temporary=False, code=raw)

    text = sanitize_error(error)

    assert text == "SMTP_PERMANENT 550"
    assert "@" not in text
    assert "juan" not in text


def test_a_temporary_451_is_marked_temporary() -> None:
    assert sanitize_error(EmailSendError(temporary=True, code="451")) == "SMTP_TEMPORARY 451"


@pytest.mark.parametrize("word", ["CONNECTION", "TIMEOUT"])
def test_network_failures_use_their_word(word: str) -> None:
    assert sanitize_error(EmailSendError(temporary=True, code=word)) == f"SMTP_TEMPORARY {word}"


def test_an_unknown_code_is_dropped_instead_of_copied() -> None:
    text = sanitize_error(EmailSendError(temporary=False, code="clave: hunter2 juan@example.com"))
    assert text == "SMTP_PERMANENT"


def test_the_text_never_exceeds_200_characters() -> None:
    text = sanitize_error(EmailSendError(temporary=True, code="4" * 5000))
    assert len(text) <= 200
    assert "@" not in text


def test_the_exception_message_carries_no_raw_detail() -> None:
    error = EmailSendError(temporary=False, code="550 <a@b.com>")
    assert "a@b.com" not in str(error)
    assert error.temporary is False
