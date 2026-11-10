"""Vencimiento de reservas contra PostgreSQL real: carreras con la confirmacion y entre pasadas
(spec online-booking-expiry, C-16, regla dura 6).

Una transaccion retiene la fila con un evento y la otra corre mientras tanto: lo que decide es el
bloqueo de fila (``FOR UPDATE`` de la confirmacion, ``FOR UPDATE SKIP LOCKED`` del vencimiento),
no el orden en que se lanzan los hilos. Cada espera tiene limite para que un fallo no cuelgue.
"""

from __future__ import annotations

import threading
import time as clock_time
from collections.abc import Callable, Iterator
from datetime import datetime, time
from types import TracebackType
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.application.appointments import AgendaDeps
from app.application.public_booking import (
    ExpiryDeps,
    PublicBookingDeps,
    confirm_online_booking,
    expire_pending_bookings,
)
from app.core.security import hash_confirmation_token
from app.domain.appointments import AgendaUnitOfWork, NewAppointment
from app.domain.appointments.errors import SlotTakenError
from app.domain.public_booking.errors import ConfirmationLinkInvalidError
from app.infrastructure.db.repositories import (
    SqlAlchemyAgendaUnitOfWork,
    SqlAlchemyAppointmentRepository,
    SqlAlchemyClinicSettingsRepository,
    SqlAlchemyPatientRepository,
    SqlAlchemyProfessionalRepository,
    SqlAlchemyTimeOffRepository,
    SqlAlchemyWorkingHoursRepository,
)
from app.infrastructure.notifications import NoOpNotificationDispatcher
from tests.integration.db.helpers import World, at, insert_working_hours, make_world, scalar
from tests.integration.db.test_appointment_concurrency import (
    JOIN_SECONDS,
    LOCK_TIMEOUT,
    finish,
    run_in_thread,
)

PENDING_UNTIL = at(9)
BEFORE_DEADLINE = at(8, 50)
AFTER_DEADLINE = at(9, 5)
TOKEN = "token-de-prueba"


@pytest.fixture
def world(engine: Engine) -> World:
    with engine.begin() as connection:
        made = make_world(connection)
        insert_working_hours(connection, made.dra_a, 0, time(9), time(13))
    return made


@pytest.fixture
def sessions(engine: Engine) -> Iterator[sessionmaker[Session]]:
    limited = create_engine(engine.url, connect_args={"options": LOCK_TIMEOUT})
    yield sessionmaker(limited, expire_on_commit=False)
    limited.dispose()


class HoldingUnitOfWork:
    """Unidad real que, antes de confirmar, avisa que ya tomo las filas y espera la orden."""

    def __init__(
        self,
        inner: SqlAlchemyAgendaUnitOfWork,
        holding: threading.Event,
        release: threading.Event,
    ) -> None:
        self._inner = inner
        self._holding = holding
        self._release = release
        self.appointments = inner.appointments
        self.notifications = inner.notifications
        self.patients = inner.patients

    def __enter__(self) -> HoldingUnitOfWork:
        self._inner.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._holding.set()
        assert self._release.wait(JOIN_SECONDS), "nadie libero la transaccion"
        self._inner.__exit__(exc_type, exc, traceback)


def expiry_deps(
    sessions: sessionmaker[Session],
    now: datetime,
    *,
    holding: threading.Event | None = None,
    release: threading.Event | None = None,
) -> ExpiryDeps:
    def unit_of_work() -> AgendaUnitOfWork:
        real = SqlAlchemyAgendaUnitOfWork(sessions)
        if holding is None or release is None:
            return real  # type: ignore[return-value]
        return HoldingUnitOfWork(real, holding, release)  # type: ignore[return-value]

    return ExpiryDeps(
        unit_of_work=unit_of_work, dispatcher=NoOpNotificationDispatcher(), clock=lambda: now
    )


def booking_deps(
    sessions: sessionmaker[Session],
    now: datetime,
    unit_of_work: Callable[[], AgendaUnitOfWork] | None = None,
) -> PublicBookingDeps:
    return PublicBookingDeps(
        agenda=AgendaDeps(
            appointments=SqlAlchemyAppointmentRepository(sessions),
            patients=SqlAlchemyPatientRepository(sessions),
            professionals=SqlAlchemyProfessionalRepository(sessions),
            working_hours=SqlAlchemyWorkingHoursRepository(sessions),
            time_off=SqlAlchemyTimeOffRepository(sessions),
            settings=SqlAlchemyClinicSettingsRepository(sessions),
            unit_of_work=unit_of_work or (lambda: SqlAlchemyAgendaUnitOfWork(sessions)),  # type: ignore[arg-type,return-value]
            dispatcher=NoOpNotificationDispatcher(),
            clock=lambda: now,
        ),
        new_token=lambda: TOKEN,
        hash_token=hash_confirmation_token,
        hold_minutes=60,
        verification=_NoVerification(),
    )


class _NoVerification:
    def dispatch(self, appointment_id: str, token: str) -> None:
        return None


def pend(sessions: sessionmaker[Session], world: World, hour: int, token: str = TOKEN) -> str:
    saved = SqlAlchemyAppointmentRepository(sessions).add_pending(
        NewAppointment(
            patient_id=str(world.juan),
            professional_id=str(world.dra_a),
            starts_at=at(hour),
            ends_at=at(hour, 30),
            created_by=None,
        ),
        hash_confirmation_token(token),
        PENDING_UNTIL,
    )
    return saved.id


