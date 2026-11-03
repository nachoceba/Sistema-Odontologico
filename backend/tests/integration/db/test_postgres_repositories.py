"""Comportamientos propios de los repositorios PostgreSQL (el resto lo cubre el contrato)."""

from __future__ import annotations

from datetime import UTC, time

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.appointments import (
    AppointmentStatus,
    NewAppointment,
    SlotTakenError,
    WorkingHours,
)
from app.infrastructure.db.repositories import (
    SqlAlchemyAppointmentRepository,
    SqlAlchemyClinicSettingsRepository,
    SqlAlchemyWorkingHoursRepository,
)
from tests.integration.db.helpers import World, at, make_world, scalar


@pytest.fixture
def world(engine: Engine) -> World:
    with engine.begin() as connection:
        return make_world(connection)


def new_appointment(world: World, start_hour: int, start_minute: int = 0) -> NewAppointment:
    return NewAppointment(
        patient_id=str(world.juan),
        professional_id=str(world.dra_a),
        starts_at=at(start_hour, start_minute),
        ends_at=at(start_hour, start_minute + 30),
        created_by=str(world.reception),
    )


def test_settings_repository_without_row_returns_defaults_and_does_not_create_it(
    engine: Engine, session_factory: sessionmaker[Session]
) -> None:
    settings = SqlAlchemyClinicSettingsRepository(session_factory).get()
    assert (settings.slot_minutes, settings.min_notice_hours) == (30, 6)
    with engine.connect() as connection:
        assert scalar(connection, "SELECT count(*) FROM clinic_settings") == 0


def test_slot_taken_comes_from_the_database_even_if_the_application_did_not_check(
    engine: Engine, session_factory: sessionmaker[Session], world: World
) -> None:
    repo = SqlAlchemyAppointmentRepository(session_factory)
    repo.add(new_appointment(world, 10))
    with pytest.raises(SlotTakenError) as raised:
        repo.add(new_appointment(world, 10, 15))
    assert raised.value.professional_id == str(world.dra_a)
    with engine.connect() as connection:
        assert scalar(connection, "SELECT count(*) FROM appointments") == 1


def test_other_integrity_errors_are_not_translated_to_slot_taken(
    session_factory: sessionmaker[Session], world: World
) -> None:
    repo = SqlAlchemyAppointmentRepository(session_factory)
    missing = NewAppointment(
        patient_id="00000000-0000-4000-8000-000000000000",
        professional_id=str(world.dra_a),
        starts_at=at(10),
        ends_at=at(10, 30),
        created_by=str(world.reception),
    )
    with pytest.raises(IntegrityError):
        repo.add(missing)


def test_reactivating_over_a_taken_slot_rolls_back_and_keeps_cancelled(
    session_factory: sessionmaker[Session], world: World
) -> None:
    repo = SqlAlchemyAppointmentRepository(session_factory)
    first = repo.add(new_appointment(world, 10))
    repo.change_status(first.id, AppointmentStatus.CANCELLED, "Aviso")
    repo.add(new_appointment(world, 10))
    with pytest.raises(SlotTakenError):
        repo.change_status(first.id, AppointmentStatus.SCHEDULED)
    found = repo.get(first.id)
    assert found is not None
    assert (found.status, found.cancel_reason) == (AppointmentStatus.CANCELLED, "Aviso")


def test_instants_are_returned_in_utc(session_factory: sessionmaker[Session], world: World) -> None:
    saved = SqlAlchemyAppointmentRepository(session_factory).add(new_appointment(world, 10))
    assert saved.starts_at.utcoffset() == UTC.utcoffset(None)
    assert saved.starts_at == at(10)


def test_invalid_reference_format_on_add_raises_value_error(
    session_factory: sessionmaker[Session], world: World
) -> None:
    repo = SqlAlchemyAppointmentRepository(session_factory)
    bad = NewAppointment(
        patient_id="pac-1",
        professional_id=str(world.dra_a),
        starts_at=at(10),
        ends_at=at(10, 30),
        created_by=str(world.reception),
    )
    with pytest.raises(ValueError, match="paciente"):
        repo.add(bad)


def test_replace_working_hours_is_atomic_when_a_new_block_is_rejected(
    session_factory: sessionmaker[Session], world: World
) -> None:
    repo = SqlAlchemyWorkingHoursRepository(session_factory)
    professional = str(world.dra_a)
    old = [WorkingHours(weekday=0, start_time=time(9), end_time=time(13))]
    repo.replace_for_professional(professional, old)
    broken = [WorkingHours(weekday=9, start_time=time(9), end_time=time(13))]
    with pytest.raises(IntegrityError):
        repo.replace_for_professional(professional, broken)
    assert repo.list_for_professional(professional) == old
