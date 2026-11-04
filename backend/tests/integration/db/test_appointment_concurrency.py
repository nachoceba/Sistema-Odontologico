"""Dos pedidos simultaneos por el mismo horario contra PostgreSQL real (spec
appointment-unit-of-work, regla dura 3 y 6, D-9).

Es una prueba de caracterizacion: el constraint ``ex_appointments_no_overlap`` ya existe desde
C-02. Lo que prueba es que, aunque las validaciones del dominio de ambos pedidos pasen, la base
deja pasar exactamente uno y el otro termina con ``SlotTakenError``. Cada espera tiene limite
(``lock_timeout`` en la conexion y ``join`` con timeout) para que un fallo no cuelgue la suite.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from datetime import datetime, time, timedelta
from types import TracebackType
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.application.appointments import AgendaDeps, book_appointment, reschedule_appointment
from app.domain.appointments import (
    Appointment,
    AppointmentRepository,
    AppointmentStatus,
    NewAppointment,
)
from app.domain.appointments.errors import SlotTakenError
from app.domain.auth import Principal, Role
from app.infrastructure.db.models import AppointmentModel
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
from tests.integration.db.helpers import (
    World,
    at,
    insert_appointment,
    insert_working_hours,
    make_world,
    scalar,
)

JOIN_SECONDS = 20.0
LOCK_TIMEOUT = "-c lock_timeout=10000"
NOW = at(10, day=3)  # sabado 3 de octubre de 2026, 10:00 local


@pytest.fixture
def world(engine: Engine) -> World:
    with engine.begin() as connection:
        made = make_world(connection)
        for professional in (made.dra_a, made.dr_b):
            insert_working_hours(connection, professional, 0, time(9), time(13))
    return made


@pytest.fixture
def sessions(engine: Engine) -> Iterator[sessionmaker[Session]]:
    """Sesiones con ``lock_timeout``: una espera de lock que no termina falla en vez de colgar."""
    limited = create_engine(engine.url, connect_args={"options": LOCK_TIMEOUT})
    yield sessionmaker(limited, expire_on_commit=False)
    limited.dispose()


class Outcome:
    """Resultado de una operacion corrida en un hilo: el valor o la excepcion."""

    def __init__(self) -> None:
        self.value: Any = None
        self.error: BaseException | None = None


def run_in_thread(operation: Callable[[], Any]) -> tuple[threading.Thread, Outcome]:
    outcome = Outcome()

    def target() -> None:
        try:
            outcome.value = operation()
        except BaseException as error:  # noqa: BLE001  (se reporta en el hilo principal)
            outcome.error = error

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    return thread, outcome


def finish(*pairs: tuple[threading.Thread, Outcome]) -> None:
    for thread, _ in pairs:
        thread.join(JOIN_SECONDS)
        assert not thread.is_alive(), "un hilo quedo colgado esperando un lock"


def scheduled_count(engine: Engine, professional: Any) -> int:
    with engine.connect() as connection:
        return int(
            scalar(
                connection,
                "SELECT count(*) FROM appointments WHERE professional_id = :p "
                "AND status = 'scheduled'",
                p=professional,
            )
        )


def new_appointment(
    world: World, starts_at: datetime, *, professional: Any = None
) -> NewAppointment:
    return NewAppointment(
        patient_id=str(world.ana),
        professional_id=str(world.dra_a),
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=30),
        created_by=str(world.reception),
    )


class GatedAppointments:
    """Frena cada escritura hasta que todos los pedidos hayan validado (D-9, variante B)."""

    def __init__(self, inner: AppointmentRepository, gate: threading.Barrier) -> None:
        self._inner = inner
        self._gate = gate

    def add(self, new: NewAppointment) -> Appointment:
        self._gate.wait(timeout=JOIN_SECONDS)
        return self._inner.add(new)

    def reschedule(
        self, appointment_id: str, starts_at: datetime, ends_at: datetime
    ) -> Appointment:
        self._gate.wait(timeout=JOIN_SECONDS)
        return self._inner.reschedule(appointment_id, starts_at, ends_at)

    def get(self, appointment_id: str) -> Appointment | None:
        return self._inner.get(appointment_id)

    def change_status(
        self, appointment_id: str, status: AppointmentStatus, cancel_reason: str | None = None
    ) -> Appointment:
        return self._inner.change_status(appointment_id, status, cancel_reason)

    def list_for_professional(
        self, professional_id: str, start: datetime, end: datetime | None = None
    ) -> list[Appointment]:
        return self._inner.list_for_professional(professional_id, start, end)

    def list_for_patient(
        self, patient_id: str, start: datetime, end: datetime | None = None
    ) -> list[Appointment]:
        return self._inner.list_for_patient(patient_id, start, end)


class GatedUnitOfWork:
    """La unidad de trabajo real, con la escritura de turnos frenada por la barrera."""

    def __init__(self, inner: SqlAlchemyAgendaUnitOfWork, gate: threading.Barrier) -> None:
        self._inner = inner
        self.appointments = GatedAppointments(inner.appointments, gate)
        self.notifications = inner.notifications

    def __enter__(self) -> GatedUnitOfWork:
        self._inner.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._inner.__exit__(exc_type, exc, traceback)


def gated_deps(sessions: sessionmaker[Session], gate: threading.Barrier) -> AgendaDeps:
    return AgendaDeps(
        appointments=SqlAlchemyAppointmentRepository(sessions),
        patients=SqlAlchemyPatientRepository(sessions),
        professionals=SqlAlchemyProfessionalRepository(sessions),
        working_hours=SqlAlchemyWorkingHoursRepository(sessions),
        time_off=SqlAlchemyTimeOffRepository(sessions),
        settings=SqlAlchemyClinicSettingsRepository(sessions),
        unit_of_work=lambda: GatedUnitOfWork(SqlAlchemyAgendaUnitOfWork(sessions), gate),
        dispatcher=NoOpNotificationDispatcher(),
        clock=lambda: NOW,
    )


def notification_rows(engine: Engine) -> list[tuple[str, str]]:
    with engine.connect() as connection:
        return [
            (str(row[0]), str(row[1]))
            for row in connection.execute(
                text("SELECT kind, status FROM email_notifications ORDER BY id")
            )
        ]


def principal_for(world: World) -> Principal:
    return Principal(user_id=str(world.reception), role=Role.RECEPTIONIST)


def test_a_second_session_waits_for_the_first_and_loses_with_slot_taken(
    engine: Engine, world: World, sessions: sessionmaker[Session]
) -> None:
    repo = SqlAlchemyAppointmentRepository(sessions)
    request = new_appointment(world, at(10))

    with sessions.begin() as first:
        first.add(
            AppointmentModel(
                patient_id=world.juan,
                professional_id=world.dra_a,
                starts_at=at(10),
                ends_at=at(10, 30),
                status=AppointmentStatus.SCHEDULED,
                created_by=world.reception,
            )
        )
        first.flush()  # la primera sesion tiene el horario sin confirmar todavia
        pair = run_in_thread(lambda: repo.add(request))
        pair[0].join(0.5)
        assert pair[0].is_alive(), "la segunda sesion debia quedar esperando el horario"
    finish(pair)

    assert isinstance(pair[1].error, SlotTakenError)
    assert scheduled_count(engine, world.dra_a) == 1


def test_two_bookings_that_both_validated_leave_one_appointment_and_one_slot_taken(
    engine: Engine, world: World, sessions: sessionmaker[Session]
) -> None:
    gate = threading.Barrier(2)
    deps = gated_deps(sessions, gate)
    principal = principal_for(world)

    def book(patient: Any) -> Callable[[], Appointment]:
        return lambda: book_appointment(
            deps,
            principal,
            patient_id=str(patient),
            professional_id=str(world.dra_a),
            starts_at=at(10),
        )

    pairs = [run_in_thread(book(world.juan)), run_in_thread(book(world.ana))]
    finish(*pairs)

    outcomes = [outcome for _, outcome in pairs]
    errors = [o.error for o in outcomes if o.error is not None]
    winners = [o.value for o in outcomes if o.error is None]
    assert len(winners) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], SlotTakenError)
    assert scheduled_count(engine, world.dra_a) == 1
    assert notification_rows(engine) == [("confirmation", "pending")]  # solo la del ganador


def test_rescheduling_competes_with_booking_and_exactly_one_wins(
    engine: Engine, world: World, sessions: sessionmaker[Session]
) -> None:
    with engine.begin() as connection:
        mine = insert_appointment(connection, world, at(10), at(10, 30), patient=world.juan)
    gate = threading.Barrier(2)
    deps = gated_deps(sessions, gate)
    principal = principal_for(world)

    pairs = [
        run_in_thread(lambda: reschedule_appointment(deps, str(mine), at(11))),
        run_in_thread(
            lambda: book_appointment(
                deps,
                principal,
                patient_id=str(world.ana),
                professional_id=str(world.dra_a),
                starts_at=at(11),
            )
        ),
    ]
    finish(*pairs)

    outcomes = [outcome for _, outcome in pairs]
    losers = [o for o in outcomes if o.error is not None]
    assert len(losers) == 1
    assert isinstance(losers[0].error, SlotTakenError)
    with engine.connect() as connection:
        starts = {
            str(row[0]): row[1]
            for row in connection.execute(text("SELECT id, starts_at FROM appointments"))
        }
    reschedule_lost = outcomes[0].error is not None
    assert (starts[str(mine)] == at(10)) is reschedule_lost
    assert scheduled_count(engine, world.dra_a) == (2 if reschedule_lost else 1)
    assert notification_rows(engine) == [("confirmation", "pending")]  # solo la del ganador


def test_simultaneous_bookings_with_different_professionals_both_succeed(
    engine: Engine, world: World, sessions: sessionmaker[Session]
) -> None:
    gate = threading.Barrier(2)
    deps = gated_deps(sessions, gate)
    principal = principal_for(world)

    def book(patient: Any, professional: Any) -> Callable[[], Appointment]:
        return lambda: book_appointment(
            deps,
            principal,
            patient_id=str(patient),
            professional_id=str(professional),
            starts_at=at(10),
        )

    pairs = [
        run_in_thread(book(world.juan, world.dra_a)),
        run_in_thread(book(world.ana, world.dr_b)),
    ]
    finish(*pairs)

    assert [outcome.error for _, outcome in pairs] == [None, None]
    assert scheduled_count(engine, world.dra_a) == 1
    assert scheduled_count(engine, world.dr_b) == 1
