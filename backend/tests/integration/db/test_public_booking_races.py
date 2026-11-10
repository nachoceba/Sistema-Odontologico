"""Reserva online contra PostgreSQL real: carreras de la misma franja y del mismo DNI nuevo
(spec public-booking, regla dura 6, design D-4 y D-9).

Cada hilo valida por su lado y una barrera los frena justo antes de escribir, para que las dos
validaciones pasen con la base todavia vacia: lo que decide es el constraint de exclusion y el
indice unico del documento, no el orden de las lecturas.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from datetime import datetime, time
from types import TracebackType
from typing import Any, cast

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.application.appointments import AgendaDeps, book_appointment
from app.application.public_booking import PublicBookingDeps, book_online
from app.core.security import generate_confirmation_token, hash_confirmation_token
from app.domain.appointments import AgendaUnitOfWork
from app.domain.appointments.errors import SlotTakenError
from app.domain.auth import Principal, Role
from app.domain.patients import PatientRepository
from app.domain.public_booking.errors import BookingNotPossibleError
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
from app.infrastructure.notifications import NoOpNotificationDispatcher
from tests.integration.db.helpers import World, at, insert_working_hours, make_world, scalar
from tests.integration.db.test_appointment_concurrency import (
    JOIN_SECONDS,
    LOCK_TIMEOUT,
    NOW,
    finish,
    gated_deps,
    run_in_thread,
)


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


class NoVerification:
    def dispatch(self, appointment_id: str, token: str) -> None:
        return None


class GatedPatients:
    """Frena cada lectura por documento hasta que los dos pedidos ya leyeron (sin ficha)."""

    def __init__(self, inner: SqlAlchemyPatientRepository, gate: threading.Barrier) -> None:
        self._inner = inner
        self._gate = gate

    def get_by_document(self, document_number: str) -> Any:
        found = self._inner.get_by_document(document_number)
        self._gate.wait(timeout=JOIN_SECONDS)
        return found

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class PatientGatedUnitOfWork:
    def __init__(self, inner: SqlAlchemyAgendaUnitOfWork, gate: threading.Barrier) -> None:
        self._inner = inner
        self.appointments = inner.appointments
        self.notifications = inner.notifications
        self.patients = cast(PatientRepository, GatedPatients(inner.patients, gate))

    def __enter__(self) -> PatientGatedUnitOfWork:
        self._inner.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._inner.__exit__(exc_type, exc, traceback)


def public_deps(agenda: AgendaDeps) -> PublicBookingDeps:
    return PublicBookingDeps(
        agenda=agenda,
        new_token=generate_confirmation_token,
        hash_token=hash_confirmation_token,
        hold_minutes=60,
        verification=NoVerification(),
    )


def patient_gated_deps(sessions: sessionmaker[Session], gate: threading.Barrier) -> AgendaDeps:
    def unit_of_work() -> AgendaUnitOfWork:
        return cast(
            AgendaUnitOfWork, PatientGatedUnitOfWork(SqlAlchemyAgendaUnitOfWork(sessions), gate)
        )

    return AgendaDeps(
        appointments=SqlAlchemyAppointmentRepository(sessions),
        patients=SqlAlchemyPatientRepository(sessions),
        professionals=SqlAlchemyProfessionalRepository(sessions),
        working_hours=SqlAlchemyWorkingHoursRepository(sessions),
        time_off=SqlAlchemyTimeOffRepository(sessions),
        settings=SqlAlchemyClinicSettingsRepository(sessions),
        treatments=SqlAlchemyTreatmentRepository(sessions),
        unit_of_work=unit_of_work,
        dispatcher=NoOpNotificationDispatcher(),
        clock=lambda: NOW,
    )


def online(deps: PublicBookingDeps, world: World, starts_at: datetime, document: str) -> Any:
    return lambda: book_online(
        deps,
        professional_id=str(world.dra_a),
        treatment_id=str(world.consulta),
        starts_at=starts_at,
        document_number=document,
        first_name="Lucia",
        last_name="Diaz",
        email=f"{document}@example.com",
        phone=None,
    )


def count(engine: Engine, sql: str, **params: Any) -> int:
    with engine.connect() as connection:
        return int(scalar(connection, sql, **params))


def test_two_online_bookings_of_one_slot_with_new_documents_leave_one_appointment_and_one_patient(
    engine: Engine, world: World, sessions: sessionmaker[Session]
) -> None:
    gate = threading.Barrier(2)
    deps = public_deps(gated_deps(sessions, gate))

    pairs = [
        run_in_thread(online(deps, world, at(10), "40111111")),
        run_in_thread(online(deps, world, at(10), "40222222")),
    ]
    finish(*pairs)

    outcomes = [outcome for _, outcome in pairs]
    losers = [o for o in outcomes if o.error is not None]
    assert len(losers) == 1
    assert isinstance(losers[0].error, SlotTakenError)
    assert count(engine, "SELECT count(*) FROM appointments WHERE status = 'scheduled'") == 1
    winner_doc = "40111111" if outcomes[0].error is None else "40222222"
    loser_doc = "40222222" if winner_doc == "40111111" else "40111111"
    assert (
        count(engine, "SELECT count(*) FROM patients WHERE document_number = :d", d=winner_doc) == 1
    )
    # La ficha de la perdedora se creo en la misma transaccion y se deshizo con ella.
    assert (
        count(engine, "SELECT count(*) FROM patients WHERE document_number = :d", d=loser_doc) == 0
    )


def test_an_online_booking_and_a_reception_booking_of_one_slot_leave_one_appointment(
    engine: Engine, world: World, sessions: sessionmaker[Session]
) -> None:
    gate = threading.Barrier(2)
    agenda = gated_deps(sessions, gate)
    deps = public_deps(agenda)
    reception = Principal(user_id=str(world.reception), role=Role.RECEPTIONIST)

    pairs = [
        run_in_thread(online(deps, world, at(10), "40333333")),
        run_in_thread(
            lambda: book_appointment(
                agenda,
                reception,
                patient_id=str(world.juan),
                professional_id=str(world.dra_a),
                treatment_id=str(world.limpieza),  # otro tratamiento: el horario es uno solo
                starts_at=at(10),
            )
        ),
    ]
    finish(*pairs)

    errors = [o.error for _, o in pairs if o.error is not None]
    assert len(errors) == 1
    assert isinstance(errors[0], SlotTakenError)
    assert count(engine, "SELECT count(*) FROM appointments WHERE status = 'scheduled'") == 1
    online_won = pairs[0][1].error is None
    assert count(
        engine, "SELECT count(*) FROM patients WHERE document_number = :d", d="40333333"
    ) == (1 if online_won else 0)


def test_two_bookings_with_the_same_new_document_leave_one_patient_and_one_generic_rejection(
    engine: Engine, world: World, sessions: sessionmaker[Session]
) -> None:
    gate = threading.Barrier(2)
    deps = public_deps(patient_gated_deps(sessions, gate))

    pairs = [
        run_in_thread(online(deps, world, at(10), "40444444")),
        run_in_thread(online(deps, world, at(10, 30), "40444444")),
    ]
    finish(*pairs)

    errors = [o.error for _, o in pairs if o.error is not None]
    assert len(errors) == 1
    assert isinstance(errors[0], BookingNotPossibleError)
    assert (
        count(engine, "SELECT count(*) FROM patients WHERE document_number = :d", d="40444444") == 1
    )
    assert count(engine, "SELECT count(*) FROM appointments WHERE status = 'scheduled'") == 1


def test_the_loser_of_a_race_keeps_no_pending_appointment_or_token(
    engine: Engine, world: World, sessions: sessionmaker[Session]
) -> None:
    gate = threading.Barrier(2)
    deps = public_deps(gated_deps(sessions, gate))

    finish(
        run_in_thread(online(deps, world, at(10), "40555555")),
        run_in_thread(online(deps, world, at(10), "40666666")),
    )

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT pending_until IS NOT NULL, confirmation_token_hash IS NOT NULL "
                "FROM appointments"
            )
        ).all()
    assert [tuple(row) for row in rows] == [(True, True)]
