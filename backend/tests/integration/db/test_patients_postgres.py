"""Garantias de la base para pacientes que la bateria de contrato no puede probar en memoria
(spec patient-repository): borrar con turnos y dos altas simultaneas con el mismo documento.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.patients.errors import DocumentTakenError, PatientHasAppointmentsError
from app.domain.patients.types import NewPatient
from app.infrastructure.db.repositories import SqlAlchemyPatientRepository
from tests.integration.db.helpers import World, at, insert_appointment, make_world, scalar

JOIN_SECONDS = 20.0


@pytest.fixture
def world(engine: Engine) -> World:
    with engine.begin() as connection:
        return make_world(connection)


@pytest.fixture
def sessions(engine: Engine) -> Iterator[sessionmaker[Session]]:
    own = create_engine(engine.url, connect_args={"options": "-c lock_timeout=10000"})
    yield sessionmaker(own, expire_on_commit=False)
    own.dispose()


def _count(engine: Engine, sql: str, **params: object) -> int:
    with engine.connect() as connection:
        return int(scalar(connection, sql, **params))


@pytest.mark.parametrize("status", ["cancelled", "scheduled", "completed"])
def test_delete_of_patient_with_an_appointment_in_any_status_is_rejected(
    engine: Engine, world: World, sessions: sessionmaker[Session], status: str
) -> None:
    with engine.begin() as connection:
        insert_appointment(connection, world, at(10), at(10, 30), status=status)
    repo = SqlAlchemyPatientRepository(sessions)
    with pytest.raises(PatientHasAppointmentsError):
        repo.delete(str(world.juan))
    assert _count(engine, "SELECT count(*) FROM patients WHERE id = :p", p=world.juan) == 1
    assert _count(engine, "SELECT count(*) FROM appointments") == 1


def test_delete_of_patient_without_appointments_leaves_the_others(
    engine: Engine, world: World, sessions: sessionmaker[Session]
) -> None:
    repo = SqlAlchemyPatientRepository(sessions)
    assert repo.delete(str(world.ana)) is True
    assert _count(engine, "SELECT count(*) FROM patients") == 1


def test_two_simultaneous_adds_with_the_same_document_save_one_and_reject_one(
    engine: Engine, sessions: sessionmaker[Session]
) -> None:
    repo = SqlAlchemyPatientRepository(sessions)
    gate = threading.Barrier(2)
    results: list[object] = []

    def add_laura(first_name: str) -> None:
        gate.wait(timeout=JOIN_SECONDS)
        try:
            results.append(
                repo.add(
                    NewPatient(
                        first_name=first_name,
                        last_name="Ruiz",
                        document_number="40222333",
                        email="laura@example.com",
                        birth_date=date(1990, 5, 10),
                    )
                )
            )
        except DocumentTakenError as error:
            results.append(error)

    threads = [threading.Thread(target=add_laura, args=(name,), daemon=True) for name in ("A", "B")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(JOIN_SECONDS)
        assert not thread.is_alive()
    assert sum(isinstance(r, DocumentTakenError) for r in results) == 1
    assert len(results) == 2
    assert _count(engine, "SELECT count(*) FROM patients WHERE document_number = '40222333'") == 1
