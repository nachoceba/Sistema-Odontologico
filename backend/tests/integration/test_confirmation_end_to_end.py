"""Confirmacion de punta a punta: agendar, cola real (Redis), worker, SMTP real (Mailpit) y
fila ``sent`` en PostgreSQL (spec local-environment y notification-tasks).

Usa la base de pruebas y una cola propia del test para no mezclarse con el ``worker`` del
entorno, que trabaja sobre la base de desarrollo: dentro del proceso corre un worker real de
Celery que escucha solo esa cola. Los mensajes de Mailpit se borran al terminar.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from datetime import time as dtime
from zoneinfo import ZoneInfo

import pytest
from celery import Celery
from celery.contrib.testing.worker import start_worker
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.application.appointments import AgendaDeps, book_appointment
from app.application.notifications import RequeueDeps, requeue_pending
from app.domain.auth import Principal, Role
from app.infrastructure.db.repositories import (
    SqlAlchemyAgendaUnitOfWork,
    SqlAlchemyAppointmentRepository,
    SqlAlchemyClinicSettingsRepository,
    SqlAlchemyNotificationRepository,
    SqlAlchemyPatientRepository,
    SqlAlchemyProfessionalRepository,
    SqlAlchemyTimeOffRepository,
    SqlAlchemyWorkingHoursRepository,
)
from app.infrastructure.tasks import wiring
from app.infrastructure.tasks.celery_app import celery_app
from app.infrastructure.tasks.dispatcher import CeleryNotificationDispatcher
from tests.integration.db.helpers import (
    World,
    insert_working_hours,
    make_world,
)
from tests.mailpit_support import mailpit as _mailpit
from tests.mailpit_support import messages_to as _messages_to

BA = ZoneInfo("America/Argentina/Buenos_Aires")
WAIT_SECONDS = 20.0
FAST_SECONDS = 5.0


def _next_monday_at_10() -> datetime:
    day = (datetime.now(BA) + timedelta(days=7)).date()
    day += timedelta(days=(7 - day.weekday()) % 7)
    return datetime.combine(day, dtime(10, 0), tzinfo=BA).astimezone(UTC)


@pytest.fixture
def scene(engine: Engine) -> Iterator[tuple[World, str]]:
    """Dos profesionales, un paciente con un email unico y su horario de lunes."""
    address = f"e2e-{uuid.uuid4().hex[:10]}@example.com"
    with engine.begin() as connection:
        world = make_world(connection)
        insert_working_hours(connection, world.dra_a, 0, dtime(9), dtime(13))
        connection.execute(
            text("UPDATE patients SET email = :email WHERE id = :id"),
            {"email": address, "id": world.juan},
        )
    yield world, address
    ids = [message["ID"] for message in _messages_to(address)]
    if ids:
        _mailpit("/messages", method="DELETE", body={"IDs": ids})


def agenda_deps(sessions: sessionmaker[Session], publish: Callable[[str], None]) -> AgendaDeps:
    return AgendaDeps(
        appointments=SqlAlchemyAppointmentRepository(sessions),
        patients=SqlAlchemyPatientRepository(sessions),
        professionals=SqlAlchemyProfessionalRepository(sessions),
        working_hours=SqlAlchemyWorkingHoursRepository(sessions),
        time_off=SqlAlchemyTimeOffRepository(sessions),
        settings=SqlAlchemyClinicSettingsRepository(sessions),
        unit_of_work=lambda: SqlAlchemyAgendaUnitOfWork(sessions),
        dispatcher=CeleryNotificationDispatcher(publish),
        clock=lambda: datetime.now(UTC),
    )


def principal(world: World) -> Principal:
    return Principal(user_id=str(world.reception), role=Role.RECEPTIONIST)


def status_of(engine: Engine, appointment_id: str) -> tuple[str, str | None] | None:
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT status, error FROM email_notifications WHERE appointment_id = :id"),
            {"id": appointment_id},
        ).first()
    return None if row is None else (str(row[0]), row[1])


def test_booking_reaches_mailpit_through_redis_and_a_worker_and_marks_sent(
    engine: Engine,
    scene: tuple[World, str],
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world, address = scene
    queue = f"test-{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(wiring, "get_session_factory", lambda: session_factory)

    def publish(notification_id: str) -> None:
        celery_app.tasks["enviar_email"].apply_async(
            args=[notification_id], retry=False, queue=queue
        )

    with start_worker(
        celery_app, pool="solo", perform_ping_check=False, queues=[queue], loglevel="WARNING"
    ):
        appointment = book_appointment(
            agenda_deps(session_factory, publish),
            principal(world),
            patient_id=str(world.juan),
            professional_id=str(world.dra_a),
            starts_at=_next_monday_at_10(),
        )
        deadline = time.monotonic() + WAIT_SECONDS
        while time.monotonic() < deadline and status_of(engine, appointment.id) != ("sent", None):
            time.sleep(0.3)

    assert status_of(engine, appointment.id) == ("sent", None)
    [message] = _messages_to(address)
    assert message["Subject"].startswith("Turno confirmado:")
    full = _mailpit(f"/message/{message['ID']}")
    assert "Hola, Juan Perez:" in full["Text"]
    assert "Dra. A" in full["Text"]


def test_with_an_unreachable_redis_booking_is_fast_and_the_confirmation_stays_pending(
    engine: Engine, scene: tuple[World, str], session_factory: sessionmaker[Session]
) -> None:
    world, _ = scene
    broken = Celery("sin-redis", broker="redis://127.0.0.1:1/0")
    broken.conf.broker_transport_options = dict(celery_app.conf.broker_transport_options)

    def publish(notification_id: str) -> None:
        broken.send_task("enviar_email", args=[notification_id], retry=False)

    started = time.monotonic()
    appointment = book_appointment(
        agenda_deps(session_factory, publish),
        principal(world),
        patient_id=str(world.juan),
        professional_id=str(world.dra_a),
        starts_at=_next_monday_at_10(),
    )
    elapsed = time.monotonic() - started

    assert elapsed < FAST_SECONDS
    assert status_of(engine, appointment.id) == ("pending", None)


def test_with_the_worker_stopped_the_email_leaves_after_a_requeue_pass(
    engine: Engine,
    scene: tuple[World, str],
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world, address = scene
    queue = f"test-{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(wiring, "get_session_factory", lambda: session_factory)

    def publish(notification_id: str) -> None:
        celery_app.tasks["enviar_email"].apply_async(
            args=[notification_id], retry=False, queue=queue
        )

    def lost(notification_id: str) -> None:
        """La publicacion de agendar no llega a ningun worker."""
        return None

    appointment = book_appointment(
        agenda_deps(session_factory, lost),
        principal(world),
        patient_id=str(world.juan),
        professional_id=str(world.dra_a),
        starts_at=_next_monday_at_10(),
    )
    assert status_of(engine, appointment.id) == ("pending", None)
    assert _messages_to(address) == []

    requeue = RequeueDeps(
        notifications=SqlAlchemyNotificationRepository(session_factory),
        publish=publish,
        clock=lambda: datetime.now(UTC) + timedelta(minutes=10),
    )
    with start_worker(
        celery_app, pool="solo", perform_ping_check=False, queues=[queue], loglevel="WARNING"
    ):
        assert requeue_pending(requeue) == 1
        deadline = time.monotonic() + WAIT_SECONDS
        while time.monotonic() < deadline and status_of(engine, appointment.id) != ("sent", None):
            time.sleep(0.3)

    assert status_of(engine, appointment.id) == ("sent", None)
    assert len(_messages_to(address)) == 1