def count(engine: Engine, sql: str, **params: Any) -> int:
    with engine.connect() as connection:
        return int(scalar(connection, sql, **params))


def kinds(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        return sorted(
            row[0] for row in connection.execute(text("SELECT kind::text FROM email_notifications"))
        )


def wait_until_blocked(engine: Engine, fragment: str) -> None:
    """Espera a que otra conexion este bloqueada por un lock ejecutando ``fragment``."""
    deadline = clock_time.monotonic() + JOIN_SECONDS
    while clock_time.monotonic() < deadline:
        with engine.connect() as connection:
            waiting = connection.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE wait_event_type = 'Lock' AND query ILIKE :fragment"
                ),
                {"fragment": f"%{fragment}%"},
            ).scalar_one()
        if waiting:
            return
        clock_time.sleep(0.05)
    pytest.fail("la otra transaccion nunca quedo esperando el lock")


def test_confirmation_wins_when_it_holds_the_row_and_the_expiry_skips_it(
    engine: Engine, world: World, sessions: sessionmaker[Session]
) -> None:
    appointment_id = pend(sessions, world, 10)
    holding, release = threading.Event(), threading.Event()
    held = booking_deps(
        sessions,
        BEFORE_DEADLINE,
        unit_of_work=lambda: HoldingUnitOfWork(  # type: ignore[return-value]
            SqlAlchemyAgendaUnitOfWork(sessions), holding, release
        ),
    )

    confirming = run_in_thread(lambda: confirm_online_booking(held, TOKEN))
    assert holding.wait(JOIN_SECONDS)
    # La confirmacion ya tomo la fila (FOR UPDATE) y no hizo commit: el vencimiento no la espera.
    expired = expire_pending_bookings(expiry_deps(sessions, AFTER_DEADLINE))
    release.set()
    finish(confirming)

    assert confirming[1].error is None
    assert expired == 0
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT status::text, pending_until, cancel_reason FROM appointments")
        ).one()
    assert (row[0], row[1], row[2]) == ("scheduled", None, None)
    assert kinds(engine) == ["confirmation"]
    assert appointment_id


def test_expiry_wins_when_it_holds_the_row_and_the_confirmation_gets_410(
    engine: Engine, world: World, sessions: sessionmaker[Session]
) -> None:
    pend(sessions, world, 10)
    holding, release = threading.Event(), threading.Event()

    expiring = run_in_thread(
        lambda: expire_pending_bookings(
            expiry_deps(sessions, AFTER_DEADLINE, holding=holding, release=release)
        )
    )
    assert holding.wait(JOIN_SECONDS)
    # El vencimiento ya cancelo la fila sin commit: la confirmacion queda esperando su FOR UPDATE.
    confirming = run_in_thread(
        lambda: confirm_online_booking(booking_deps(sessions, BEFORE_DEADLINE), TOKEN)
    )
    wait_until_blocked(engine, "FOR UPDATE")
    release.set()
    finish(expiring, confirming)

    assert expiring[1].error is None
    assert expiring[1].value == 1
    assert isinstance(confirming[1].error, ConfirmationLinkInvalidError)
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT status::text, cancel_reason, pending_until FROM appointments")
        ).one()
    assert (row[0], row[1], row[2]) == ("cancelled", "Reserva online no confirmada", None)
    assert kinds(engine) == ["booking_expired"]


def test_two_simultaneous_passes_cancel_each_reservation_once_and_leave_one_notice_each(
    engine: Engine, world: World, sessions: sessionmaker[Session]
) -> None:
    pend(sessions, world, 10, "token-uno")
    pend(sessions, world, 11, "token-dos")
    holding, release = threading.Event(), threading.Event()

    first = run_in_thread(
        lambda: expire_pending_bookings(
            expiry_deps(sessions, AFTER_DEADLINE, holding=holding, release=release)
        )
    )
    assert holding.wait(JOIN_SECONDS)
    # La primera pasada tiene las dos filas tomadas: la segunda las saltea sin esperar.
    second = expire_pending_bookings(expiry_deps(sessions, AFTER_DEADLINE))
    release.set()
    finish(first)

    assert first[1].error is None
    assert (first[1].value, second) == (2, 0)
    assert count(engine, "SELECT count(*) FROM appointments WHERE status = 'cancelled'") == 2
    assert kinds(engine) == ["booking_expired", "booking_expired"]
    # Una tercera pasada ya no encuentra nada.
    assert expire_pending_bookings(expiry_deps(sessions, AFTER_DEADLINE)) == 0
    assert count(engine, "SELECT count(*) FROM email_notifications") == 2


def test_the_cancelled_slot_is_free_for_the_reception_after_expiring(
    engine: Engine, world: World, sessions: sessionmaker[Session]
) -> None:
    """Regla dura 6: la franja vuelve a ser agendable y el constraint sigue protegiendola."""
    pend(sessions, world, 10)
    repo = SqlAlchemyAppointmentRepository(sessions)
    staff = NewAppointment(
        patient_id=str(world.ana),
        professional_id=str(world.dra_a),
        starts_at=at(10),
        ends_at=at(10, 30),
        created_by=str(world.reception),
    )
    with pytest.raises(SlotTakenError):
        repo.add(staff)

    expire_pending_bookings(expiry_deps(sessions, AFTER_DEADLINE))

    assert repo.add(staff).starts_at == at(10)
    with pytest.raises(SlotTakenError):
        repo.add(staff)  # ahora la ocupa la recepcion
