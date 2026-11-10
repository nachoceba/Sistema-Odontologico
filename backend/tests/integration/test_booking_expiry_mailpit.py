"""Vencimiento de una reserva online con cola real (Redis), worker y SMTP real (Mailpit)
(specs online-booking-expiry y email-templates, C-16).

Usa la base de pruebas y una cola propia del test para no mezclarse con el ``worker`` del
entorno. Una reserva con el DNI de una ficha existente manda la verificacion al email de la
ficha y nunca al que se escribio. Los mensajes de Mailpit se borran al terminar.
"""

from __future__ import annotations

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

from app.application.appointments import AgendaDeps, cancel_appointment
from app.application.public_booking import (
    ExpiryDeps,
    PublicBookingDeps,
    book_online,
    expire_pending_bookings,
)
from app.core.config import get_settings
from app.core.security import generate_confirmation_token, hash_confirmation_token
from app.infrastructure.db.repositories import (
    SqlAlchemyAgendaUnitOfWork,
    SqlAlchemyAppointmentRepository,
    SqlAlchemyClinicSettingsRepository,
    SqlAlchemyPatientRepository,
    SqlAlchemyProfessionalRepository,
    SqlAlchemyTimeOffRepository,
    SqlAlchemyTreatmentRepository,
    SqlAlchemyWorkingHoursRepository,
)
from app.infrastructure.tasks import wiring
from app.infrastructure.tasks.celery_app import celery_app
from app.infrastructure.tasks.dispatcher import (
    CeleryNotificationDispatcher,
    CeleryVerificationDispatcher,
)
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
        treatments=SqlAlchemyTreatmentRepository(sessions),
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


def _expiry_deps(sessions: sessionmaker[Session], queue: str, now: datetime) -> ExpiryDeps:
    agenda = _agenda(sessions, queue)
    return ExpiryDeps(
        unit_of_work=agenda.unit_of_work, dispatcher=agenda.dispatcher, clock=lambda: now
    )


def _expired_notices(address: str) -> list[dict[str, str]]:
    return [m for m in messages_to(address) if "se canceló por falta" in m["Subject"]]


def test_an_expired_reservation_notifies_the_email_on_file_with_the_professional_and_local_hour(
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
        book_online(
            deps,
            professional_id=str(scene.world.dra_a),
            treatment_id=str(scene.world.limpieza),
            starts_at=_tomorrow_at_10(),
            document_number=scene.document,
            first_name="Juan",
            last_name="Perez",
            email=scene.typed,
            phone=None,
        )
        assert _wait_for(lambda: messages_to(scene.on_file))  # llego la verificacion

        expired = expire_pending_bookings(
            _expiry_deps(session_factory, queue, datetime.now(UTC) + timedelta(hours=2))
        )
        [notice] = _wait_for(lambda: _expired_notices(scene.on_file))
        body = mailpit(f"/message/{notice['ID']}")["Text"]

    assert expired == 1
    clinic = SqlAlchemyClinicSettingsRepository(session_factory).get().clinic_name
    assert notice["Subject"] == f"Tu turno en {clinic} se canceló por falta de confirmación"
    assert "Profesional: Dra. A" in body
    assert "Tratamiento: Limpieza dental" in body
    assert "10:00" in body  # hora local del consultorio, no UTC
    assert "13:00" not in body
    assert f"{get_settings().PUBLIC_APP_URL}/turnos." in body
    assert scene.document not in body
    assert _expired_notices(scene.typed) == []
    assert _kinds(engine) == ["booking_expired"]
    with engine.connect() as connection:
        status = connection.execute(text("SELECT status::text, cancel_reason FROM appointments"))
        assert tuple(status.one()) == ("cancelled", "Reserva online no confirmada")


def test_a_reservation_cancelled_by_the_reception_gets_no_expiry_notice(
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
        book_online(
            deps,
            professional_id=str(scene.world.dra_a),
            treatment_id=str(scene.world.limpieza),
            starts_at=_tomorrow_at_10(),
            document_number=scene.document,
            first_name="Juan",
            last_name="Perez",
            email=scene.typed,
            phone=None,
        )
        assert _wait_for(lambda: messages_to(scene.on_file))
        with engine.connect() as connection:
            appointment_id = str(
                connection.execute(text("SELECT id FROM appointments")).scalar_one()
            )
        cancel_appointment(deps.agenda, appointment_id, "Cancela la recepción")

        expired = expire_pending_bookings(
            _expiry_deps(session_factory, queue, datetime.now(UTC) + timedelta(hours=2))
        )
        time.sleep(1.5)  # margen para que un aviso indebido llegara a Mailpit

    assert expired == 0
    assert _expired_notices(scene.on_file) == []
    assert _kinds(engine) == []
