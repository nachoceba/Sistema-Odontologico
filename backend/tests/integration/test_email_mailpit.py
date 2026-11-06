"""Envio real a Mailpit y lectura por su API HTTP (spec email-sending).

Corre en el contenedor (``mailpit:1025`` y ``mailpit:8025``). Cada test usa un asunto unico y
borra solo sus mensajes, para no tocar los demas emails del entorno.
"""

from __future__ import annotations

import json
import socket
import urllib.parse
import urllib.request
import uuid
from collections.abc import Iterator
from typing import Any

import pytest

from app.domain.notifications import EmailSendError, OutgoingEmail
from app.infrastructure.email.smtp import SmtpEmailSender

pytestmark = pytest.mark.integration

MAILPIT_HOST = "mailpit"
API = f"http://{MAILPIT_HOST}:8025/api/v1"


def _call(path: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"{API}{path}", data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
        payload = response.read()
    return json.loads(payload) if payload.startswith((b"{", b"[")) else payload


def _find(subject: str) -> list[dict[str, Any]]:
    found = _call(f"/search?query={urllib.parse.quote(f'subject:{subject}')}")
    messages: list[dict[str, Any]] = found["messages"]
    return messages


@pytest.fixture
def subject() -> Iterator[str]:
    token = f"Prueba-{uuid.uuid4().hex[:10]}"
    yield token
    ids = [message["ID"] for message in _find(token)]
    if ids:
        _call("/messages", method="DELETE", body={"IDs": ids})


def sender(port: int = 1025, host: str = MAILPIT_HOST) -> SmtpEmailSender:
    return SmtpEmailSender(
        host=host,
        port=port,
        user="",
        password="",
        use_tls=False,
        sender="turnos@consultorio.test",
    )


def test_a_message_reaches_mailpit_with_sender_recipient_subject_and_accents(
    subject: str,
) -> None:
    body = "Hola, Juan Peña Gómez: miércoles 10:00 h"

    sender().send(OutgoingEmail("juan.perez@example.com", subject, body))

    [message] = _find(subject)
    assert message["From"]["Address"] == "turnos@consultorio.test"
    assert [to["Address"] for to in message["To"]] == ["juan.perez@example.com"]
    assert message["Subject"] == subject
    full = _call(f"/message/{message['ID']}")
    assert full["Text"].strip() == body


def test_a_second_message_with_other_data_is_delivered_independently(subject: str) -> None:
    sender().send(OutgoingEmail("ana.gomez@example.com", subject, "Año nuevo, niña"))

    [message] = _find(subject)
    assert [to["Address"] for to in message["To"]] == ["ana.gomez@example.com"]
    assert _call(f"/message/{message['ID']}")["Text"].strip() == "Año nuevo, niña"


def test_a_server_that_is_not_listening_is_a_temporary_failure() -> None:
    with socket.socket() as probe:
        probe.bind(("", 0))
        free_port = probe.getsockname()[1]

    with pytest.raises(EmailSendError) as caught:
        sender(port=free_port, host="127.0.0.1").send(
            OutgoingEmail("juan.perez@example.com", "Sin servidor", "Texto")
        )

    assert caught.value.temporary is True
