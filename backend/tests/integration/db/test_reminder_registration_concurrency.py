"""Alta del recordatorio mientras se reprograma o cancela el turno, contra PostgreSQL real.

La primera sesion modifica el turno (lo tiene con ``FOR UPDATE``) y no termina su transaccion;
la segunda intenta registrar el ``reminder`` del horario viejo y debe esperar. Al confirmarse la
primera, el alta vuelve a evaluar el turno con el dato confirmado y no registra nada
(spec notification-registration, design D-4). Las esperas tienen limite para no colgar la suite.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.domain.appointments import AgendaUnitOfWork, AppointmentStatus, Notification
from app.infrastructure.db.repositories import (
    SqlAlchemyAgendaUnitOfWork,
    SqlAlchemyNotificationRepository,
)
from tests.integration.db.helpers import at, insert_appointment, make_world

JOIN_SECONDS = 20.0
LOCK_TIMEOUT = "-c lock_timeout=10000"
WAIT_SECONDS = 1.0


@pytest.fixture
def sessions(engine: Engine) -> Iterator[sessionmaker[Session]]:
    limited = create_engine(engine.url, connect_args={"options": LOCK_TIMEOUT})
    yield sessionmaker(limited, expire_on_commit=False)
    limited.dispose()


@pytest.fixture
def appointment_id(engine: Engine) -> str:
    with engine.begin() as connection:
        world = make_world(connection)
        return str(insert_appointment(connection, world, at(10), at(10, 30)))


def _reschedule(uow: AgendaUnitOfWork, appointment_id: str) -> None:
    uow.appointments.reschedule(appointment_id, at(11), at(11, 30))


def _cancel(uow: AgendaUnitOfWork, appointment_id: str) -> None:
    uow.appointments.change_status(appointment_id, AppointmentStatus.CANCELLED, "motivo")


@pytest.mark.parametrize("change", [_reschedule, _cancel], ids=["reprogramar", "cancelar"])
def test_a_reminder_for_the_old_start_waits_and_is_not_registered_after_the_change_commits(
    engine: Engine,
    sessions: sessionmaker[Session],
    appointment_id: str,
    change: Callable[[AgendaUnitOfWork, str], None],
) -> None:
    results: list[Notification | None] = []
    second = SqlAlchemyNotificationRepository(sessions)

    def register_old_start() -> None:
        results.append(second.add_pending_reminder(appointment_id, at(10)))

    thread = threading.Thread(target=register_old_start, daemon=True)
    with SqlAlchemyAgendaUnitOfWork(sessions) as first:
        change(first, appointment_id)
        thread.start()
        thread.join(WAIT_SECONDS)
        assert thread.is_alive(), "el alta no espero a la modificacion en curso"
    thread.join(JOIN_SECONDS)
    assert not thread.is_alive(), "el alta quedo esperando despues de confirmar"

    assert results == [None]
    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT count(*) FROM email_notifications WHERE kind = 'reminder'")
        ).scalar_one()
    assert count == 0


def test_a_reminder_registered_before_an_unrelated_open_transaction_still_succeeds(
    sessions: sessionmaker[Session], appointment_id: str
) -> None:
    # Control: sin modificacion en curso el mismo alta registra el recordatorio.
    saved = SqlAlchemyNotificationRepository(sessions).add_pending_reminder(appointment_id, at(10))

    assert saved is not None
    assert saved.appointment_starts_at == at(10)
