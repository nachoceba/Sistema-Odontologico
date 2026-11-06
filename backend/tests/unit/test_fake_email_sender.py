"""El doble de EmailSender de los tests se comporta como pide el puerto."""

from __future__ import annotations

import pytest

from app.domain.notifications import EmailSendError, OutgoingEmail
from tests.email_fakes import FakeEmailSender

EMAIL = OutgoingEmail("juan.perez@example.com", "Asunto", "Cuerpo")


def test_it_stores_the_sent_messages_in_order() -> None:
    sender = FakeEmailSender()
    other = OutgoingEmail("ana@example.com", "Otro", "Texto")
    sender.send(EMAIL)
    sender.send(other)
    assert sender.sent == [EMAIL, other]


def test_it_fails_with_a_temporary_error_n_times_then_recovers() -> None:
    sender = FakeEmailSender()
    sender.fail_next(2, temporary=True, code="TIMEOUT")
    for _ in range(2):
        with pytest.raises(EmailSendError) as caught:
            sender.send(EMAIL)
        assert caught.value.temporary is True
    sender.send(EMAIL)
    assert sender.sent == [EMAIL]
    assert sender.attempts == 3


def test_it_fails_with_a_permanent_error_without_storing() -> None:
    sender = FakeEmailSender()
    sender.fail_next(1, temporary=False, code="550")
    with pytest.raises(EmailSendError) as caught:
        sender.send(EMAIL)
    assert caught.value.temporary is False
    assert caught.value.code == "550"
    assert sender.sent == []
