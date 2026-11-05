"""Desactivar, reactivar y borrar pacientes sin tocar la agenda (spec patient-management)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.application.appointments import book_appointment, cancel_appointment
from app.application.patients import (
    deactivate_patient,
    delete_patient,
    reactivate_patient,
)
from app.domain.appointments import Appointment, AppointmentStatus
from app.domain.appointments.errors import (
    PatientInactiveError,
    PatientNotFoundError,
    SlotTakenError,
)
from app.domain.auth import ForbiddenError
from app.domain.patients.errors import PatientHasAppointmentsError
from app.domain.patients.types import NewPatient
from tests.unit.application.agenda_helpers import ADMIN, DENTIST_A, PROF_A, RECEPTION, World
from tests.unit.domain.appointments.helpers import local, monday


def _agenda_state(world: World) -> tuple[list[Appointment], object]:
    return world.everything(), world.notifications.snapshot()


def _seed_with_status(
    world: World, starts_at: datetime, status: AppointmentStatus, patient_id: str = "pac-1"
) -> Appointment:
    created = world.seed(starts_at, patient_id=patient_id)
    if status is AppointmentStatus.SCHEDULED:
        return created
    return world.appointments.change_status(created.id, status, "motivo")


# --- Desactivar ---


def test_deactivate_lists_only_future_scheduled_appointments_and_changes_none() -> None:
    world = World()  # sabado 3 de octubre, 10:00 local
    tomorrow = _seed_with_status(world, local(2026, 10, 4, 10), AppointmentStatus.SCHEDULED)
    cancelled = _seed_with_status(world, local(2026, 10, 12, 10), AppointmentStatus.CANCELLED)
    done = _seed_with_status(world, local(2026, 10, 2, 10), AppointmentStatus.COMPLETED)
    state_before = _agenda_state(world)
    result = deactivate_patient(world.patient_deps(), RECEPTION, "pac-1")
    assert result.patient.active is False
    assert world.patients.get_record("pac-1") == result.patient
    assert [a.id for a in result.upcoming_appointments] == [tomorrow.id]
    assert _agenda_state(world) == state_before
    statuses = {a.id: a.status for a in world.everything()}
    assert statuses == {
        tomorrow.id: AppointmentStatus.SCHEDULED,
        cancelled.id: AppointmentStatus.CANCELLED,
        done.id: AppointmentStatus.COMPLETED,
    }


def test_upcoming_appointments_are_ordered_by_start() -> None:
    world = World()
    later = world.seed(local(2026, 10, 9, 10))
    sooner = world.seed(local(2026, 10, 5, 10))
    result = deactivate_patient(world.patient_deps(), ADMIN, "pac-1")
    assert [a.id for a in result.upcoming_appointments] == [sooner.id, later.id]


def test_after_deactivating_the_patient_cannot_be_booked() -> None:
    world = World()
    deactivate_patient(world.patient_deps(), RECEPTION, "pac-1")
    before = world.everything()
    with pytest.raises(PatientInactiveError):
        book_appointment(
            world.deps(),
            RECEPTION,
            patient_id="pac-1",
            professional_id=PROF_A,
            starts_at=monday(10),
        )
    assert world.everything() == before


def test_an_appointment_already_started_is_not_listed_and_stays_scheduled() -> None:
    world = World(now=local(2026, 10, 5, 10, 15))
    started = world.seed(local(2026, 10, 5, 10), minutes=30)
    result = deactivate_patient(world.patient_deps(), RECEPTION, "pac-1")
    assert result.upcoming_appointments == []
    assert world.appointments.get(started.id) == started
    assert started.status is AppointmentStatus.SCHEDULED


def test_an_appointment_starting_right_now_is_not_listed() -> None:
    world = World(now=local(2026, 10, 5, 10, 0))
    world.seed(local(2026, 10, 5, 10, 0))
    next_one = world.seed(local(2026, 10, 5, 10, 30))
    result = deactivate_patient(world.patient_deps(), RECEPTION, "pac-1")
    assert [a.id for a in result.upcoming_appointments] == [next_one.id]


def test_cancelling_an_appointment_of_an_inactive_patient_is_still_allowed() -> None:
    world = World()
    appointment = book_appointment(
        world.deps(),
        RECEPTION,
        patient_id="pac-1",
        professional_id=PROF_A,
        starts_at=monday(10),
    )
    deactivate_patient(world.patient_deps(), RECEPTION, "pac-1")
    cancelled = cancel_appointment(world.deps(), appointment.id, "Pidió cancelar")
    assert cancelled.status is AppointmentStatus.CANCELLED
    # el horario quedó libre: otra paciente activa lo puede tomar
    again = book_appointment(
        world.deps(),
        RECEPTION,
        patient_id="pac-2",
        professional_id=PROF_A,
        starts_at=monday(10),
    )
    assert again.status is AppointmentStatus.SCHEDULED


def test_deactivating_an_already_inactive_patient_is_not_an_error() -> None:
    world = World()
    world.set_patient_active("pac-2", False)
    future = world.seed(local(2026, 10, 6, 10), patient_id="pac-2")
    result = deactivate_patient(world.patient_deps(), RECEPTION, "pac-2")
    assert result.patient.active is False
    assert [a.id for a in result.upcoming_appointments] == [future.id]


def test_deactivating_with_an_hour_ahead_boundary_uses_the_injected_clock() -> None:
    world = World(now=local(2026, 10, 5, 9, 0))
    in_one_hour = world.seed(local(2026, 10, 5, 10, 0) + timedelta(0))
    result = deactivate_patient(world.patient_deps(), RECEPTION, "pac-1")
    assert [a.id for a in result.upcoming_appointments] == [in_one_hour.id]


def test_dentist_cannot_deactivate_and_nothing_changes() -> None:
    world = World()
    with pytest.raises(ForbiddenError):
        deactivate_patient(world.patient_deps(), DENTIST_A, "pac-1")
    record = world.patients.get_record("pac-1")
    assert record is not None
    assert record.active is True


def test_deactivating_an_unknown_patient_is_not_found() -> None:
    world = World()
    with pytest.raises(PatientNotFoundError):
        deactivate_patient(world.patient_deps(), RECEPTION, "no-existe")


# --- Reactivar ---


def test_reactivating_lets_the_patient_receive_appointments_again() -> None:
    world = World()
    world.set_patient_active("pac-2", False)
    state_before = _agenda_state(world)
    record = reactivate_patient(world.patient_deps(), RECEPTION, "pac-2")
    assert record.active is True
    assert _agenda_state(world) == state_before
    booked = book_appointment(
        world.deps(),
        RECEPTION,
        patient_id="pac-2",
        professional_id=PROF_A,
        starts_at=monday(10),
    )
    assert booked.patient_id == "pac-2"


def test_reactivating_an_active_patient_is_not_an_error() -> None:
    world = World()
    record = reactivate_patient(world.patient_deps(), ADMIN, "pac-1")
    assert (record.id, record.active) == ("pac-1", True)


def test_dentist_cannot_reactivate() -> None:
    world = World()
    world.set_patient_active("pac-2", False)
    with pytest.raises(ForbiddenError):
        reactivate_patient(world.patient_deps(), DENTIST_A, "pac-2")
    record = world.patients.get_record("pac-2")
    assert record is not None
    assert record.active is False


def test_reactivating_an_unknown_patient_is_not_found() -> None:
    world = World()
    with pytest.raises(PatientNotFoundError):
        reactivate_patient(world.patient_deps(), RECEPTION, "no-existe")


# --- Regla dura 6: reactivar no habilita superponer ---


def test_reactivating_does_not_allow_overlapping_a_scheduled_appointment() -> None:
    world = World()
    world.set_patient_active("pac-2", False)
    taken = book_appointment(
        world.deps(),
        RECEPTION,
        patient_id="pac-1",
        professional_id=PROF_A,
        starts_at=monday(10),
    )
    reactivate_patient(world.patient_deps(), RECEPTION, "pac-2")
    with pytest.raises(SlotTakenError):
        book_appointment(
            world.deps(),
            RECEPTION,
            patient_id="pac-2",
            professional_id=PROF_A,
            starts_at=monday(10),
        )
    scheduled = [a for a in world.everything() if a.status is AppointmentStatus.SCHEDULED]
    assert [a.id for a in scheduled] == [taken.id]


# --- Borrar ---


def test_admin_deletes_a_patient_without_appointments_and_frees_the_document() -> None:
    world = World()
    laura = world.patients.add(NewPatient("Laura", "Ruiz", "40222333", "laura@example.com"))
    delete_patient(world.patient_deps(), ADMIN, laura.id)
    assert world.patients.get_record(laura.id) is None
    again = world.patients.add(NewPatient("Otra", "Ruiz", "40222333", "otra@example.com"))
    assert again.document_number == "40222333"


@pytest.mark.parametrize(
    "status",
    [AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED, AppointmentStatus.SCHEDULED],
)
def test_delete_is_rejected_when_the_patient_has_any_appointment(
    status: AppointmentStatus,
) -> None:
    world = World()
    _seed_with_status(world, local(2026, 10, 12, 10), status)
    state_before = _agenda_state(world)
    with pytest.raises(PatientHasAppointmentsError):
        delete_patient(world.patient_deps(), ADMIN, "pac-1")
    assert world.patients.get_record("pac-1") is not None
    assert _agenda_state(world) == state_before


def test_delete_of_an_unknown_patient_is_not_found() -> None:
    world = World()
    with pytest.raises(PatientNotFoundError):
        delete_patient(world.patient_deps(), ADMIN, "no-existe")


@pytest.mark.parametrize("principal", [RECEPTION, DENTIST_A])
def test_only_the_admin_can_delete(principal: object) -> None:
    from app.domain.auth import Principal

    assert isinstance(principal, Principal)
    world = World()
    laura = world.patients.add(NewPatient("Laura", "Ruiz", "40222333", "laura@example.com"))
    with pytest.raises(ForbiddenError):
        delete_patient(world.patient_deps(), principal, laura.id)
    assert world.patients.get_record(laura.id) is not None
