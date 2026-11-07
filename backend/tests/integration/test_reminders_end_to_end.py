"""Recordatorio de punta a punta: pasada forzada, cola real (Redis), worker, SMTP real (Mailpit)
y fila ``reminder`` ``sent`` en PostgreSQL (specs reminder-scheduling y local-environment).

Usa la base de pruebas y una cola propia del test para no mezclarse con el ``worker`` del
entorno, que trabaja sobre la base de desarrollo. Los mensajes de Mailpit se borran al terminar.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from datetime import time as dtime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from celery.contrib.testing.worker import start_worker
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.tasks import wiring
from app.infrastructure.tasks.celery_app import celery_app
from app.infrastructure.tasks.notifications import enviar_recordatorios
from tests.integration.db.helpers import World, insert_appointment, make_world

BA = ZoneInfo("America/Argentina/Buenos_Aires")
MAILPIT_API = "http://mailpit:8025/api/v1"
WAIT_SECONDS = 20.0


def _mailpit(path: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"{MAILPIT_API}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
        payload = response.read()
    return json.loads(payload) if payload.startswith((b"{", b"[")) else payload


def _messages_to(address: str) -> list[dict[str, Any]]:
    query = urllib.parse.quote(f"to:{address}")
    messages: list[dict[str, Any]] = _mailpit(f"/search?query={query}")["messages"]
    return messages


def _tomorrow_at_10() -> datetime:
    tomorrow = datetime.now(BA).date() + timedelta(days=1)
    return datetime.combine(tomorrow, dtime(10, 0), tzinfo=BA).astimezone(UTC)


@pytest.fixture
def scene(engine: Engine) -> Iterator[tuple[World, str, str]]:
    """Un turno para mañana de un paciente con un email unico; devuelve su id y su email."""
    address = f"rec-{uuid.uuid4().hex[:10]}@example.com"
    with engine.begin() as connection:
        world = make_world(connection)
        connection.execute(
            text("UPDATE patients SET email = :email WHERE id = :id"),
            {"email": address, "id": world.juan},
        )
        start = _tomorrow_at_10()
        appointment = insert_appointment(connection, world, start, start + timedelta(minutes=30))
    yield world, str(appointment), address
    ids = [message["ID"] for message in _messages_to(address)]
    if ids:
        _mailpit("/messages", method="DELETE", body={"IDs": ids})


def reminder_rows(engine: Engine, appointment_id: str) -> list[tuple[str, str, str | None]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT kind, status, error FROM email_notifications "
                "WHERE appointment_id = :id ORDER BY created_at"
            ),
            {"id": appointment_id},
        ).all()
    return [(str(r[0]), str(r[1]), r[2]) for r in rows]


def test_a_forced_pass_sends_tomorrows_reminder_to_mailpit_and_a_second_pass_adds_nothing(
    engine: Engine,
    scene: tuple[World, str, str],
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, appointment_id, address = scene
    queue = f"test-{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(wiring, "get_session_factory", lambda: session_factory)

    with start_worker(
        celery_app, pool="solo", perform_ping_check=False, queues=[queue], loglevel="WARNING"
    ):
        enviar_recordatorios.apply_async(kwargs={"forzar": True}, queue=queue)
        deadline = time.monotonic() + WAIT_SECONDS
        while time.monotonic() < deadline and reminder_rows(engine, appointment_id) != [
            ("reminder", "sent", None)
        ]:
            time.sleep(0.3)

    assert reminder_rows(engine, appointment_id) == [("reminder", "sent", None)]
    [message] = _messages_to(address)
    assert message["Subject"].startswith("Recordatorio de turno")
    full = _mailpit(f"/message/{message['ID']}")
    assert "Te recordamos tu turno." in full["Text"]
    assert "Dra. A" in full["Text"]

    second = enviar_recordatorios.apply(kwargs={"forzar": True}, throw=True).get()

    assert second["processed"] == 0
    assert len(_messages_to(address)) == 1
    assert reminder_rows(engine, appointment_id) == [("reminder", "sent", None)]
