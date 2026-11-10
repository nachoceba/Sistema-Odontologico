"""Reserva online de punta a punta con cola real (Redis), worker y SMTP real (Mailpit)
(specs public-booking, notification-tasks y reminder-scheduling, C-15).

Usa la base de pruebas y una cola propia del test para no mezclarse con el ``worker`` del
entorno. Una reserva con el DNI de una ficha existente manda la verificacion al email de la
ficha y nunca al que se escribio. Los mensajes de Mailpit se borran al terminar.
"""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from datetime import time as dtime
from zoneinfo import ZoneInfo

import pytest
from celery.contrib.testing.worker import start_worker
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.application.appointments import AgendaDeps
from app.application.public_booking import PublicBookingDeps, book_online, confirm_online_booking
from app.core.config import get_settings
from app.core.security import generate_confirmation_token, hash_confirmation_token
from app.infrastructure.db.repositories import (
    SqlAlchemyAgendaUnitOfWork,
    SqlAlchemyAppointmentRepository,
    SqlAlchemyClinicSettingsRepository,
    SqlAlchemyPatientRepository,
    SqlAlchemyProfessionalRepository,
    SqlAlchemyTimeOffRepository,
    SqlAlchemyWorkingHoursRepository,
)
from app.infrastructure.tasks import wiring
from app.infrastructure.tasks.celery_app import celery_app
from app.infrastructure.tasks.dispatcher import (
    CeleryNotificationDispatcher,
    CeleryVerificationDispatcher,
)
from app.infrastructure.tasks.notifications import enviar_recordatorios
from tests.integration.db.helpers import World, insert_working_hours, make_world
from tests.mailpit_support import delete_messages, mailpit, messages_to

BA = ZoneInfo("America/Argentina/Buenos_Aires")
WAIT_SECONDS = 20.0


def _tomorrow_at_10() -> datetime:
    tomorrow = datetime.now(BA).date() + timedelta(days=1)
    return datetime.combine(tomorrow, dtime(10, 0), tzinfo=BA).astimezone(UTC)


class Scene:
    def __init__(self, world: World, on_file: str, typed: str, document: str) -> None:
        self.world = world
        self.on_file = on_file
        self.typed = typed
        self.document = document


@pytest.fixture
def scene(engine: Engine) -> Iterator[Scene]:
    on_file = f"ficha-{uuid.uuid4().hex[:10]}@example.com"
    typed = f"escrito-{uuid.uuid4().hex[:10]}@example.com"
    with engine.begin() as connection:
        world = make_world(connection)
        for weekday in range(7):
            insert_working_hours(connection, world.dra_a, weekday, dtime(9), dtime(13))
        connection.execute(
            text("UPDATE patients SET email = :email WHERE id = :id"),
            {"email": on_file, "id": world.juan},
        )
        document = str(
            connection.execute(
                text("SELECT document_number FROM patients WHERE id = :id"), {"id": world.juan}
            ).scalar_one()
        )
    yield Scene(world, on_file, typed, document)
    for address in (on_file, typed):
        delete_messages(messages_to(address))


def _agenda(sessions: sessionmaker[Session], queue: str) -> AgendaDeps:
    def publish(notification_id: str) -> None:
        celery_app.tasks["enviar_email"].apply_async(
            args=[notification_id], retry=False, queue=queue
        )

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


def _deps(sessions: sessionmaker[Session], queue: str) -> PublicBookingDeps:
    def verify(appointment_id: str, token: str) -> None:
        celery_app.tasks["enviar_verificacion_reserva"].apply_async(
            args=[appointment_id, token], retry=False, queue=queue
        )

    return PublicBookingDeps(
        agenda=_agenda(sessions, queue),
        new_token=generate_confirmation_token,
        hash_token=hash_confirmation_token,
        hold_minutes=60,
        verification=CeleryVerificationDispatcher(verify),
    )


def _wait_for(find: Callable[[], list[dict[str, str]]]) -> list[dict[str, str]]:
    deadline = time.monotonic() + WAIT_SECONDS
    found = find()
    while not found and time.monotonic() < deadline:
        time.sleep(0.3)
        found = find()
    return found


def _kinds(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT kind FROM email_notifications ORDER BY created_at")
        ).all()
    return [str(row[0]) for row in rows]


def test_the_verification_goes_to_the_email_on_file_and_confirming_sends_the_confirmation(
    engine: Engine,
    scene: Scene,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = f"test-{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(wiring, "get_session_factory", lambda: session_factory)
    deps = _deps(session_factory, queue)

    with start_worker(
        celery_app, pool="solo", perform_ping_check=False, queues=[queue], loglevel="WARNING"
    ):
        booked = book_online(
            deps,
            professional_id=str(scene.world.dra_a),
            starts_at=_tomorrow_at_10(),
            document_number=scene.document,
            first_name="Juan",
            last_name="Perez",
            email=scene.typed,
            phone=None,
        )
        [verification] = _wait_for(lambda: messages_to(scene.on_file))
        body = mailpit(f"/message/{verification['ID']}")["Text"]
        token_match = re.search(r"/turnos/confirmar#token=([\w-]+)", body)

        assert verification["Subject"].startswith("Confirmá tu turno")
        assert token_match is not None
        assert body.count(get_settings().PUBLIC_APP_URL) >= 1
        assert "Dra. A" in body
        assert scene.document not in body
        assert messages_to(scene.typed) == []
        assert booked.professional_display_name == "Dra. A"

        # Un pendiente no recibe recordatorio ni siquiera con la pasada forzada.
        summary = enviar_recordatorios.apply(kwargs={"forzar": True}, throw=True).get()
        assert summary["processed"] == 0
        assert "reminder" not in _kinds(engine)

        confirm_online_booking(deps, token_match.group(1))
        confirmations = _wait_for(
            lambda: [
                m
                for m in messages_to(scene.on_file)
                if m["Subject"].startswith("Turno confirmado:")
            ]
        )

    assert len(confirmations) == 1
    assert messages_to(scene.typed) == []
    assert _kinds(engine) == ["confirmation"]
